from pathlib import Path
import os
import py_compile
import subprocess
import sys

from symboliclight.codegen import generate_python
from symboliclight.checker import check_program
from symboliclight.parser import parse_source


ROOT = Path(__file__).resolve().parents[1]


def test_codegen_emits_valid_python(tmp_path: Path) -> None:
    source_path = ROOT / "examples" / "todo_app.sl"
    app = parse_source(source_path.read_text(encoding="utf-8"), path=str(source_path))
    output = tmp_path / "todo_app.py"
    output.write_text(generate_python(app), encoding="utf-8")

    py_compile.compile(str(output), doraise=True)


def test_generated_cli_add_and_list(tmp_path: Path) -> None:
    source_path = ROOT / "examples" / "todo_app.sl"
    app = parse_source(source_path.read_text(encoding="utf-8"), path=str(source_path))
    output = tmp_path / "todo_app.py"
    output.write_text(generate_python(app), encoding="utf-8")
    db_path = tmp_path / "todo.sqlite"

    add = subprocess.run(
        [sys.executable, str(output), "add", "Buy milk"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )
    listed = subprocess.run(
        [sys.executable, str(output), "list"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )

    assert "Buy milk" in add.stdout
    assert "Buy milk" in listed.stdout


def test_codegen_supports_imported_enum_store_and_source_comments(tmp_path: Path) -> None:
    source_path = ROOT / "examples" / "issue_tracker.sl"
    app = parse_source(source_path.read_text(encoding="utf-8"), path=str(source_path))
    diagnostics = check_program(app, source_path=source_path)
    output = tmp_path / "issue_tracker.py"
    generated = generate_python(app)
    output.write_text(generated, encoding="utf-8")
    db_path = tmp_path / "issue.sqlite"

    assert "# source:" in generated
    assert "def fn_models_is_open(status):" in generated
    py_compile.compile(str(output), doraise=True)

    created = subprocess.run(
        [sys.executable, str(output), "create", "First issue"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )
    listed = subprocess.run(
        [sys.executable, str(output), "list_open"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "First issue" in created.stdout
    assert "open" in listed.stdout
