import json

from verifieraudit.cli import main

from conftest import EXAMPLES


def test_init_then_audit(tmp_path, capsys):
    target = tmp_path / "new_task"
    assert main(["init", str(target)]) == 0
    assert (target / "task.toml").is_file()
    assert main(["init", str(target)]) == 2  # refuses to overwrite

    out = tmp_path / "report"
    code = main(["audit", str(target), "--out", str(out), "--samples", "50", "--strict"])
    printed = capsys.readouterr().out
    # The starter test checks a single example, so the starter grader is weak.
    assert code == 1
    assert "FAIL" in printed
    data = json.loads((out / "report.json").read_text())
    assert data["tasks"][0]["name"] == "my_task"
    assert (out / "report.md").read_text().startswith("# VerifierAudit report")


def test_strict_exit_codes(tmp_path):
    strong = EXAMPLES / "leap_year_strong"
    assert main(["audit", str(strong), "--out", str(tmp_path / "a"), "--samples", "50", "--strict"]) == 0
    weak = EXAMPLES / "roman_gameable"
    assert main(["audit", str(weak), "--out", str(tmp_path / "b"), "--samples", "50"]) == 0
    assert main(["audit", str(weak), "--out", str(tmp_path / "c"), "--samples", "50", "--strict"]) == 1


def test_missing_folder(tmp_path, capsys):
    assert main(["audit", str(tmp_path / "nope")]) == 2
    assert "error:" in capsys.readouterr().err
