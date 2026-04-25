from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os

from symboliclight.cli import main


def test_cli_exit_codes_for_check_build_test_schema_doctor_and_migrate(tmp_path: Path) -> None:
    valid = tmp_path / "valid.sl"
    valid.write_text(
        """
app Valid {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  test "ok" {
    assert true
  }
}
""",
        encoding="utf-8",
    )
    invalid = tmp_path / "invalid.sl"
    invalid.write_text("app Broken { store items: Missing }", encoding="utf-8")

    assert main(["check", str(valid)]) == 0
    assert main(["check", str(invalid)]) == 1
    assert main(["build", str(valid), "--out", str(tmp_path / "valid.py")]) == 0
    assert main(["build", str(invalid), "--out", str(tmp_path / "invalid.py")]) == 1
    assert main(["test", str(valid)]) == 0
    assert main(["test", str(invalid)]) == 1
    assert main(["schema", str(valid), "--out", str(tmp_path / "schema.json")]) == 0
    assert main(["schema", str(invalid), "--out", str(tmp_path / "bad_schema.json")]) == 1
    assert main(["doctor", str(valid)]) == 0
    assert main(["doctor", str(invalid)]) == 1
    assert main(["migrate", "plan", str(valid), "--db", str(tmp_path / "missing.sqlite")]) == 0


def test_cli_exit_codes_for_fmt_new_and_add(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "app.sl"
    source.write_text('app Demo { route GET "/ok" -> Text { return "ok" } }', encoding="utf-8")
    commented = tmp_path / "commented.sl"
    commented.write_text('// note\napp Demo { route GET "/ok" -> Text { return "ok" } }', encoding="utf-8")

    assert main(["fmt", str(source)]) == 0
    assert main(["fmt", str(source), "--check"]) == 0
    assert main(["add", "route", "GET", "/health", str(source)]) == 0
    assert main(["add", "route", "GET", "/blocked", str(commented)]) == 1

    monkeypatch.chdir(tmp_path)
    assert main(["new", "api", "ok"]) == 0
    assert main(["new", "api", "bad", "--template", "todo", "--backend", "postgres"]) == 1


def test_argparse_errors_return_two() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "symboliclight.cli"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )

    assert completed.returncode == 2
