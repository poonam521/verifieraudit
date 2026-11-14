from verifieraudit import oracle, runner

GOOD = "def f(x):\n    return abs(x)\n"
TESTS = """
    from solution import f

    def test_positive():
        assert f(3) == 3
"""


def _compare(task, source, **kwargs):
    return oracle.compare(task, source, samples=100, seed=0, timeout=kwargs.get("timeout", 10))


def test_grader_passes_and_fails(make_task):
    task = make_task(GOOD, TESTS)
    assert runner.grade(task, GOOD).passed
    result = runner.grade(task, "def f(x):\n    return 0\n")
    assert not result.passed and not result.timed_out
    assert "assert" in result.output


def test_grader_timeout_counts_as_failure(make_task):
    task = make_task(GOOD, TESTS, timeout=2)
    result = runner.grade(task, "def f(x):\n    while True:\n        pass\n")
    assert result.timed_out and not result.passed


def test_oracle_finds_a_counterexample(make_task):
    task = make_task(GOOD, TESTS)
    result = _compare(task, "def f(x):\n    return x\n")
    assert not result.equivalent
    assert result.call.startswith("f(-")
    assert result.got.startswith("-")


def test_oracle_accepts_a_different_but_correct_solution(make_task):
    task = make_task(GOOD, TESTS)
    assert _compare(task, "def f(x):\n    return x if x >= 0 else -x\n").equivalent


def test_oracle_compares_exception_types(make_task):
    reference = "def f(x):\n    if x < 0:\n        raise ValueError('negative')\n    return x\n"
    task = make_task(reference, "from solution import f\n\ndef test_ok():\n    assert f(1) == 1\n")
    other_message = reference.replace("negative", "below zero")
    assert _compare(task, other_message).equivalent
    assert not _compare(task, reference.replace("ValueError", "KeyError")).equivalent


def test_oracle_edge_cases_and_custom_equality(make_task):
    inputs = """
        EDGE_CASES = [(1000,)]

        def generate(rng):
            return (rng.randint(0, 5),)

        def same(expected, got):
            return sorted(expected) == sorted(got)
    """
    reference = "def f(n):\n    return list(range(n))\n"
    task = make_task(reference, "from solution import f\n\ndef test_ok():\n    assert f(1) == [0]\n",
                     inputs=inputs)
    assert _compare(task, "def f(n):\n    return list(range(n))[::-1]\n").equivalent
    only_edge = "def f(n):\n    return [] if n == 1000 else list(range(n))\n"
    result = _compare(task, only_edge)
    assert not result.equivalent and result.call == "f(1000)"


def test_oracle_handles_hangs_crashes_and_missing_functions(make_task):
    task = make_task(GOOD, TESTS)
    hang = _compare(task, "def f(x):\n    while x == 7:\n        pass\n    return abs(x)\n")
    assert not hang.equivalent and "does not finish" in hang.got
    assert not _compare(task, "def g(x):\n    return x\n").equivalent
    assert not _compare(task, "this is not python").equivalent
    assert not _compare(task, "import os\nos._exit(3)\n").equivalent


def test_oracle_does_not_let_candidates_mutate_shared_inputs(make_task):
    inputs = "def generate(rng):\n    return ([3, 1, 2],)\n"
    reference = "def f(items):\n    return sorted(items)\n"
    task = make_task(reference, "from solution import f\n\ndef test_ok():\n    assert f([2, 1]) == [1, 2]\n",
                     inputs=inputs)
    in_place = "def f(items):\n    items.sort()\n    return items\n"
    assert _compare(task, in_place).equivalent
