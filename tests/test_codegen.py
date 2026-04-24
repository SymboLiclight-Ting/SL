from pathlib import Path
import json
import os
import py_compile
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from symboliclight.codegen import generate_python, generate_python_artifact
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


def test_codegen_emits_source_map() -> None:
    source_path = ROOT / "examples" / "todo_app.sl"
    app = parse_source(source_path.read_text(encoding="utf-8"), path=str(source_path))
    artifact = generate_python_artifact(app, generated_path="build/todo_app.py")

    assert artifact.source_map["version"] == 1
    assert artifact.source_map["generated"] == "build/todo_app.py"
    assert artifact.source_map["line_map"]
    assert "cmd_add" in artifact.source_map["symbols"]


def test_generated_test_failure_reports_sl_source(tmp_path: Path) -> None:
    source = """
app Failing {
  test "fails" {
    assert false
  }
}
"""
    app_path = tmp_path / "failing.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    output = tmp_path / "failing.py"
    output.write_text(generate_python(app), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(output), "test"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert f"SL source: {app_path}:3:1" in completed.stderr


def test_generated_http_handles_typed_body_response_and_bad_json(tmp_path: Path) -> None:
    source = """
app HttpBody {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  route POST "/todos" body CreateTodo -> Response<Todo> {
    let item = todos.insert({ title: request.body.title, done: false })
    return response(status: 201, body: item)
  }
}
"""
    app_path = tmp_path / "http_body.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "http_body.py"
    output.write_text(generate_python(app), encoding="utf-8")
    db_path = tmp_path / "http.sqlite"
    port = free_port()

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    server = subprocess.Popen(
        [sys.executable, str(output), "serve", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )
    try:
        wait_for_server(port)
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/todos",
            data=b'{"title": "Buy milk"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 201
            assert payload["title"] == "Buy milk"

        bad_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/todos",
            data=b'{"title":',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(bad_request, timeout=5)
            raise AssertionError("expected malformed JSON to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            error_payload = json.loads(exc.read().decode("utf-8"))
            assert error_payload["error"] == "malformed JSON body"

        missing_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/todos",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(missing_request, timeout=5)
            raise AssertionError("expected missing field to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            error_payload = json.loads(exc.read().decode("utf-8"))
            assert error_payload["fields"] == ["title"]
    finally:
        server.terminate()
        server.wait(timeout=10)


def test_generated_tests_load_fixtures_and_check_golden(tmp_path: Path) -> None:
    golden_dir = tmp_path / "golden"
    golden_dir.mkdir()
    (golden_dir / "todos.json").write_text(
        """[
  {
    "done": false,
    "id": 1,
    "title": "Buy milk"
  }
]""",
        encoding="utf-8",
    )
    source = """
app Fixtures {
  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  fixture todos {
    { title: "Buy milk", done: false }
  }

  test "fixture count" {
    assert todos.count() == 1
  }

  test "golden list" golden "./golden/todos.json" {
    return todos.all()
  }
}
"""
    app_path = tmp_path / "fixtures.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "fixtures.py"
    output.write_text(generate_python(app), encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    completed = subprocess.run(
        [sys.executable, str(output), "test"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ok - 2 test(s) passed" in completed.stdout
    assert not (golden_dir / "todos.json.actual").exists()


def test_codegen_sanitizes_route_handler_names(tmp_path: Path) -> None:
    source = """
app Routes {
  route GET "/items/{id}" -> Text {
    return "item"
  }

  route GET "/a-b" -> Text {
    return "dash"
  }

  route GET "/a_b" -> Text {
    return "underscore"
  }
}
"""
    app_path = tmp_path / "routes.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "routes.py"
    generated = generate_python(app)
    output.write_text(generated, encoding="utf-8")

    handler_lines = [line for line in generated.splitlines() if line.startswith("def route_get_a_b_")]

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "def route_get_items_id_" in generated
    assert len(handler_lines) == 2
    assert len(set(handler_lines)) == 2
    py_compile.compile(str(output), doraise=True)


def test_generated_store_quotes_sqlite_identifiers(tmp_path: Path) -> None:
    source = """
app SqlKeywords {
  type Item = {
    id: Id<Item>,
    order: Text,
  }

  store select: Item

  test "sqlite keywords" {
    let item = select.insert({ order: "first" })
    select.filter(order: "first")
    let updated = select.update(item.id, { order: "second" })
    assert updated.order == "second"
    assert select.exists(item.id) == true
    assert select.delete(item.id) == true
  }
}
"""
    app_path = tmp_path / "sql_keywords.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "sql_keywords.py"
    output.write_text(generate_python(app), encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    completed = subprocess.run(
        [sys.executable, str(output), "test"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ok - 1 test(s) passed" in completed.stdout


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/missing", timeout=0.2):
                return
        except urllib.error.HTTPError:
            return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("server did not start")
