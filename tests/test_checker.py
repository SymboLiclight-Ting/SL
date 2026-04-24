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
