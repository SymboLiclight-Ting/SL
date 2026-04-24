import json
from pathlib import Path

from symboliclight.lsp import (
    definition_at,
    diagnostics_for_document,
    document_symbols,
    formatting_edits,
    hover_at,
    path_from_uri,
)


def test_lsp_reports_diagnostics_for_invalid_file(tmp_path: Path) -> None:
    source = tmp_path / "bad.sl"
    text = """
app Bad {
  store items: Missing
}
"""

    diagnostics = diagnostics_for_document(source.as_uri(), text)

    assert any("Unknown type `Missing`" in diagnostic.message for diagnostic in diagnostics)


def test_lsp_hover_reports_route_body_field_type(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    text = """
app Demo {
  type CreateTodo = {
    title: Text,
  }

  route POST "/todos" body CreateTodo -> Text {
    return request.body.title
  }
}
"""
    line = next(index for index, item in enumerate(text.splitlines()) if "request.body.title" in item)
    character = text.splitlines()[line].index("title")

    hover = hover_at(source.as_uri(), text, line, character)

    assert hover is not None
    assert "`request.body.title: Text`" in json.dumps(hover)


def test_lsp_hover_uses_enclosing_route_body_type(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    text = """
app Demo {
  type FirstBody = {
    shared: Text,
  }

  type SecondBody = {
    shared: Int,
  }

  route POST "/first" body FirstBody -> Text {
    return request.body.shared
  }

  route POST "/second" body SecondBody -> Int {
    return request.body.shared
  }
}
"""
    lines = text.splitlines()
    line = [index for index, item in enumerate(lines) if "request.body.shared" in item][-1]
    character = lines[line].index("shared")

    hover = hover_at(source.as_uri(), text, line, character)

    assert hover is not None
    assert "`request.body.shared: Int`" in json.dumps(hover)


def test_lsp_document_symbols_cover_core_declarations(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    text = """
app Demo {
  enum Status { open, closed }
  type Item = { id: Id<Item>, title: Text, }
  config AppConfig = { port: Int = env_int("PORT", 8000), }
  store items: Item
  fixture items { { title: "x" } }
  fn ok() -> Bool { return true }
  command add(title: Text) -> Item { return items.insert({ title: title }) }
  route GET "/items" -> List<Item> { return items.all() }
  test "ok" { assert ok() == true }
}
"""

    names = {symbol["name"] for symbol in document_symbols(source.as_uri(), text)}

    assert {"Demo", "Status", "Item", "AppConfig", "items", "fixture items", "ok", "add", "GET /items", "ok"} <= names


def test_lsp_definition_resolves_imported_type(tmp_path: Path) -> None:
    module = tmp_path / "models.sl"
    module.write_text("module models { type Issue = { id: Id<Issue>, title: Text, } }", encoding="utf-8")
    source = tmp_path / "app.sl"
    text = """
app Demo {
  import "./models.sl" as models
  store issues: models.Issue
}
"""
    line = next(index for index, item in enumerate(text.splitlines()) if "models.Issue" in item)
    character = text.splitlines()[line].index("Issue")

    location = definition_at(source.as_uri(), text, line, character)

    assert location is not None
    assert location["uri"] == module.as_uri()
    assert location["range"]["start"]["line"] == 0


def test_lsp_formatting_refuses_comments(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    text = """
// keep this
app Demo {
}
""".lstrip()

    edits, error = formatting_edits(source.as_uri(), text)

    assert edits is None
    assert error is not None
    assert "comments" in error


def test_lsp_path_from_uri_preserves_posix_absolute_path() -> None:
    assert str(path_from_uri("file:///tmp/app.sl")).replace("\\", "/") == "/tmp/app.sl"


def test_lsp_path_from_uri_preserves_windows_drive_path() -> None:
    assert str(path_from_uri("file:///D:/tmp/app.sl")).replace("\\", "/") == "D:/tmp/app.sl"
