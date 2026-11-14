import subprocess

from verifieraudit import leaks, probes

SOLUTION = """
    def f(a, b=0):
        total = a + b
        result = total * 2
        return result
"""


def test_examples_are_extracted_from_asserts_and_parametrize(make_task):
    tests = """
        import pytest
        import solution
        from solution import f

        def test_direct():
            assert f(1, 2) == 6
            assert 4 == solution.f(2)
            assert f(compute()) == 1      # not a literal: ignored

        @pytest.mark.parametrize("a, b, expected", [(5, 5, 20), (0, 1, 2)])
        def test_table(a, b, expected):
            assert f(a, b) == expected
    """
    task = make_task(SOLUTION, tests)
    examples = dict((args, expected) for args, expected in probes.extract_examples(task))
    assert examples == {(1, 2): 6, (2,): 4, (5, 5): 20, (0, 1): 2}


def test_memoriser_reproduces_the_examples_and_nothing_else(make_task):
    task = make_task(SOLUTION, "from solution import f\n\ndef test_a():\n    assert f(1, 2) == 6\n")
    built = {probe.id: probe for probe in probes.build_probes(task)}
    namespace = {}
    exec(built["memoriser"].source, namespace)
    assert namespace["f"](1, 2) == 6
    assert namespace["f"](9, 9) is None
    assert "def f(a, b=0):" in built["stub-zero"].source
    assert built["stub-echo"].source.strip().endswith("return a")
    assert "empty" in built


def test_no_memoriser_without_literal_examples(make_task):
    task = make_task(SOLUTION, "from solution import f\n\ndef test_a():\n    assert f(1) > 0\n")
    assert "memoriser" not in {probe.id for probe in probes.build_probes(task)}


def test_leak_scan_finds_solution_copy_and_visible_tests(make_task):
    tests = "from solution import f\n\ndef test_a():\n    assert f(1, 2) == 6\n"
    task = make_task(SOLUTION, tests, visible={
        "README.md": "Write f(a, b).\n",
        "old/backup.txt": SOLUTION,
        "tests/test_solution.py": tests,
    })
    found = {(leak.kind, leak.path, leak.severity) for leak in leaks.scan(task)}
    assert found == {
        ("solution-in-files", "old/backup.txt", "high"),
        ("grader-visible", "tests/test_solution.py", "medium"),
    }


def test_leak_scan_is_quiet_when_nothing_is_leaked(make_task):
    task = make_task(SOLUTION, "from solution import f\n\ndef test_a():\n    assert f(1) == 2\n",
                     visible={"README.md": "Write f(a, b) that returns twice the sum.\n"})
    assert leaks.scan(task) == []
    assert leaks.scan(make_task(SOLUTION, "from solution import f\n")) == []


def test_leak_scan_reads_git_history(make_task):
    task = make_task(SOLUTION, "from solution import f\n\ndef test_a():\n    assert f(1) == 2\n",
                     visible={"README.md": "Write f.\n", "solution.py": SOLUTION})
    repo = task.visible_dir

    def git(*args):
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                        *args], check=True, capture_output=True)

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "add solution")
    (repo / "solution.py").write_text("# TODO: implement f\n")
    git("commit", "-q", "-am", "remove solution")

    kinds = {leak.kind for leak in leaks.scan(task)}
    assert kinds == {"solution-in-git-history"}
