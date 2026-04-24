import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VSCODE = ROOT / "editors" / "vscode"


def test_vscode_extension_metadata_is_valid_json() -> None:
    package = json.loads((VSCODE / "package.json").read_text(encoding="utf-8"))
    grammar = json.loads((VSCODE / "syntaxes" / "symboliclight.tmLanguage.json").read_text(encoding="utf-8"))
    snippets = json.loads((VSCODE / "snippets" / "symboliclight.json").read_text(encoding="utf-8"))

    assert package["contributes"]["languages"][0]["id"] == "symboliclight"
    assert ".sl" in package["contributes"]["languages"][0]["extensions"]
    assert package["contributes"]["grammars"][0]["scopeName"] == "source.sl"
    assert "app|module|import" in grammar["repository"]["keywords"]["patterns"][0]["match"]
    assert {"app", "type", "store", "command", "route GET", "route POST body", "test"} <= set(snippets)
