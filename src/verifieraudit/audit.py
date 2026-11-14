"""Run the full audit for a task and decide a verdict."""

from __future__ import annotations

import os
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import leaks as leak_scan
from . import oracle, probes, runner
from .leaks import Leak
from .mutate import generate_mutants
from .task import Task, TaskError


@dataclass
class Config:
    samples: int = 300
    seed: int = 0
    max_mutants: int = 200
    workers: int = field(default_factory=lambda: min(8, os.cpu_count() or 2))
    oracle_timeout: float = 10.0
    max_false_accept: float = 0.05
    max_false_reject: float = 0.0


@dataclass
class Outcome:
    """What happened to one candidate solution."""

    id: str
    title: str
    status: str
    call: str = ""
    expected: str = ""
    got: str = ""
    note: str = ""
    source: str = ""


@dataclass
class TaskAudit:
    name: str
    description: str = ""
    error: str = ""
    mutants: list[Outcome] = field(default_factory=list)
    alternates: list[Outcome] = field(default_factory=list)
    probes: list[Outcome] = field(default_factory=list)
    leaks: list[Leak] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Mutants: equivalent | rejected | false_accept
    @property
    def false_accepts(self) -> list[Outcome]:
        return [m for m in self.mutants if m.status == "false_accept"]

    @property
    def wrong_mutants(self) -> int:
        return sum(m.status in ("rejected", "false_accept") for m in self.mutants)

    @property
    def false_accept_rate(self) -> float | None:
        return len(self.false_accepts) / self.wrong_mutants if self.wrong_mutants else None

    # Alternates: accepted | false_reject | invalid
    @property
    def false_rejects(self) -> list[Outcome]:
        return [a for a in self.alternates if a.status == "false_reject"]

    @property
    def valid_alternates(self) -> int:
        return sum(a.status in ("accepted", "false_reject") for a in self.alternates)

    @property
    def false_reject_rate(self) -> float | None:
        return len(self.false_rejects) / self.valid_alternates if self.valid_alternates else None

    # Probes: rejected | exploit | skipped
    @property
    def exploits(self) -> list[Outcome]:
        return [p for p in self.probes if p.status == "exploit"]

    @property
    def passed(self) -> bool:
        return not self.error and not self.issues


def _evidence(result: oracle.OracleResult) -> dict[str, str]:
    return {"call": result.call, "expected": result.expected, "got": result.got}


def _audit_mutant(task: Task, mutant, cfg: Config) -> Outcome:
    verdict = oracle.compare(task, mutant.source, samples=cfg.samples, seed=cfg.seed,
                             timeout=cfg.oracle_timeout)
    if verdict.equivalent:
        return Outcome(mutant.id, mutant.description, "equivalent",
                       note="behaves like the reference on every sampled input")
    graded = runner.grade(task, mutant.source)
    return Outcome(mutant.id, mutant.description,
                   "false_accept" if graded.passed else "rejected",
                   source=mutant.source if graded.passed else "", **_evidence(verdict))


def _audit_alternate(task: Task, path, cfg: Config) -> Outcome:
    source = path.read_text(encoding="utf-8")
    verdict = oracle.compare(task, source, samples=cfg.samples, seed=cfg.seed,
                             timeout=cfg.oracle_timeout)
    if not verdict.equivalent:
        return Outcome(path.name, path.name, "invalid",
                       note="disagrees with the reference, so it is not a fair test of the grader",
                       **_evidence(verdict))
    graded = runner.grade(task, source)
    if graded.passed:
        return Outcome(path.name, path.name, "accepted")
    return Outcome(path.name, path.name, "false_reject", note=graded.tail())


def _audit_probe(task: Task, probe, cfg: Config) -> Outcome:
    verdict = oracle.compare(task, probe.source, samples=cfg.samples, seed=cfg.seed,
                             timeout=cfg.oracle_timeout)
    if verdict.equivalent:
        return Outcome(probe.id, probe.title, "skipped",
                       note="happens to be correct for this task")
    graded = runner.grade(task, probe.source)
    return Outcome(probe.id, probe.title, "exploit" if graded.passed else "rejected",
                   source=probe.source if graded.passed else "", **_evidence(verdict))


def _percent(rate: float) -> str:
    return f"{rate:.0%}" if rate in (0, 1) else f"{rate:.1%}"


def audit_task(task: Task, cfg: Config | None = None) -> TaskAudit:
    cfg = cfg or Config()
    audit = TaskAudit(name=task.name, description=task.description)
    reference = task.reference_source()

    try:
        sanity = oracle.compare(task, reference, samples=min(cfg.samples, 50),
                                seed=cfg.seed, timeout=cfg.oracle_timeout)
        if not sanity.equivalent:
            raise TaskError(
                "the reference solution does not give the same answer twice "
                f"({sanity.call or sanity.detail}); it must be deterministic"
            )
        graded = runner.grade(task, reference)
        if not graded.passed:
            raise TaskError("the reference solution fails its own grader:\n" + graded.tail())
        mutants = generate_mutants(reference)
    except (TaskError, SyntaxError) as exc:
        audit.error = str(exc)
        return audit

    if len(mutants) > cfg.max_mutants:
        keep = set(random.Random(cfg.seed).sample(range(len(mutants)), cfg.max_mutants))
        mutants = [m for i, m in enumerate(mutants) if i in keep]
        audit.warnings.append(f"sampled {cfg.max_mutants} mutants out of a larger set")

    with ThreadPoolExecutor(max_workers=max(1, cfg.workers)) as pool:
        audit.mutants = list(pool.map(lambda m: _audit_mutant(task, m, cfg), mutants))
        audit.alternates = list(pool.map(lambda p: _audit_alternate(task, p, cfg), task.alternates))
        audit.probes = list(pool.map(lambda p: _audit_probe(task, p, cfg), probes.build_probes(task)))
    audit.leaks = leak_scan.scan(task)

    rate = audit.false_accept_rate
    if rate is not None and rate > cfg.max_false_accept:
        audit.issues.append(
            f"accepts wrong solutions: {len(audit.false_accepts)} of {audit.wrong_mutants} "
            f"wrong variants passed ({_percent(rate)})"
        )
    elif audit.false_accepts:
        audit.warnings.append(
            f"{len(audit.false_accepts)} of {audit.wrong_mutants} wrong variants passed "
            f"({_percent(rate)}), within the allowed {_percent(cfg.max_false_accept)}"
        )
    rate = audit.false_reject_rate
    if rate is not None and rate > cfg.max_false_reject:
        audit.issues.append(
            f"rejects correct solutions: {len(audit.false_rejects)} of "
            f"{audit.valid_alternates} correct alternatives failed ({_percent(rate)})"
        )
    if audit.exploits:
        audit.issues.append(
            "can be cheated: " + ", ".join(p.id for p in audit.exploits) + " passed the grader"
        )
    for leak in audit.leaks:
        message = f"{leak.path} {leak.detail}"
        if leak.severity == "high":
            audit.issues.append("answer leaked: " + message)
        else:
            audit.warnings.append(message)
    for alternate in audit.alternates:
        if alternate.status == "invalid":
            audit.warnings.append(f"alternate {alternate.id} {alternate.note}")
    if not audit.wrong_mutants:
        audit.warnings.append("no behaviour-changing mutants were found; add EDGE_CASES or more samples")
    return audit


def audit_tasks(tasks: list[Task], cfg: Config | None = None) -> list[TaskAudit]:
    return [audit_task(task, cfg) for task in tasks]
