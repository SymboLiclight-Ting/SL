from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from symboliclight.ast import App, FieldDecl, TypeDecl, Unit
from symboliclight.checker import check_program_result
from symboliclight.cli_support import contains_line_comment_source
from symboliclight.diagnostics import Diagnostic, SourceLocation
from symboliclight.formatter import format_unit
from symboliclight.parser import parse_source_result


WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


def run_lsp_server() -> None:
    server = LspServer()
    server.run()


class LspServer:
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}

    def run(self) -> None:
        while True:
            message = self.read_message()
            if message is None:
                return
            response = self.handle(message)
            if response is not None:
                self.write_message(response)

    def handle(self, message: dict[str, object]) -> dict[str, object] | None:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "hoverProvider": True,
                        "definitionProvider": True,
                        "documentSymbolProvider": True,
                        "documentFormattingProvider": True,
                    }
                },
            }
        if method == "shutdown":
            return {"jsonrpc": "2.0", "id": request_id, "result": None}
        if method == "exit":
            return None
        if method == "textDocument/didOpen":
            text_document = params.get("textDocument") if isinstance(params, dict) else {}
            if isinstance(text_document, dict):
                uri = str(text_document.get("uri", ""))
                text = str(text_document.get("text", ""))
                self.documents[uri] = text
                self.publish_diagnostics(uri, text)
            return None
        if method == "textDocument/didChange":
            text_document = params.get("textDocument") if isinstance(params, dict) else {}
            changes = params.get("contentChanges") if isinstance(params, dict) else []
            if isinstance(text_document, dict) and isinstance(changes, list) and changes:
                uri = str(text_document.get("uri", ""))
                change = changes[-1]
                if isinstance(change, dict):
                    text = str(change.get("text", ""))
                    self.documents[uri] = text
                    self.publish_diagnostics(uri, text)
            return None
        if method == "textDocument/hover":
            uri, text, line, character = self.document_position(params)
            return {"jsonrpc": "2.0", "id": request_id, "result": hover_at(uri, text, line, character)}
        if method == "textDocument/definition":
            uri, text, line, character = self.document_position(params)
            return {"jsonrpc": "2.0", "id": request_id, "result": definition_at(uri, text, line, character)}
        if method == "textDocument/documentSymbol":
            uri, text, _, _ = self.document_position(params)
            return {"jsonrpc": "2.0", "id": request_id, "result": document_symbols(uri, text)}
        if method == "textDocument/formatting":
            uri, text, _, _ = self.document_position(params)
            result, error = formatting_edits(uri, text)
            if error is not None:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32001, "message": error}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        if request_id is not None:
            return {"jsonrpc": "2.0", "id": request_id, "result": None}
        return None

    def document_position(self, params: object) -> tuple[str, str, int, int]:
        if not isinstance(params, dict):
            return "", "", 0, 0
        text_document = params.get("textDocument") if isinstance(params.get("textDocument"), dict) else {}
        position = params.get("position") if isinstance(params.get("position"), dict) else {}
        uri = str(text_document.get("uri", "")) if isinstance(text_document, dict) else ""
        text = self.documents.get(uri)
        if text is None:
            path = path_from_uri(uri)
            text = path.read_text(encoding="utf-8") if path.exists() else ""
        line = int(position.get("line", 0)) if isinstance(position, dict) else 0
        character = int(position.get("character", 0)) if isinstance(position, dict) else 0
        return uri, text, line, character

    def publish_diagnostics(self, uri: str, text: str) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": uri, "diagnostics": [diagnostic_to_lsp(item) for item in diagnostics_for_document(uri, text)]},
        }
        self.write_message(payload)

    def read_message(self) -> dict[str, object] | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if line == b"":
                return None
            if line in {b"\r\n", b"\n"}:
                break
            name, _, value = line.decode("ascii").partition(":")
            headers[name.lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))

    def write_message(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()


def diagnostics_for_document(uri: str, text: str) -> list[Diagnostic]:
    path = path_from_uri(uri)
    parse_result = parse_source_result(text, path=str(path))
    diagnostics = list(parse_result.diagnostics)
    if parse_result.unit is None or any(item.severity == "error" for item in diagnostics):
        return diagnostics
    diagnostics.extend(check_program_result(parse_result.unit, source_path=path).diagnostics)
    return diagnostics


def hover_at(uri: str, text: str, line: int, character: int) -> dict[str, object] | None:
    token = token_at(text, line, character)
    if token is None:
        return None
    unit = parsed_unit(uri, text)
    if unit is None:
        return None
    type_name = infer_hover_type(unit, token)
    if type_name is None:
        return None
    return {"contents": {"kind": "markdown", "value": f"`{token}: {type_name}`"}}


def infer_hover_type(unit: Unit, token: str) -> str | None:
    if isinstance(unit, App) and token.startswith("request.body."):
        field_name = token.split(".")[-1]
        for route in unit.routes:
            if route.body_type is None:
                continue
            type_decl = find_type(unit, route.body_type.name)
            field = find_field(type_decl, field_name) if type_decl else None
            if field is not None:
                return field.type_ref.render()
    for type_decl in unit.types:
        if token == type_decl.name:
            return "type"
    for enum_decl in unit.enums:
        if token == enum_decl.name:
            return "enum"
    for function in unit.functions:
        if token == function.name:
            return function.return_type.render()
        for param in function.params:
            if token == param.name:
                return param.type_ref.render()
    if isinstance(unit, App):
        for route in unit.routes:
            if token == route.function_name:
                return route.return_type.render()
    return None


def document_symbols(uri: str, text: str) -> list[dict[str, object]]:
    unit = parsed_unit(uri, text)
    if unit is None:
        return []
    symbols = [symbol(unit.name, 2, unit.location)]
    for item in unit.imports:
        symbols.append(symbol(item.alias, 13, item.location))
    for item in unit.types:
        symbols.append(symbol(item.name, 23, item.location))
    for item in unit.enums:
        symbols.append(symbol(item.name, 10, item.location))
    if isinstance(unit, App):
        for item in unit.configs:
            symbols.append(symbol(item.name, 13, item.location))
        for item in unit.stores:
            symbols.append(symbol(item.name, 13, item.location))
        for item in unit.fixtures:
            symbols.append(symbol(f"fixture {item.store_name}", 13, item.location))
    for item in unit.functions:
        symbols.append(symbol(item.name, 12, item.location))
    if isinstance(unit, App):
        for item in unit.routes:
            symbols.append(symbol(f"{item.method} {item.path}", 12, item.location))
        for item in unit.tests:
            symbols.append(symbol(item.name, 12, item.location))
    return symbols


def definition_at(uri: str, text: str, line: int, character: int) -> dict[str, object] | None:
    token = token_at(text, line, character)
    if token is None:
        return None
    unit = parsed_unit(uri, text)
    if unit is None:
        return None
    location = local_definition(unit, token, uri)
    if location is not None:
        return location
    parts = token.split(".")
    if len(parts) < 2:
        return None
    alias, name = parts[0], parts[1]
    import_decl = next((item for item in unit.imports if item.alias == alias), None)
    if import_decl is None:
        return None
    import_path = (path_from_uri(uri).parent / import_decl.path).resolve()
    if not import_path.exists():
        return None
    imported = parsed_unit(import_path.as_uri(), import_path.read_text(encoding="utf-8"))
    if imported is None:
        return None
    return local_definition(imported, name, import_path.as_uri())


def formatting_edits(uri: str, text: str) -> tuple[list[dict[str, object]] | None, str | None]:
    if contains_line_comment_source(text):
        return None, "SL formatter refuses to rewrite files with // comments in v0.5."
    result = parse_source_result(text, path=str(path_from_uri(uri)))
    if result.unit is None or any(item.severity == "error" for item in result.diagnostics):
        return None, "Fix parser errors before formatting."
    formatted = format_unit(result.unit)
    if formatted == text:
        return [], None
    line_count = len(text.splitlines())
    end_character = len(text.splitlines()[-1]) if text.splitlines() else 0
    return [
        {
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": line_count, "character": end_character}},
            "newText": formatted,
        }
    ], None


def parsed_unit(uri: str, text: str) -> Unit | None:
    result = parse_source_result(text, path=str(path_from_uri(uri)))
    if result.unit is None or any(item.severity == "error" for item in result.diagnostics):
        return None
    return result.unit


def local_definition(unit: Unit, token: str, uri: str) -> dict[str, object] | None:
    candidates: list[tuple[str, SourceLocation]] = [(unit.name, unit.location)]
    candidates.extend((item.name, item.location) for item in unit.types)
    candidates.extend((item.name, item.location) for item in unit.enums)
    candidates.extend((item.name, item.location) for item in unit.functions)
    if isinstance(unit, App):
        candidates.extend((item.name, item.location) for item in unit.stores)
        candidates.extend((item.name, item.location) for item in unit.configs)
    match = next((location for name, location in candidates if name == token), None)
    if match is None:
        return None
    return {"uri": uri, "range": location_range(match)}


def find_type(unit: Unit, name: str) -> TypeDecl | None:
    return next((item for item in unit.types if item.name == name), None)


def find_field(type_decl: TypeDecl | None, name: str) -> FieldDecl | None:
    if type_decl is None:
        return None
    return next((field for field in type_decl.fields if field.name == name), None)


def token_at(text: str, line: int, character: int) -> str | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    source_line = lines[line]
    for match in WORD_RE.finditer(source_line):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def symbol(name: str, kind: int, location: SourceLocation) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "range": location_range(location),
        "selectionRange": location_range(location),
    }


def location_range(location: SourceLocation) -> dict[str, object]:
    line = max(location.line - 1, 0)
    column = max(location.column - 1, 0)
    return {
        "start": {"line": line, "character": column},
        "end": {"line": line, "character": column + 1},
    }


def diagnostic_to_lsp(diagnostic: Diagnostic) -> dict[str, object]:
    return {
        "range": location_range(diagnostic.location),
        "severity": 1 if diagnostic.severity == "error" else 2,
        "code": diagnostic.code,
        "source": "slc",
        "message": diagnostic.message,
        "data": {"suggestion": diagnostic.suggestion},
    }


def path_from_uri(uri: str) -> Path:
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        return Path(unquote(parsed.path.lstrip("/")) if parsed.netloc == "" else f"//{parsed.netloc}{unquote(parsed.path)}")
    return Path(uri or "<memory>").resolve()
