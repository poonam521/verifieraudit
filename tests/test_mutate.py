import ast

from verifieraudit.mutate import generate_mutants

SOURCE = '''
def clamp(x, low, high):
    """Keep x between low and high."""
    if x < low:
        return low
    if x > high and True:
        return high
    return x + 0
'''


def _descriptions(source=SOURCE):
    return [m.description for m in generate_mutants(source)]


def test_each_mutant_is_valid_python_and_differs_from_the_original():
    mutants = generate_mutants(SOURCE)
    original = ast.unparse(ast.parse(SOURCE))
    assert mutants
    for mutant in mutants:
        assert ast.unparse(ast.parse(mutant.source)) != original
    assert len({m.source for m in mutants}) == len(mutants)
    assert len({m.id for m in mutants}) == len(mutants)


def test_expected_edit_kinds_are_generated():
    text = "\n".join(_descriptions())
    assert "line 4: `<` changed to `<=`" in text
    assert "line 6: `>` changed to `>=`" in text
    assert "`and` changed to `or`" in text
    assert "`+` changed to `-`" in text
    assert "`0` changed to `1`" in text
    assert "`True` changed to `False`" in text
    assert "condition `x < low` negated" in text
    assert "`return low` changed to `return None`" in text


def test_docstrings_are_left_alone():
    assert not any("Keep x" in d for d in _descriptions())


def test_exactly_one_edit_per_mutant():
    source = "def f(a, b):\n    return a < b\n"
    sources = {m.source.strip() for m in generate_mutants(source)}
    assert sources == {
        "def f(a, b):\n    return a <= b",
        "def f(a, b):\n    return None",
    }


def test_augmented_assignment_and_strings():
    source = "def f(n):\n    n += 2\n    return 'x' * n\n"
    text = "\n".join(_descriptions(source))
    assert "`+` changed to `-`" in text
    assert "`'x'` changed to `''`" in text
