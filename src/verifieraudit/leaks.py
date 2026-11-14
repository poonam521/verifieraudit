"""Look for answers left where an agent could read them.

Scans the task's ``visible`` folder (everything the agent is given) for:

* a copy of the reference solution in any file,
* the reference solution recoverable from git history,
* the grader's own test files (which hand out the expected outputs).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .task import Task

MAX_FILE_BYTES = 1_000_000
MIN_LINE_LENGTH = 10
OVERLAP_THRESHOLD = 0.6


@dataclass(frozen=True)
class Leak:
    severity: str  # "high" or "medium"
    kind: str
    path: str
    detail: str


def _distinctive_lines(source: str) -> set[str]:
    lines = set()
    for raw in source.splitlines():
        line = raw.strip()
        if len(line) < MIN_LINE_LENGTH or line.startswith(("#", '"""', "'''")):
            continue
        lines.add(line)
    return lines


def _overlap(wanted: set[str], text: str) -> float:
    if len(wanted) < 2:
        return 0.0
    present = {line.strip() for line in text.splitlines()}
    return len(wanted & present) / len(wanted)


def _normalise(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def scan(task: Task) -> list[Leak]:
    if task.visible_dir is None:
        return []
    leaks: list[Leak] = []
    wanted = _distinctive_lines(task.reference_source())
    grader_files = {
        _normalise(path.read_text(encoding="utf-8", errors="ignore")): path.name
        for path in task.grader_dir.rglob("*.py")
    }

    for path in sorted(task.visible_dir.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(task.visible_dir).parts:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(task.visible_dir).as_posix()
        share = _overlap(wanted, text)
        if share >= OVERLAP_THRESHOLD:
            leaks.append(Leak(
                "high", "solution-in-files", relative,
                f"contains {share:.0%} of the reference solution's lines",
            ))
        if _normalise(text) in grader_files:
            leaks.append(Leak(
                "medium", "grader-visible", relative,
                "is a copy of the grader's tests, so the expected outputs can be read off",
            ))

    if (task.visible_dir / ".git").exists() and shutil.which("git"):
        try:
            history = subprocess.run(
                ["git", "-C", str(task.visible_dir), "log", "--all", "-p", "--no-color"],
                capture_output=True, text=True, errors="ignore", timeout=30,
            ).stdout
        except (subprocess.TimeoutExpired, OSError):
            history = ""
        added = "\n".join(
            line[1:] for line in history.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        share = _overlap(wanted, added)
        if share >= OVERLAP_THRESHOLD:
            leaks.append(Leak(
                "high", "solution-in-git-history", ".git",
                f"{share:.0%} of the reference solution's lines can be recovered "
                "with `git log -p`",
            ))
    return leaks
