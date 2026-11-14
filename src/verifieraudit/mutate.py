"""Generate small, plausible-looking wrong versions ("mutants") of a solution.

Each mutant differs from the original by exactly one edit: a flipped
comparison, a swapped arithmetic operator, an off-by-one constant, a negated
condition, and so on. These are the mistakes real code (and real agents)
make, so a grader that cannot tell them apart from the correct solution is
accepting wrong answers.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Mutant:
    id: str
    operator: str
    lineno: int
    description: str
    source: str


_COMPARE = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
}
_ARITH = {
    ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.Div: ast.Mult,
    ast.FloorDiv: ast.Mult, ast.Mod: ast.FloorDiv, ast.Pow: ast.Mult,
}
_BOOL = {ast.And: ast.Or, ast.Or: ast.And}
_SYMBOL = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==",
    ast.NotEq: "!=", ast.In: "in", ast.NotIn: "not in", ast.Is: "is",
    ast.IsNot: "is not", ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
    ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**", ast.And: "and", ast.Or: "or",
}

Edit = tuple[str, str, Callable[[ast.AST], None]]


def _constant_variants(value: object) -> list[object]:
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, int):
        return [value + 1, value - 1]
    if isinstance(value, float):
        return [value + 1.0]
    if isinstance(value, str):
        return [""] if value else ["mutant"]
    return []


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    ids.add(id(body[0].value))
    return ids


def _edits(node: ast.AST, skip: set[int]) -> list[Edit]:
    edits: list[Edit] = []
    if isinstance(node, ast.Compare):
        for index, op in enumerate(node.ops):
            new = _COMPARE.get(type(op))
            if new is not None:
                edits.append((
                    "comparison",
                    f"`{_SYMBOL[type(op)]}` changed to `{_SYMBOL[new]}`",
                    lambda n, index=index, new=new: n.ops.__setitem__(index, new()),
                ))
    elif isinstance(node, (ast.BinOp, ast.AugAssign)):
        new = _ARITH.get(type(node.op))
        if new is not None:
            edits.append((
                "arithmetic",
                f"`{_SYMBOL[type(node.op)]}` changed to `{_SYMBOL[new]}`",
                lambda n, new=new: setattr(n, "op", new()),
            ))
    elif isinstance(node, ast.BoolOp):
        new = _BOOL[type(node.op)]
        edits.append((
            "boolean",
            f"`{_SYMBOL[type(node.op)]}` changed to `{_SYMBOL[new]}`",
            lambda n, new=new: setattr(n, "op", new()),
        ))
    elif isinstance(node, ast.Constant) and id(node) not in skip:
        for value in _constant_variants(node.value):
            edits.append((
                "constant",
                f"`{node.value!r}` changed to `{value!r}`",
                lambda n, value=value: setattr(n, "value", value),
            ))
    if isinstance(node, (ast.If, ast.While, ast.IfExp)):
        edits.append((
            "negate-condition",
            f"condition `{ast.unparse(node.test)}` negated",
            lambda n: setattr(n, "test", ast.UnaryOp(op=ast.Not(), operand=n.test)),
        ))
    if isinstance(node, ast.Return) and node.value is not None:
        if not (isinstance(node.value, ast.Constant) and node.value.value is None):
            edits.append((
                "return-none",
                f"`return {ast.unparse(node.value)}` changed to `return None`",
                lambda n: setattr(n, "value", ast.Constant(value=None)),
            ))
    return edits


def generate_mutants(source: str) -> list[Mutant]:
    """Return every distinct single-edit mutant of ``source``."""
    tree = ast.parse(source)
    original = ast.unparse(tree)
    skip = _docstring_ids(tree)
    nodes = list(ast.walk(tree))

    mutants: list[Mutant] = []
    seen = {original}
    for position, node in enumerate(nodes):
        for edit_index, (operator, description, _) in enumerate(_edits(node, skip)):
            clone = copy.deepcopy(tree)
            target = list(ast.walk(clone))[position]
            # Recompute the edit against the clone so it mutates the copy.
            clone_skip = _docstring_ids(clone)
            _edits(target, clone_skip)[edit_index][2](target)
            ast.fix_missing_locations(clone)
            mutated = ast.unparse(clone)
            if mutated in seen:
                continue
            seen.add(mutated)
            lineno = getattr(node, "lineno", 0)
            mutants.append(Mutant(
                id=f"m{len(mutants) + 1:03d}",
                operator=operator,
                lineno=lineno,
                description=f"line {lineno}: {description}",
                source=mutated + "\n",
            ))
    return mutants
