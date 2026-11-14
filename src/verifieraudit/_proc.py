"""Running candidate code in a separate process with a time and memory limit.

This is process isolation, not a security sandbox: it protects the audit from
hangs, crashes and runaway memory, not from deliberately hostile code.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass

MEMORY_LIMIT_BYTES = 2 * 1024**3


@dataclass
class ProcResult:
    returncode: int | None
    output: str
    timed_out: bool
    duration: float


def _limit_memory() -> None:  # runs in the child, POSIX only
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except Exception:
        pass


def run(cmd: list[str], *, cwd: str, env: dict[str, str], timeout: float) -> ProcResult:
    posix = os.name == "posix"
    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=posix,
        preexec_fn=_limit_memory if posix else None,
    )
    try:
        output, _ = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        if posix:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        output, _ = proc.communicate()
    return ProcResult(
        returncode=None if timed_out else proc.returncode,
        output=output or "",
        timed_out=timed_out,
        duration=time.monotonic() - started,
    )
