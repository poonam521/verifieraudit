"""Run a task's grader against one candidate solution."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import _proc
from .task import Task

DEFAULT_COMMAND = (
    "{python}", "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider",
)


@dataclass
class GradeResult:
    passed: bool
    timed_out: bool
    duration: float
    output: str

    def tail(self, lines: int = 12) -> str:
        return "\n".join(self.output.strip().splitlines()[-lines:])


def grade(task: Task, source: str) -> GradeResult:
    """Copy the grader into a scratch folder, drop in ``source`` as the solution, run it."""
    command = [
        part.replace("{python}", sys.executable)
        for part in (task.command or DEFAULT_COMMAND)
    ]
    with tempfile.TemporaryDirectory(prefix="verifieraudit-") as tmp:
        shutil.copytree(
            task.grader_dir,
            Path(tmp) / task.grader_dir.name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
        (Path(tmp) / task.solution.name).write_text(source, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
        env["PYTHONPATH"] = tmp
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = _proc.run(command, cwd=tmp, env=env, timeout=task.timeout)
    return GradeResult(
        passed=result.returncode == 0,
        timed_out=result.timed_out,
        duration=result.duration,
        output=result.output,
    )
