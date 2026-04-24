from pathlib import Path

from symboliclight.checker import check_program
from symboliclight.parser import parse_source


ROOT = Path(__file__).resolve().parents[1]


def parse_fixture(name: str):
    path = ROOT / "examples" / name
    return parse_source(path.read_text(encoding="utf-8"), path=str(path)), path


def test_checker_accepts_todo_app() -> None:
    app, path = parse_fixture("todo_app.sl")
    diagnostics = check_program(app, source_path=path)

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_accepts_imported_issue_tracker() -> None:
    app, path = parse_fixture("issue_tracker.sl")
    diagnostics = check_program(app, source_path=path)

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_rejects_unknown_store_type() -> None:
    source = """
app Bad {
  store todos: Missing
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Unknown type `Missing`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_missing_intent() -> None:
    source = """
app Bad {
  intent "./missing.intent.yaml"
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=ROOT / "examples" / "bad.sl")

    assert any("IntentSpec file not found" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_store_call_inside_fn() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  fn load() -> List<Todo> {
    return todos.all()
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Pure fn cannot call store method" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_route_calling_command() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title })
  }

  route POST "/todos" -> Todo {
    return add(request.body.title)
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("cannot be called from `route`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_unknown_record_field() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, extra: false })
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("has no field `extra`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_store_insert_without_record_literal() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert(title)
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Store insert requires a record literal" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_filter_value_type_mismatch() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command find() -> List<Todo> {
    return todos.filter(done: "no")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Filter `done` expected `Bool`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_bad_store_id_argument() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command load(title: Text) -> Option<Todo> {
    return todos.get(title)
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("id expected `Int`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_named_args_for_non_filter_store_methods() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command load() -> Option<Todo> {
    return todos.get(id: 1)
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("does not accept named arguments" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_duplicate_import_alias(tmp_path: Path) -> None:
    (tmp_path / "models.sl").write_text("module models { fn ok() -> Bool { return true } }", encoding="utf-8")
    source = """
app Bad {
  import "./models.sl" as models
  import "./models.sl" as models
}
"""
    path = tmp_path / "bad.sl"
    path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(path))
    diagnostics = check_program(app, source_path=path)

    assert any("Duplicate import alias `models`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_import_alias_collision(tmp_path: Path) -> None:
    (tmp_path / "models.sl").write_text("module models { fn ok() -> Bool { return true } }", encoding="utf-8")
    source = """
app Bad {
  import "./models.sl" as Item

  type Item = {
    id: Id<Item>,
  }
}
"""
    path = tmp_path / "bad.sl"
    path.write_text(source, encoding="utf-8")
    app = parse_source(source, path=str(path))
    diagnostics = check_program(app, source_path=path)

    assert any("conflicts with a local declaration" in diagnostic.message for diagnostic in diagnostics)


def test_checker_supports_function_named_arguments() -> None:
    source = """
app Good {
  fn join(left: Text, right: Text) -> Text {
    return left
  }

  test "named args" {
    assert join(right: "b", left: "a") == "a"
  }
}
"""
    app = parse_source(source, path="good.sl")
    diagnostics = check_program(app, source_path=Path("good.sl"))

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_rejects_bad_named_arguments() -> None:
    source = """
app Bad {
  fn join(left: Text, right: Text) -> Text {
    return left
  }

  test "bad named args" {
    assert join(left: "a", left: "b", extra: "c") == "a"
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("provided more than once" in diagnostic.message for diagnostic in diagnostics)
    assert any("has no parameter `extra`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_duplicate_record_field() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, title: "again" })
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("provided more than once" in diagnostic.message for diagnostic in diagnostics)


def test_checker_accepts_option_and_result_constructors() -> None:
    source = """
app Good {
  fn maybe(flag: Bool) -> Option<Text> {
    if flag {
      return some("yes")
    } else {
      return none()
    }
  }

  fn result(flag: Bool) -> Result<Text, Text> {
    if flag {
      return ok("yes")
    } else {
      return err("no")
    }
  }
}
"""
    app = parse_source(source, path="good.sl")
    diagnostics = check_program(app, source_path=Path("good.sl"))

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_rejects_get_route_body() -> None:
    source = """
app Bad {
  type Query = {
    title: Text,
  }

  route GET "/items" body Query -> Text {
    return request.body.title
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("GET routes cannot declare" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_delete_route_body() -> None:
    source = """
app Bad {
  type DeleteBody = {
    reason: Text,
  }

  route DELETE "/items" body DeleteBody -> Bool {
    return true
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("DELETE routes cannot declare" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_unknown_route_body_field() -> None:
    source = """
app Bad {
  type CreateTodo = {
    title: Text,
  }

  route POST "/todos" body CreateTodo -> Text {
    return request.body.missing
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("has no field `missing`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_response_body_mismatch() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  route POST "/todos" -> Response<Todo> {
    return response(status: 201, body: "wrong")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Return type mismatch" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_response_record_literal_missing_field() -> None:
    source = """
app Bad {
  type PublicTodo = {
    title: Text,
    done: Bool,
  }

  route GET "/todo" -> Response<PublicTodo> {
    return response(status: 200, body: { title: "Buy milk" })
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Missing required field `done`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_response_record_literal_unknown_field() -> None:
    source = """
app Bad {
  type PublicTodo = {
    title: Text,
    done: Bool,
  }

  route GET "/todo" -> Response<PublicTodo> {
    return response(status: 200, body: { title: "Buy milk", done: false, extra: true })
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("has no field `extra`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_accepts_response_record_literal_matching_target() -> None:
    source = """
app Good {
  type PublicTodo = {
    title: Text,
    done: Bool,
  }

  route GET "/todo" -> Response<PublicTodo> {
    return response(status: 200, body: { title: "Buy milk", done: false })
  }
}
"""
    app = parse_source(source, path="good.sl")
    diagnostics = check_program(app, source_path=Path("good.sl"))

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_accepts_request_header_in_routes() -> None:
    source = """
app Good {
  config AdminConfig = {
    admin_token: Text = env("ADMIN_TOKEN", "dev-token"),
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
    app = parse_source(source, path="good.sl")
    diagnostics = check_program(app, source_path=Path("good.sl"))

    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]


def test_checker_rejects_request_header_outside_routes() -> None:
    source = """
app Bad {
  command bad() -> Option<Text> {
    return request.header("Authorization")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("`request.header` is only allowed in route blocks" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_request_header_non_text_name() -> None:
    source = """
app Bad {
  route GET "/secure" -> Option<Text> {
    return request.header(123)
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Argument `name` expected `Text`, found `Int`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_request_header_unknown_named_arg() -> None:
    source = """
app Bad {
  route GET "/secure" -> Option<Text> {
    return request.header(value: "Authorization")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Builtin `request.header` has no argument `value`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_validates_fixture_records() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  fixture todos {
    { name: "wrong" }
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("has no field `name`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_allows_clear_only_in_tests() -> None:
    source = """
app Bad {
  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  command clear_all() -> Int {
    return todos.clear()
  }

  test "clear" {
    assert todos.clear() == 0
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("only allowed in tests" in diagnostic.message for diagnostic in diagnostics)


def test_checker_enforces_write_text_boundary() -> None:
    source = """
app Bad {
  route POST "/write" -> Bool {
    return write_text("out.txt", "body")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("write_text" in diagnostic.message and "command and test" in diagnostic.message for diagnostic in diagnostics)


def test_checker_enforces_read_text_boundary() -> None:
    source = """
app Bad {
  config AppConfig = {
    content: Text = read_text("settings.txt"),
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("read_text" in diagnostic.message and "command, route, and test" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_unknown_builtin_named_arg() -> None:
    source = """
app Bad {
  command load() -> Text {
    return env(foo: "SL_NAME", default: "app")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Builtin `env` has no argument `foo`" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_duplicate_builtin_named_arg() -> None:
    source = """
app Bad {
  route POST "/items" -> Response<Text> {
    return response(status: 200, status: 201, body: "ok")
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Argument `status` is provided more than once" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_python_keyword_parameters() -> None:
    source = """
app Bad {
  command bad(class: Text) -> Text {
    return class
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Parameter `class` conflicts with a Python reserved word" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_python_keyword_locals() -> None:
    source = """
app Bad {
  command bad() -> Text {
    let class = "bad"
    return class
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Local variable `class` conflicts with a Python reserved word" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_generated_cli_command_names() -> None:
    source = """
app Bad {
  command test() -> Text {
    return "bad"
  }

  command serve() -> Text {
    return "bad"
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Command `test` conflicts with a generated CLI command" in diagnostic.message for diagnostic in diagnostics)
    assert any("Command `serve` conflicts with a generated CLI command" in diagnostic.message for diagnostic in diagnostics)


def test_checker_rejects_duplicate_routes() -> None:
    source = """
app Bad {
  route GET "/items" -> Text {
    return "one"
  }

  route GET "/items" -> Text {
    return "two"
  }
}
"""
    app = parse_source(source, path="bad.sl")
    diagnostics = check_program(app, source_path=Path("bad.sl"))

    assert any("Duplicate route `GET /items`" in diagnostic.message for diagnostic in diagnostics)
