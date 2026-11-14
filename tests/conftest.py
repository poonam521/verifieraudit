import textwrap
from pathlib import Path

import pytest

from verifieraudit.task import load_task

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "tasks"


@pytest.fixture
def make_task(tmp_path):
    """Build a small task folder on the fly and load it."""

    made = []

    def build(solution, tests, *, entry="f", inputs=None, alternates=None, visible=None, timeout=10):
        root = tmp_path / f"task{len(made) or ''}"
        made.append(root)
        (root / "tests").mkdir(parents=True)
        config = f'entry = "{entry}"\ntimeout = {timeout}\n'
        if visible is not None:
            config += 'visible = "visible"\n'
            for name, content in visible.items():
                path = root / "visible" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(content))
        (root / "task.toml").write_text(config)
        (root / "solution.py").write_text(textwrap.dedent(solution))
        (root / "tests" / "test_solution.py").write_text(textwrap.dedent(tests))
        (root / "inputs.py").write_text(textwrap.dedent(
            inputs or "def generate(rng):\n    return (rng.randint(-20, 20),)\n"
        ))
        for name, content in (alternates or {}).items():
            (root / "alternates").mkdir(exist_ok=True)
            (root / "alternates" / name).write_text(textwrap.dedent(content))
        return load_task(root)

    return build
