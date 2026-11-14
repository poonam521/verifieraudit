"""Compare a candidate solution with the reference on many inputs.

Runs as a standalone script in its own process (no package imports), so a
candidate that hangs or crashes cannot take the audit down with it.

usage: _oracle_worker.py REFERENCE CANDIDATE INPUTS ENTRY SEED SAMPLES
"""

import contextlib
import copy
import importlib.util
import io
import json
import random
import signal
import sys

MARK = "@@VERIFIERAUDIT@@"
CALL_LIMIT_SECONDS = 1.0


class _Hang(BaseException):
    """Raised by the timer. BaseException so candidate code cannot swallow it."""


def _on_alarm(signum, frame):
    raise _Hang()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call(fn, args):
    timed = hasattr(signal, "setitimer")
    try:
        args = copy.deepcopy(args)
        if timed:
            signal.setitimer(signal.ITIMER_REAL, CALL_LIMIT_SECONDS)
        try:
            return ("ok", fn(*args))
        finally:
            if timed:
                signal.setitimer(signal.ITIMER_REAL, 0)
    except _Hang:
        return ("hang", None)
    except Exception as exc:  # the candidate's own errors are a normal outcome
        return ("raise", type(exc).__name__)


def _show(outcome):
    kind, value = outcome
    if kind == "ok":
        text = repr(value)
        return text if len(text) <= 200 else text[:197] + "..."
    if kind == "raise":
        return f"raises {value}"
    return f"does not finish (over {CALL_LIMIT_SECONDS:g}s)"


def _same(expected, got, custom):
    if expected[0] != got[0]:
        return False
    if expected[0] != "ok":
        return expected[1] == got[1]
    try:
        if custom is not None:
            return bool(custom(expected[1], got[1]))
        return bool(expected[1] == got[1])
    except Exception:
        return False


def _compare(argv):
    reference_path, candidate_path, inputs_path, entry, seed, samples = argv
    inputs = _load(inputs_path, "va_inputs")
    reference = getattr(_load(reference_path, "va_reference"), entry)

    try:
        candidate_module = _load(candidate_path, "va_candidate")
    except Exception as exc:
        return {"status": "different", "reason": "load_error",
                "detail": f"{type(exc).__name__}: {exc}"}
    candidate = getattr(candidate_module, entry, None)
    if not callable(candidate):
        return {"status": "different", "reason": "missing_entry",
                "detail": f"no function named {entry}"}

    rng = random.Random(int(seed))
    cases = list(getattr(inputs, "EDGE_CASES", []))
    cases += [inputs.generate(rng) for _ in range(int(samples))]
    custom = getattr(inputs, "same", None)

    if hasattr(signal, "setitimer"):
        signal.signal(signal.SIGALRM, _on_alarm)

    for case in cases:
        args = case if isinstance(case, tuple) else (case,)
        expected = _call(reference, args)
        if expected[0] == "hang":
            return {"status": "error", "reason": "reference_hang",
                    "detail": "reference solution did not finish on " + repr(args)[:200]}
        got = _call(candidate, args)
        if not _same(expected, got, custom):
            shown = ", ".join(repr(a) for a in args)
            if len(shown) > 200:
                shown = shown[:197] + "..."
            return {"status": "different", "reason": "counterexample",
                    "call": f"{entry}({shown})",
                    "expected": _show(expected), "got": _show(got)}
    return {"status": "equivalent", "cases": len(cases)}


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            result = _compare(sys.argv[1:])
        except Exception as exc:
            result = {"status": "error", "reason": "worker_error",
                      "detail": f"{type(exc).__name__}: {exc}"}
    sys.__stdout__.write(MARK + json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
