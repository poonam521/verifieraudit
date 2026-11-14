"""Cheating solutions: code that does not solve the task but may still pass.

Three families:

* ``memoriser``: a lookup table built from the examples written in the
  grader's own tests. If it passes, the grader can be beaten by anyone (or
  any agent) who can read the tests.
* ``stub-*``: functions that ignore their input and return a constant.
* ``empty``: a file with no function at all.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .task import Task


@dataclass(frozen=True)
class Probe:
    id: str
    title: str
    source: str


def _literal(node: ast.AST, env: dict[str, object] | None = None) -> tuple[bool, object]:
    if env is not None and isinstance(node, ast.Name) and node.id in env:
        return True, env[node.id]
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False, None


def _is_entry_call(node: ast.AST, entry: str) -> bool:
    if not isinstance(node, ast.Call) or node.keywords:
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == entry) or (
        isinstance(func, ast.Attribute) and func.attr == entry
    )


def _pairs_in(scope: ast.AST, entry: str, env: dict[str, object] | None) -> list[tuple[tuple, object]]:
    pairs = []
    for node in ast.walk(scope):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
            continue
        if not isinstance(node.ops[0], (ast.Eq, ast.Is)):
            continue
        left, right = node.left, node.comparators[0]
        if _is_entry_call(right, entry):
            left, right = right, left
        if not _is_entry_call(left, entry):
            continue
        args = [_literal(arg, env) for arg in left.args]
        ok, expected = _literal(right, env)
        if ok and all(found for found, _ in args):
            pairs.append((tuple(value for _, value in args), expected))
    return pairs


def _parametrize_envs(function: ast.FunctionDef) -> list[dict[str, object]]:
    envs: list[dict[str, object]] = []
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or len(decorator.args) < 2:
            continue
        if not ast.unparse(decorator.func).endswith("parametrize"):
            continue
        ok_names, names = _literal(decorator.args[0])
        ok_rows, rows = _literal(decorator.args[1])
        if not (ok_names and ok_rows):
            continue
        if isinstance(names, str):
            names = [part.strip() for part in names.split(",")]
        try:
            for row in rows:
                values = [row] if len(names) == 1 else list(row)
                if len(values) == len(names):
                    envs.append(dict(zip(names, values)))
        except TypeError:
            continue
    return envs


def extract_examples(task: Task) -> list[tuple[tuple, object]]:
    """Find ``entry(args) == expected`` examples written in the grader's tests."""
    examples: dict[str, tuple[tuple, object]] = {}
    for path in sorted(task.grader_dir.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        found = _pairs_in(tree, task.entry, None)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for env in _parametrize_envs(node):
                    found += _pairs_in(node, task.entry, env)
        for args, expected in found:
            examples.setdefault(repr(args), (args, expected))
    return list(examples.values())


def _signature(task: Task) -> tuple[str, str | None]:
    tree = ast.parse(task.reference_source())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == task.entry:
            params = node.args.posonlyargs + node.args.args
            return ast.unparse(node.args), (params[0].arg if params else None)
    return "*args, **kwargs", None


def build_probes(task: Task) -> list[Probe]:
    probes: list[Probe] = []

    examples = extract_examples(task)
    if examples:
        rows = "\n".join(
            f"    {repr(args)!r}: {expected!r}," for args, expected in examples
        )
        probes.append(Probe(
            id="memoriser",
            title=f"lookup table of the {len(examples)} example(s) written in the tests",
            source=(
                "# Knows only the examples that appear in the grader's tests.\n"
                f"_TABLE = {{\n{rows}\n}}\n\n\n"
                f"def {task.entry}(*args):\n"
                "    return _TABLE.get(repr(args))\n"
            ),
        ))

    signature, first = _signature(task)
    constants = [("none", "None"), ("zero", "0"), ("one", "1"), ("empty-string", "''"),
                 ("empty-list", "[]"), ("true", "True"), ("false", "False")]
    if first:
        constants.append(("echo", first))
    for name, expression in constants:
        probes.append(Probe(
            id=f"stub-{name}",
            title=f"ignores the task and always returns `{expression}`",
            source=f"def {task.entry}({signature}):\n    return {expression}\n",
        ))

    probes.append(Probe(
        id="empty",
        title="empty file with no function at all",
        source="# intentionally empty\n",
    ))
    return probes
