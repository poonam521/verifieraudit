"""Files written by ``verifieraudit init``."""

from __future__ import annotations

from pathlib import Path

FILES = {
    "task.toml": '''\
name = "my_task"
description = "One sentence saying what the function should do."
entry = "add"            # the function the grader tests
solution = "solution.py" # a solution you know is correct
grader = "tests"         # the tests being audited
timeout = 20             # seconds allowed for one grader run
# visible = "visible"    # optional: folder of files an agent is given
''',
    "solution.py": '''\
def add(a, b):
    return a + b
''',
    "inputs.py": '''\
"""How to make inputs for the function under test."""

# Inputs that are always tried. Put boundary values here.
EDGE_CASES = [(0, 0), (-1, 1)]


def generate(rng):
    """Return one tuple of arguments. ``rng`` is a seeded random.Random."""
    return (rng.randint(-100, 100), rng.randint(-100, 100))


# Optional: define same(expected, got) if two different outputs can both be
# correct (for example, when the order of a returned list does not matter).
''',
    "tests/test_solution.py": '''\
from solution import add


def test_add():
    assert add(2, 3) == 5
''',
    "alternates/README.md": '''\
Put other correct solutions here as .py files. The audit checks that the
grader accepts every one of them.
''',
}


def write_task(target: str | Path) -> list[Path]:
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"{target} already exists and is not empty")
    written = []
    for relative, content in FILES.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
