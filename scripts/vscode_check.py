from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VSCODE = ROOT / "editors" / "vscode"


def main() -> int:
    errors: list[str] = []
    package = load_json(VSCODE / "package.json", errors)
    load_json(VSCODE / "syntaxes" / "symboliclight.tmLanguage.json", errors)
    snippets = load_json(VSCODE / "snippets" / "symboliclight.json", errors)
    load_json(VSCODE / "language-configuration.json", errors)
    if package:
        contributes = package.get("contributes", {})
        languages = contributes.get("languages", [])
        if not any(language.get("id") == "symboliclight" for language in languages):
            errors.append("VS Code extension must contribute language id symboliclight")
        grammars = contributes.get("grammars", [])
        if not any(grammar.get("scopeName") == "source.sl" for grammar in grammars):
            errors.append("VS Code grammar must use scopeName source.sl")
        if package.get("version") != "1.0.0":
            errors.append("VS Code extension version must be 1.0.0")
    if snippets is not None and not snippets:
        errors.append("VS Code snippets file must not be empty")
    extension = VSCODE / "extension.js"
    if not extension.exists():
        errors.append("VS Code extension.js is missing")
    elif "slc" not in extension.read_text(encoding="utf-8"):
        errors.append("VS Code extension.js must launch slc")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("ok - VS Code extension check passed")
    return 0


def load_json(path: Path, errors: list[str]) -> object | None:
    if not path.exists():
        errors.append(f"missing {path.relative_to(ROOT)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return None


if __name__ == "__main__":
    raise SystemExit(main())
