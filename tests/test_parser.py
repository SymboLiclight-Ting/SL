from pathlib import Path

import pytest

from symboliclight.ast import App, Module
from symboliclight.diagnostics import SymbolicLightError
from symboliclight.parser import parse_source


ROOT = Path(__file__).resolve().parents[1]


def test_parser_accepts_todo_app() -> None:
    source = (ROOT / "examples" / "todo_app.sl").read_text(encoding="utf-8")
    app = parse_source(source, path="examples/todo_app.sl")

    assert app.name == "TodoApp"
    assert len(app.types) == 1
    assert len(app.stores) == 1
    assert len(app.routes) == 2
    assert len(app.tests) == 1


def test_parser_accepts_module_import_enum_and_intent_test() -> None:
    module_source = (ROOT / "examples" / "models.sl").read_text(encoding="utf-8")
    module = parse_source(module_source, path="examples/models.sl")

    assert isinstance(module, Module)
    assert module.enums[0].name == "Status"

    app_source = (ROOT / "examples" / "issue_tracker.sl").read_text(encoding="utf-8")
    app = parse_source(app_source, path="examples/issue_tracker.sl")

    assert isinstance(app, App)
    assert app.imports[0].alias == "models"
    assert app.tests[0].external_ref == "intent.acceptance"


def test_parser_rejects_malformed_block() -> None:
    with pytest.raises(SymbolicLightError):
        parse_source("app Broken { type Todo = { id: Id<Todo> }", path="broken.sl")
