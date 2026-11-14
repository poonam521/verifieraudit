"""Decide whether a candidate really behaves differently from the reference.

A mutant only counts as "wrong" if it gives a different result from the
reference solution on at least one input. The comparison runs on the task's
``EDGE_CASES`` plus randomly generated inputs, so the answer is evidence-based
rather than exhaustive: a difference that only shows up on an input that was
never sampled is reported as "equivalent" and left out of the rates.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import _proc
from .task import Task, TaskError

_WORKER = Path(__file__).with_name("_oracle_worker.py")
_MARK = "@@VERIFIERAUDIT@@"


@dataclass
class OracleResult:
    equivalent: bool
    reason: str = ""
    call: str = ""
    expected: str = ""
    got: str = ""
    detail: str = ""


def compare(task: Task, source: str, *, samples: int, seed: int, timeout: float) -> OracleResult:
    with tempfile.TemporaryDirectory(prefix="verifieraudit-") as tmp:
        candidate = Path(tmp) / "candidate.py"
        candidate.write_text(source, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = _proc.run(
            [sys.executable, str(_WORKER), str(task.solution), str(candidate),
             str(task.inputs), task.entry, str(seed), str(samples)],
            cwd=tmp, env=env, timeout=timeout,
        )

    if result.timed_out:
        return OracleResult(False, reason="timeout", got="does not finish",
                            detail=f"comparison exceeded {timeout:g}s")
    payload = None
    for line in result.output.splitlines():
        if line.startswith(_MARK):
            payload = json.loads(line[len(_MARK):])
    if payload is None:
        return OracleResult(False, reason="crashed", got="crashes the interpreter",
                            detail=result.output.strip()[-300:])
    if payload["status"] == "error":
        raise TaskError(f"{task.name}: {payload.get('detail', payload.get('reason'))}")
    if payload["status"] == "equivalent":
        return OracleResult(True, reason="equivalent")
    return OracleResult(
        False,
        reason=payload.get("reason", ""),
        call=payload.get("call", ""),
        expected=payload.get("expected", ""),
        got=payload.get("got", payload.get("detail", "")),
        detail=payload.get("detail", ""),
    )
