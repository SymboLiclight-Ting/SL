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


def test_codegen_emits_handlers_for_all_checked_http_methods(tmp_path: Path) -> None:
    source = """
app HttpMethods {
  route DELETE "/items" -> Text {
    return "deleted"
  }

  route PATCH "/items" -> Text {
    return "patched"
  }

  route PUT "/items" -> Text {
    return "put"
  }
}
"""
    app_path = tmp_path / "methods.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    generated = generate_python(app)
    output = tmp_path / "methods.py"
    output.write_text(generated, encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "def do_DELETE(self):" in generated
    assert "def do_PATCH(self):" in generated
    assert "def do_PUT(self):" in generated
    py_compile.compile(str(output), doraise=True)


def test_codegen_runs_nested_module_function_imports(tmp_path: Path) -> None:
    (tmp_path / "base.sl").write_text(
        """
module base {
  fn yes() -> Bool {
    return true
  }
}
""",
        encoding="utf-8",
    )
    (tmp_path / "mid.sl").write_text(
        """
module mid {
  import "./base.sl" as base

  fn pass() -> Bool {
    return base.yes()
  }
}
""",
        encoding="utf-8",
    )
    source = """
app Nested {
  import "./mid.sl" as mid

  command check() -> Bool {
    return mid.pass()
  }

  test "nested module fn" {
    assert mid.pass() == true
  }
}
"""
    app_path = tmp_path / "app.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    generated = generate_python(app)
    output = tmp_path / "app.py"
    output.write_text(generated, encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "def fn_mid_base_yes():" in generated
    assert "def fn_mid_pass():" in generated
    py_compile.compile(str(output), doraise=True)
    completed = subprocess.run(
        [sys.executable, str(output), "test"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ok - 1 test(s) passed" in completed.stdout
