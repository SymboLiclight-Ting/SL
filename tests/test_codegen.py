from pathlib import Path
import http.client
import importlib.util
import json
import os
import py_compile
import queue
import sqlite3
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from symboliclight.codegen import generate_python, generate_python_artifact, generate_schema_hash
from symboliclight.checker import check_program
from symboliclight.parser import parse_source


ROOT = Path(__file__).resolve().parents[1]


def test_codegen_emits_valid_python(tmp_path: Path) -> None:
    source_path = ROOT / "examples" / "todo_app.sl"
    app = parse_source(source_path.read_text(encoding="utf-8"), path=str(source_path))
    output = tmp_path / "todo_app.py"
    output.write_text(generate_python(app), encoding="utf-8")

    py_compile.compile(str(output), doraise=True)


def test_codegen_emits_postgres_backend_sql(tmp_path: Path) -> None:
    source = """
app PgDemo {
  type Item = {
    id: Id<Item>,
    title: Text,
    done: Bool,
  }

  store items: Item using postgres

  command add(title: Text) -> Item {
    return items.insert({ title: title, done: false })
  }
}
"""
    app = parse_source(source, path="pg_demo.sl")
    diagnostics = check_program(app, source_path=Path("pg_demo.sl"))
    generated = generate_python(app)
    output = tmp_path / "pg_demo.py"
    output.write_text(generated, encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "SL_DB_BACKEND = 'postgres'" in generated
    assert "import psycopg" in generated
    assert "RETURNING \"id\"" in generated
    assert "%s" in generated
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
    server, thread = start_generated_http_server(output, port, env={"SL_DB": str(db_path)})
    try:
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
            assert error_payload == {
                "error": {
                    "code": "bad_request",
                    "message": "Request body must be valid JSON.",
                }
            }

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
            assert error_payload == {
                "error": {
                    "code": "bad_request",
                    "message": "Missing required body field(s): title.",
                }
            }

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.putrequest("POST", "/todos")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", "1000001")
        conn.endheaders()
        response = conn.getresponse()
        assert response.status == 413
        error_payload = json.loads(response.read().decode("utf-8"))
        assert error_payload["error"]["code"] == "payload_too_large"
        conn.close()

        unsupported = urllib.request.Request(
            f"http://127.0.0.1:{port}/todos",
            method="TRACE",
        )
        try:
            urllib.request.urlopen(unsupported, timeout=5)
            raise AssertionError("expected unsupported method to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 405
            error_payload = json.loads(exc.read().decode("utf-8"))
            assert error_payload["error"]["code"] == "method_not_allowed"
    finally:
        stop_generated_http_server(server, thread)


def test_generated_http_runtime_exception_returns_stable_error(tmp_path: Path) -> None:
    source = """
app RuntimeHttpError {
  route GET "/boom" -> Text {
    return read_text("")
  }
}
"""
    app_path = tmp_path / "runtime_http_error.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "runtime_http_error.py"
    output.write_text(generate_python(app), encoding="utf-8")
    port = free_port()

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    db_path = tmp_path / "runtime_http_error.sqlite"
    server, thread = start_generated_http_server(output, port, env={"SL_DB": str(db_path)})
    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/boom", timeout=5)
            raise AssertionError("expected runtime exception to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 500
            assert json.loads(exc.read().decode("utf-8")) == {
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error.",
                }
            }
    finally:
        stop_generated_http_server(server, thread)


def test_generated_http_reads_request_headers(tmp_path: Path) -> None:
    source = """
app HeaderAuth {
  config AdminConfig = {
    admin_token: Text = env("ADMIN_TOKEN", "secret"),
  }

  route GET "/secure" -> Response<Text> {
    if request.header("Authorization") == some(AdminConfig.admin_token) {
      return response(status: 200, body: "ok")
    } else {
      return response(status: 401, body: "unauthorized")
    }
  }
}
"""
    app_path = tmp_path / "header_auth.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    diagnostics = check_program(app, source_path=app_path)
    output = tmp_path / "header_auth.py"
    output.write_text(generate_python(app), encoding="utf-8")
    port = free_port()

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    db_path = tmp_path / "header_auth.sqlite"
    server, thread = start_generated_http_server(
        output,
        port,
        env={"ADMIN_TOKEN": "secret", "SL_DB": str(db_path)},
    )
    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/secure", timeout=5)
            raise AssertionError("expected missing auth to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
            assert json.loads(exc.read().decode("utf-8")) == "unauthorized"

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/secure",
            headers={"Authorization": "secret"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.status == 200
            assert json.loads(response.read().decode("utf-8")) == "ok"
    finally:
        stop_generated_http_server(server, thread)


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


def test_generated_cli_parses_id_params_as_int(tmp_path: Path) -> None:
    source = """
app IdCli {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  command has_item(id: Id<Item>) -> Bool {
    return items.exists(id)
  }
}
"""
    app = parse_source(source, path="id_cli.sl")
    diagnostics = check_program(app, source_path=Path("id_cli.sl"))
    output = tmp_path / "id_cli.py"
    generated = generate_python(app)
    output.write_text(generated, encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    assert "has_item_parser.add_argument('id', type=int)" in generated
    py_compile.compile(str(output), doraise=True)
    completed = subprocess.run(
        [sys.executable, str(output), "has_item", "1"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "false" in completed.stdout


def test_generated_update_missing_id_fails_explicitly(tmp_path: Path) -> None:
    source = """
app MissingUpdate {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  command missing() -> Item {
    return items.update(999, { title: "ghost" })
  }
}
"""
    app = parse_source(source, path="missing_update.sl")
    diagnostics = check_program(app, source_path=Path("missing_update.sl"))
    output = tmp_path / "missing_update.py"
    output.write_text(generate_python(app), encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    completed = subprocess.run(
        [sys.executable, str(output), "missing"],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "items.update id not found: 999" in completed.stderr


def test_generated_try_update_returns_none_for_missing_id(tmp_path: Path) -> None:
    source = """
app TryUpdateRuntime {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  test "try update" {
    let item = items.insert({ title: "first" })
    let updated = items.try_update(item.id, { title: "second" })
    assert updated.title == "second"
    assert items.try_update(999, { title: "ghost" }) == none()
  }
}
"""
    app = parse_source(source, path="try_update_runtime.sl")
    diagnostics = check_program(app, source_path=Path("try_update_runtime.sl"))
    output = tmp_path / "try_update_runtime.py"
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


def test_generated_file_builtins_reject_empty_and_directory_paths(tmp_path: Path) -> None:
    source = """
app FileGuards {
  command read_empty() -> Text {
    return read_text("")
  }

  command write_dir(path: Text) -> Bool {
    return write_text(path, "content")
  }
}
"""
    app = parse_source(source, path="file_guards.sl")
    diagnostics = check_program(app, source_path=Path("file_guards.sl"))
    output = tmp_path / "file_guards.py"
    output.write_text(generate_python(app), encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    empty = subprocess.run(
        [sys.executable, str(output), "read_empty"],
        capture_output=True,
        text=True,
    )
    directory = subprocess.run(
        [sys.executable, str(output), "write_dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert empty.returncode != 0
    assert "file path must be a non-empty Text value" in empty.stderr
    assert directory.returncode != 0
    assert "file path points to a directory" in directory.stderr


def test_generated_response_helpers_return_result_payloads(tmp_path: Path) -> None:
    source = """
app ResponseHelpers {
  type ErrorBody = {
    code: Text,
    message: Text,
  }

  type Item = {
    title: Text,
  }

  route GET "/ok" -> Response<Result<Item, ErrorBody>> {
    return response_ok(status: 201, body: { title: "created" })
  }

  route GET "/err" -> Response<Result<Item, ErrorBody>> {
    return response_err(status: 404, code: "not_found", message: "Missing item.")
  }
}
"""
    app = parse_source(source, path="response_helpers.sl")
    diagnostics = check_program(app, source_path=Path("response_helpers.sl"))
    output = tmp_path / "response_helpers.py"
    output.write_text(generate_python(app), encoding="utf-8")

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    py_compile.compile(str(output), doraise=True)
    port = free_port()
    db_path = tmp_path / "response_helpers.sqlite"
    server, thread = start_generated_http_server(output, port, env={"SL_DB": str(db_path)})
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ok", timeout=5) as response:
            assert response.status == 201
            assert json.loads(response.read().decode("utf-8")) == {"ok": {"title": "created"}}
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/err", timeout=5)
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
            assert json.loads(exc.read().decode("utf-8")) == {
                "err": {"code": "not_found", "message": "Missing item."}
            }
    finally:
        stop_generated_http_server(server, thread)


def test_generated_schema_drift_does_not_overwrite_existing_hash(tmp_path: Path) -> None:
    source = """
app DriftRuntime {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  command count() -> Int {
    return items.count()
  }
}
"""
    app_path = tmp_path / "drift_runtime.sl"
    app_path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(app_path))
    output = tmp_path / "drift_runtime.py"
    output.write_text(generate_python(app), encoding="utf-8")
    db_path = tmp_path / "drift.sqlite"
    old_hash = "old-schema-hash"
    database = sqlite3.connect(db_path)
    try:
        database.execute("CREATE TABLE sl_migrations (version INTEGER PRIMARY KEY, schema_hash TEXT NOT NULL)")
        database.execute("INSERT INTO sl_migrations (version, schema_hash) VALUES (1, ?)", [old_hash])
        database.commit()
    finally:
        database.close()

    completed = subprocess.run(
        [sys.executable, str(output), "count"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "SL_DB": str(db_path)},
    )

    database = sqlite3.connect(db_path)
    try:
        stored = database.execute("SELECT schema_hash FROM sl_migrations WHERE version = 1").fetchone()[0]
    finally:
        database.close()

    assert "schema drift detected" in completed.stderr
    assert "v0.8" not in completed.stderr
    assert stored == old_hash
    assert stored != generate_schema_hash(app)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_generated_http_server(
    output: Path,
    port: int,
    *,
    env: dict[str, str] | None = None,
) -> tuple[object, threading.Thread]:
    module = load_generated_module(output, env=env)
    errors: queue.Queue[BaseException] = queue.Queue()
    ready = threading.Event()
    server_holder: dict[str, object] = {}
    original_http_server = module.HTTPServer

    class TrackingHTTPServer(original_http_server):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            server_holder["server"] = self
            ready.set()

    def run() -> None:
        module.HTTPServer = TrackingHTTPServer
        old_env = patch_env(env)
        try:
            module.serve("127.0.0.1", port)
        except BaseException as exc:
            errors.put(exc)
            ready.set()
        finally:
            restore_env(old_env)
            module.HTTPServer = original_http_server
            server = server_holder.get("server")
            if server is not None:
                server.server_close()
            connection = getattr(module, "CONN", None)
            if connection is not None:
                connection.close()
                module.CONN = None

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    if not ready.wait(timeout=15):
        raise AssertionError("server thread did not create an HTTP server")
    if not errors.empty():
        raise AssertionError(f"server thread exited during startup: {errors.get()!r}")

    server = server_holder.get("server")
    if server is None:
        raise AssertionError("server thread did not expose an HTTP server")
    wait_for_server(port)
    return server, thread


def stop_generated_http_server(server: object, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=5)
    if thread.is_alive():
        raise AssertionError("server thread did not stop")


def load_generated_module(output: Path, *, env: dict[str, str] | None = None) -> object:
    old_env = patch_env(env)
    try:
        module_name = f"_sl_generated_{output.stem}_{time.time_ns()}"
        spec = importlib.util.spec_from_file_location(module_name, output)
        if spec is None or spec.loader is None:
            raise AssertionError(f"could not load generated module: {output}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        restore_env(old_env)


def patch_env(env: dict[str, str] | None) -> dict[str, str | None]:
    old_env: dict[str, str | None] = {}
    for key, value in (env or {}).items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    return old_env


def restore_env(old_env: dict[str, str | None]) -> None:
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def wait_for_server(port: int) -> None:
    deadline = time.time() + 15
    last_error: OSError | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    detail = f": {last_error}" if last_error is not None else ""
    raise AssertionError(f"server did not start{detail}")
