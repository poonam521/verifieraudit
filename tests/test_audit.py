import json

import pytest

from verifieraudit import report
from verifieraudit.audit import Config, audit_task
from verifieraudit.task import discover_tasks

from conftest import EXAMPLES

CFG = Config(samples=150)


@pytest.fixture(scope="module")
def audits():
    return {task.name: audit_task(task, CFG) for task in discover_tasks(EXAMPLES)}


def test_strong_grader_passes(audits):
    audit = audits["leap_year_strong"]
    assert audit.passed and not audit.issues
    assert audit.wrong_mutants >= 20 and not audit.false_accepts
    assert audit.valid_alternates == 2 and not audit.false_rejects
    assert not audit.exploits and not audit.leaks


def test_untested_boundaries_are_reported_with_the_missing_input(audits):
    audit = audits["shipping_fee_boundaries"]
    assert not audit.passed
    assert audit.false_accept_rate > 0.2
    by_title = {m.title: m for m in audit.false_accepts}
    boundary = by_title["line 8: `<=` changed to `<`"]
    assert (boundary.call, boundary.expected, boundary.got) == ("shipping_fee(5)", "7.5", "15.0")


def test_overstrict_grader_rejects_correct_solutions(audits):
    audit = audits["chunk_overstrict"]
    assert not audit.false_accepts
    assert {a.id for a in audit.false_rejects} == {"inline_check.py", "loop_different_message.py"}
    assert {a.id for a in audit.alternates if a.status == "accepted"} == {"same_shape.py"}
    assert any("rejects correct solutions" in issue for issue in audit.issues)


def test_gameable_grader_and_leak_are_reported(audits):
    audit = audits["roman_gameable"]
    assert [p.id for p in audit.exploits] == ["memoriser"]
    assert {leak.kind for leak in audit.leaks} == {"solution-in-files", "grader-visible"}
    assert any("can be cheated" in issue for issue in audit.issues)
    assert any("answer leaked" in issue for issue in audit.issues)


def test_property_test_blind_spot_including_a_hang(audits):
    audit = audits["binary_search_blindspot"]
    assert not audit.passed and not audit.exploits
    # Every miss is a search for an absent value (expected is blank when the
    # comparison itself timed out, which is how hangs show up on Windows).
    assert all(m.expected in ("-1", "") for m in audit.false_accepts)
    assert any("does not finish" in m.got for m in audit.false_accepts)


def test_reports_render(audits):
    ordered = [audits[name] for name in sorted(audits)]
    data = json.loads(report.to_json(ordered, CFG))
    assert [t["verdict"] for t in data["tasks"]] == ["FAIL", "FAIL", "PASS", "FAIL", "FAIL"]
    markdown = report.to_markdown(ordered, CFG)
    assert "## leap_year_strong: PASS" in markdown
    assert "| line 8: `<=` changed to `<` | `shipping_fee(5)` | `7.5` | `15.0` |" in markdown
    console = report.to_console(ordered)
    assert "1 of 5 graders passed the audit." in console


def test_invalid_task_is_reported_not_crashed(make_task):
    task = make_task("def f(x):\n    return x\n",
                     "from solution import f\n\ndef test_a():\n    assert f(1) == 2\n")
    audit = audit_task(task, CFG)
    assert not audit.passed and "fails its own grader" in audit.error


def test_thresholds_are_configurable(make_task):
    solution = "def f(x):\n    if x > 10:\n        return 10\n    return x\n"
    tests = ("from solution import f\n\ndef test_a():\n    assert f(50) == 10\n"
             "    for x in range(-5, 10):\n        assert f(x) == x\n")
    task = make_task(solution, tests)
    strict = audit_task(task, Config(samples=100))
    assert strict.false_accepts and not strict.passed
    lenient = audit_task(task, Config(samples=100, max_false_accept=1.0))
    assert lenient.passed and lenient.warnings
