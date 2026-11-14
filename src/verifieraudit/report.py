"""Turn audit results into a console summary, Markdown and JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from . import __version__
from .audit import Config, TaskAudit


def _rate(count: int, total: int) -> str:
    if not total:
        return "n/a"
    share = count / total
    percent = f"{share:.0%}" if share in (0, 1) else f"{share:.1%}"
    return f"{count}/{total} ({percent})"


def _verdict(audit: TaskAudit) -> str:
    if audit.error:
        return "INVALID"
    return "PASS" if audit.passed else "FAIL"


def summary_rows(audits: list[TaskAudit]) -> list[list[str]]:
    rows = [["Task", "Wrong accepted", "Correct rejected", "Cheats", "Leaks", "Verdict"]]
    for audit in audits:
        if audit.error:
            rows.append([audit.name, "-", "-", "-", "-", "INVALID"])
            continue
        rows.append([
            audit.name,
            _rate(len(audit.false_accepts), audit.wrong_mutants),
            _rate(len(audit.false_rejects), audit.valid_alternates),
            str(len(audit.exploits)),
            str(len(audit.leaks)),
            _verdict(audit),
        ])
    return rows


def to_console(audits: list[TaskAudit]) -> str:
    rows = summary_rows(audits)
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = []
    for index, row in enumerate(rows):
        lines.append("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip())
        if index == 0:
            lines.append("  ".join("-" * width for width in widths))
    for audit in audits:
        if audit.error:
            lines += ["", f"{audit.name}: INVALID", f"  - {audit.error}"]
        elif audit.issues:
            lines += ["", f"{audit.name}: FAIL"] + [f"  - {issue}" for issue in audit.issues]
    failed = sum(not audit.passed for audit in audits)
    lines += ["", f"{len(audits) - failed} of {len(audits)} graders passed the audit."]
    return "\n".join(lines)


def to_dict(audits: list[TaskAudit], cfg: Config) -> dict:
    return {
        "tool": "verifieraudit",
        "version": __version__,
        "settings": {"samples": cfg.samples, "seed": cfg.seed,
                     "max_false_accept": cfg.max_false_accept,
                     "max_false_reject": cfg.max_false_reject},
        "tasks": [
            {
                "name": audit.name,
                "verdict": _verdict(audit),
                "error": audit.error,
                "issues": audit.issues,
                "warnings": audit.warnings,
                "false_accepts": len(audit.false_accepts),
                "wrong_mutants": audit.wrong_mutants,
                "false_accept_rate": audit.false_accept_rate,
                "equivalent_mutants": sum(m.status == "equivalent" for m in audit.mutants),
                "false_rejects": len(audit.false_rejects),
                "valid_alternates": audit.valid_alternates,
                "false_reject_rate": audit.false_reject_rate,
                "exploits": [p.id for p in audit.exploits],
                "leaks": [asdict(leak) for leak in audit.leaks],
                "mutants": [asdict(m) for m in audit.mutants],
                "alternates": [asdict(a) for a in audit.alternates],
                "probes": [asdict(p) for p in audit.probes],
            }
            for audit in audits
        ],
    }


def to_json(audits: list[TaskAudit], cfg: Config) -> str:
    return json.dumps(to_dict(audits, cfg), indent=2) + "\n"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _table(rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    lines += ["| " + " | ".join(_cell(cell) for cell in row) + " |" for row in rows[1:]]
    return lines


def to_markdown(audits: list[TaskAudit], cfg: Config) -> str:
    out = ["# VerifierAudit report", ""]
    out.append(
        f"verifieraudit {__version__}; {cfg.samples} random inputs per comparison, seed {cfg.seed}. "
        f"A grader fails if it accepts more than {cfg.max_false_accept:.0%} of wrong variants, "
        f"rejects more than {cfg.max_false_reject:.0%} of correct alternatives, can be cheated, "
        "or the answer is leaked."
    )
    out += [""] + _table(summary_rows(audits)) + [""]

    for audit in audits:
        out += [f"## {audit.name}: {_verdict(audit)}", ""]
        if audit.description:
            out += [audit.description, ""]
        if audit.error:
            out += ["This task could not be audited:", "", "```", audit.error, "```", ""]
            continue
        if audit.issues:
            out += ["**Problems found**", ""] + [f"- {issue}" for issue in audit.issues] + [""]
        if audit.warnings:
            out += ["**Notes**", ""] + [f"- {warning}" for warning in audit.warnings] + [""]

        equivalent = sum(m.status == "equivalent" for m in audit.mutants)
        out.append(
            f"Tried {len(audit.mutants)} single-edit variants of the reference solution: "
            f"{audit.wrong_mutants} were wrong, {equivalent} behaved the same on every sampled "
            f"input and were left out. The grader accepted {len(audit.false_accepts)} of the wrong ones."
        )
        out.append("")

        if audit.false_accepts:
            out += ["### Wrong solutions the grader accepted", "",
                    "Each row is a test the grader is missing.", ""]
            rows = [["Edit", "Input the tests miss", "Correct answer", "Wrong answer accepted"]]
            for mutant in audit.false_accepts:
                rows.append([mutant.title, f"`{mutant.call}`" if mutant.call else "(see note)",
                             f"`{mutant.expected}`" if mutant.expected else "-",
                             f"`{mutant.got}`" if mutant.got else "-"])
            out += _table(rows) + [""]

        if audit.false_rejects:
            out += ["### Correct solutions the grader rejected", ""]
            for alternate in audit.false_rejects:
                out += [f"`{alternate.id}` matches the reference on every sampled input but failed:",
                        "", "```", alternate.note, "```", ""]

        if audit.exploits:
            out += ["### Cheats that passed", ""]
            for probe in audit.exploits:
                example = f" For example `{probe.call}` should give `{probe.expected}`." if probe.call else ""
                out.append(f"- `{probe.id}`: {probe.title}.{example}")
            out.append("")

        if audit.leaks:
            out += ["### Leaks", ""]
            out += [f"- [{leak.severity}] `{leak.path}` {leak.detail}" for leak in audit.leaks]
            out.append("")
    return "\n".join(out).rstrip() + "\n"
