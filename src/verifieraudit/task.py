"""Loading audit tasks from disk.

A task is a folder with a ``task.toml`` plus:

* a reference solution (known to be correct),
* a grader (by default a folder of pytest tests that import the solution),
* ``inputs.py`` describing how to generate inputs for the function,
* optionally ``alternates/`` with other correct solutions,
* optionally a folder of files an agent would be able to see.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class TaskError(Exception):
    """The task folder is missing something or is inconsistent."""


@dataclass(frozen=True)
class Task:
    name: str
    root: Path
    entry: str
    solution: Path
    grader_dir: Path
    inputs: Path
    alternates: tuple[Path, ...]
    visible_dir: Path | None
    command: tuple[str, ...] | None
    timeout: float
    description: str

    def reference_source(self) -> str:
        return self.solution.read_text(encoding="utf-8")


def load_task(root: str | Path) -> Task:
    root = Path(root).resolve()
    config_path = root / "task.toml"
    if not config_path.is_file():
        raise TaskError(f"{root}: no task.toml found")
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise TaskError(f"{config_path}: {exc}") from exc

    entry = config.get("entry")
    if not isinstance(entry, str) or not entry:
        raise TaskError(f"{config_path}: 'entry' (the function name to test) is required")

    solution = root / config.get("solution", "solution.py")
    grader_dir = root / config.get("grader", "tests")
    inputs = root / config.get("inputs", "inputs.py")
    for label, path, is_dir in (
        ("solution", solution, False),
        ("grader", grader_dir, True),
        ("inputs", inputs, False),
    ):
        if (is_dir and not path.is_dir()) or (not is_dir and not path.is_file()):
            raise TaskError(f"{root}: {label} not found at {path.name}")

    alternates_dir = root / config.get("alternates", "alternates")
    alternates = (
        tuple(sorted(alternates_dir.glob("*.py"))) if alternates_dir.is_dir() else ()
    )

    visible_dir = None
    if "visible" in config:
        visible_dir = root / config["visible"]
        if not visible_dir.is_dir():
            raise TaskError(f"{root}: visible folder not found at {config['visible']}")

    command = config.get("command")
    if command is not None:
        if not isinstance(command, list) or not all(isinstance(c, str) for c in command):
            raise TaskError(f"{config_path}: 'command' must be a list of strings")
        command = tuple(command)

    return Task(
        name=str(config.get("name", root.name)),
        root=root,
        entry=entry,
        solution=solution,
        grader_dir=grader_dir,
        inputs=inputs,
        alternates=alternates,
        visible_dir=visible_dir,
        command=command,
        timeout=float(config.get("timeout", 20)),
        description=str(config.get("description", "")).strip(),
    )


def discover_tasks(path: str | Path) -> list[Task]:
    """Load one task folder, or every task folder directly inside ``path``."""
    path = Path(path)
    if not path.is_dir():
        raise TaskError(f"{path}: not a folder")
    if (path / "task.toml").is_file():
        return [load_task(path)]
    tasks = [load_task(p.parent) for p in sorted(path.glob("*/task.toml"))]
    if not tasks:
        raise TaskError(f"{path}: no task.toml here or in any direct subfolder")
    return tasks
