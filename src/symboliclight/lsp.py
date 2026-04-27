from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import url2pathname
from urllib.parse import unquote, urlparse

from symboliclight.ast import (
    App,
    BinaryExpr,
    CallExpr,
    Expr,
    FieldDecl,
    IfStmt,
    LetStmt,
    ListExpr,
    LiteralExpr,
    Param,
    PathExpr,
    Stmt,
    StoreDecl,
    TypeDecl,
    TypeRef,
    Unit,
)
from symboliclight.checker import check_program_result
from symboliclight.diagnostics import Diagnostic, SourceLocation
from symboliclight.formatter import format_source
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
    type_name = infer_hover_type(unit, token, line=line)
    if type_name is None:
        return None
    return {"contents": {"kind": "markdown", "value": f"`{token}: {type_name}`"}}


def infer_hover_type(unit: Unit, token: str, *, line: int | None = None) -> str | None:
    if isinstance(unit, App) and token.startswith("request.body."):
        field_name = token.split(".")[-1]
        route = route_at_line(unit, line) if line is not None else None
        if route is None or route.body_type is None:
            return None
        type_decl = find_type(unit, route.body_type.name)
        field = find_field(type_decl, field_name) if type_decl else None
        return field.type_ref.render() if field is not None else None
    env = scoped_env_at_line(unit, line)
    local_type = type_for_path_parts(unit, token.split("."), env)
    if local_type is not None:
        return local_type.render()
    parts = token.split(".")
    if len(parts) == 2:
        config_type = config_field_type(unit, parts[0], parts[1])
        if config_type is not None:
            return config_type.render()
        store_type = store_method_type(unit, parts[0], parts[1])
        if store_type is not None:
            return store_type.render()
        enum_type = enum_variant_type(unit, parts[0], parts[1])
        if enum_type is not None:
            return enum_type
    if len(parts) == 3 and parts[0] in unit.imported_modules:
        imported = unit.imported_modules[parts[0]]
        enum_type = enum_variant_type(imported, parts[1], parts[2])
        if enum_type is not None:
            return f"{parts[0]}.{enum_type}"
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
        for store in unit.stores:
            if token == store.name:
                return f"store {store.type_ref.render()}"
        for config in unit.configs:
            if token == config.name:
                return "config"
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
    part_index = token_part_index_at(text, line, character)
    if part_index is not None and part_index > 0:
        field = field_definition_at_line(unit, token, line)
        if field is not None:
            return {"uri": uri, "range": location_range(field.location)}
    local = scoped_definition_at_line(unit, token, line)
    if local is not None:
        return {"uri": uri, "range": location_range(local)}
    field = field_definition_at_line(unit, token, line)
    if field is not None:
        return {"uri": uri, "range": location_range(field.location)}
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
    result = parse_source_result(text, path=str(path_from_uri(uri)))
    if result.unit is None or any(item.severity == "error" for item in result.diagnostics):
        return None, "Fix parser errors before formatting."
    formatted = format_source(text, path=str(path_from_uri(uri)))
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
        candidates.extend((item.function_name, item.location) for item in unit.routes)
        candidates.extend((f"{item.method} {item.path}", item.location) for item in unit.routes)
    if "." in token:
        parts = token.split(".")
        if len(parts) == 2:
            candidates.extend((f"{enum.name}.{variant}", enum.location) for enum in unit.enums for variant in enum.variants)
            if isinstance(unit, App):
                candidates.extend((f"{store.name}.{method}", store.location) for store in unit.stores for method in ("insert", "all", "get", "update", "try_update", "delete", "filter", "count", "exists", "clear"))
                candidates.extend((f"{config.name}.{field.name}", config.location) for config in unit.configs for field in config.fields)
        if len(parts) == 3:
            candidates.extend((f"{alias}.{enum.name}.{variant}", enum.location) for alias, module in unit.imported_modules.items() for enum in module.enums for variant in enum.variants)
    match = next((location for name, location in candidates if name == token), None)
    if match is None:
        return None
    return {"uri": uri, "range": location_range(match)}


def find_type(unit: Unit, name: str) -> TypeDecl | None:
    local = next((item for item in unit.types if item.name == name), None)
    if local is not None:
        return local
    if "." in name:
        alias, type_name = name.split(".", 1)
        module = unit.imported_modules.get(alias)
        if module is not None:
            return next((item for item in module.types if item.name == type_name), None)
    return None


def find_field(type_decl: TypeDecl | None, name: str) -> FieldDecl | None:
    if type_decl is None:
        return None
    return next((field for field in type_decl.fields if field.name == name), None)


def config_field_type(unit: Unit, config_name: str, field_name: str) -> TypeRef | None:
    if not isinstance(unit, App):
        return None
    config = next((item for item in unit.configs if item.name == config_name), None)
    if config is None:
        return None
    field = next((item for item in config.fields if item.name == field_name), None)
    return field.type_ref if field is not None else None


def store_method_type(unit: Unit, store_name: str, method: str) -> TypeRef | None:
    if not isinstance(unit, App):
        return None
    store = next((item for item in unit.stores if item.name == store_name), None)
    if store is None:
        return None
    return store_helper_return_type(store, method)


def store_helper_return_type(store: StoreDecl, method: str) -> TypeRef | None:
    item_type = store.type_ref
    if method in {"insert", "update"}:
        return item_type
    if method == "try_update" or method == "get":
        return TypeRef("Option", [item_type])
    if method == "all" or method == "filter":
        return TypeRef("List", [item_type])
    if method == "count" or method == "clear":
        return TypeRef("Int")
    if method in {"exists", "delete"}:
        return TypeRef("Bool")
    return None


def enum_variant_type(unit: Unit, enum_name: str, variant: str) -> str | None:
    enum_decl = next((item for item in unit.enums if item.name == enum_name), None)
    if enum_decl is None or variant not in enum_decl.variants:
        return None
    return enum_name


def scoped_env_at_line(unit: Unit, zero_based_line: int | None) -> dict[str, TypeRef]:
    if zero_based_line is None:
        return {}
    scope = enclosing_scope(unit, zero_based_line)
    if scope is None:
        return {}
    body, params = scope
    env = {param.name: param.type_ref for param in params}
    collect_let_types(unit, body, zero_based_line + 1, env)
    return env


def scoped_definition_at_line(unit: Unit, token: str, zero_based_line: int | None) -> SourceLocation | None:
    if zero_based_line is None:
        return None
    name = token.split(".", 1)[0]
    scope = enclosing_scope(unit, zero_based_line)
    if scope is None:
        return None
    body, params = scope
    param = next((item for item in params if item.name == name), None)
    if param is not None:
        return param.location
    return latest_let_location(body, name, zero_based_line + 1)


def field_definition_at_line(unit: Unit, token: str, zero_based_line: int | None) -> FieldDecl | None:
    if zero_based_line is None or "." not in token:
        return None
    env = scoped_env_at_line(unit, zero_based_line)
    parts = token.split(".")
    current = env.get(parts[0])
    field: FieldDecl | None = None
    for part in parts[1:]:
        type_decl = find_type(unit, current.name) if current is not None else None
        field = find_field(type_decl, part)
        if field is None:
            return None
        current = field.type_ref
    return field


def enclosing_scope(unit: Unit, zero_based_line: int) -> tuple[list[Stmt], list[Param]] | None:
    one_based_line = zero_based_line + 1
    candidates: list[tuple[int, list[Stmt], list[Param]]] = []
    for function in unit.functions:
        if function.location.line <= one_based_line:
            candidates.append((function.location.line, function.body, list(function.params)))
    if isinstance(unit, App):
        for route in unit.routes:
            if route.location.line <= one_based_line:
                candidates.append((route.location.line, route.body, []))
        for test in unit.tests:
            if test.location.line <= one_based_line:
                candidates.append((test.location.line, test.body, []))
    if not candidates:
        return None
    _, body, params = max(candidates, key=lambda item: item[0])
    return body, params


def collect_let_types(unit: Unit, body: list[Stmt], one_based_line: int, env: dict[str, TypeRef]) -> None:
    for statement in body:
        if statement.location.line > one_based_line:
            continue
        if isinstance(statement, LetStmt):
            env[statement.name] = infer_expr_type(unit, statement.expr, env)
        elif isinstance(statement, IfStmt):
            collect_let_types(unit, statement.then_body, one_based_line, env)
            collect_let_types(unit, statement.else_body, one_based_line, env)


def latest_let_location(body: list[Stmt], name: str, one_based_line: int) -> SourceLocation | None:
    matches: list[SourceLocation] = []
    for statement in body:
        if statement.location.line > one_based_line:
            continue
        if isinstance(statement, LetStmt) and statement.name == name:
            matches.append(statement.location)
        elif isinstance(statement, IfStmt):
            nested = latest_let_location(statement.then_body, name, one_based_line)
            if nested is not None:
                matches.append(nested)
            nested = latest_let_location(statement.else_body, name, one_based_line)
            if nested is not None:
                matches.append(nested)
    return max(matches, key=lambda location: location.line) if matches else None


def infer_expr_type(unit: Unit, expr: Expr, env: dict[str, TypeRef]) -> TypeRef:
    if isinstance(expr, LiteralExpr):
        if isinstance(expr.value, bool):
            return TypeRef("Bool")
        if isinstance(expr.value, int):
            return TypeRef("Int")
        if isinstance(expr.value, float):
            return TypeRef("Float")
        if isinstance(expr.value, str):
            return TypeRef("Text")
        return TypeRef("Unknown")
    if isinstance(expr, ListExpr):
        return TypeRef("List", [infer_expr_type(unit, expr.items[0], env) if expr.items else TypeRef("Unknown")])
    if isinstance(expr, BinaryExpr):
        return TypeRef("Bool")
    if isinstance(expr, PathExpr):
        return type_for_path_parts(unit, expr.parts, env) or TypeRef("Unknown")
    if isinstance(expr, CallExpr):
        return infer_call_type(unit, expr, env)
    return TypeRef("Unknown")


def infer_call_type(unit: Unit, expr: CallExpr, env: dict[str, TypeRef]) -> TypeRef:
    if expr.callee == ["request", "header"]:
        return TypeRef("Option", [TypeRef("Text")])
    if len(expr.callee) == 2:
        store_type = store_method_type(unit, expr.callee[0], expr.callee[1])
        if store_type is not None:
            return store_type
    if len(expr.callee) == 1:
        name = expr.callee[0]
        first = infer_expr_type(unit, expr.args[0].expr, env) if expr.args else TypeRef("Unknown")
        if name == "some":
            return TypeRef("Option", [first])
        if name == "none":
            return TypeRef("Option", [TypeRef("Unknown")])
        if name == "ok":
            return TypeRef("Result", [first, TypeRef("Unknown")])
        if name == "err":
            return TypeRef("Result", [TypeRef("Unknown"), first])
        if name in {"env", "uuid", "now", "read_text"}:
            return TypeRef("Text")
        if name == "env_int":
            return TypeRef("Int")
        if name == "write_text":
            return TypeRef("Bool")
        if name == "response":
            body = builtin_arg_expr(expr, "body", positional_index=1)
            return TypeRef("Response", [infer_expr_type(unit, body, env) if body is not None else TypeRef("Unknown")])
        if name == "response_ok":
            body = builtin_arg_expr(expr, "body", positional_index=1)
            ok_type = infer_expr_type(unit, body, env) if body is not None else TypeRef("Unknown")
            return TypeRef("Response", [TypeRef("Result", [ok_type, TypeRef("Unknown")])])
        if name == "response_err":
            body = builtin_arg_expr(expr, "body", positional_index=1)
            err_type = infer_expr_type(unit, body, env) if body is not None else TypeRef("Unknown")
            return TypeRef("Response", [TypeRef("Result", [TypeRef("Unknown"), err_type])])
        function = next((item for item in unit.functions if item.name == name), None)
        if function is not None:
            return function.return_type
        if name in {item.name for item in unit.types}:
            return TypeRef(name)
    if expr.callee and expr.callee[0] in unit.imported_modules:
        imported = unit.imported_modules[expr.callee[0]]
        function = next((item for item in imported.functions if item.name == expr.callee[1]), None) if len(expr.callee) == 2 else None
        if function is not None:
            return function.return_type
    return TypeRef("Unknown")


def builtin_arg_expr(expr: CallExpr, name: str, *, positional_index: int) -> Expr | None:
    for index, arg in enumerate(expr.args):
        if arg.name == name or (arg.name is None and index == positional_index):
            return arg.expr
    return None


def type_for_path_parts(unit: Unit, parts: list[str], env: dict[str, TypeRef]) -> TypeRef | None:
    if not parts:
        return None
    current = env.get(parts[0])
    if current is None:
        return None
    for part in parts[1:]:
        type_decl = find_type(unit, current.name)
        field = find_field(type_decl, part) if type_decl is not None else None
        if field is None:
            return None
        current = field.type_ref
    return current


def route_at_line(unit: App, zero_based_line: int | None) -> object | None:
    if zero_based_line is None:
        return None
    one_based_line = zero_based_line + 1
    candidates = [route for route in unit.routes if route.location.line <= one_based_line]
    if not candidates:
        return None
    return max(candidates, key=lambda route: route.location.line)


def token_at(text: str, line: int, character: int) -> str | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    source_line = lines[line]
    for match in WORD_RE.finditer(source_line):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def token_part_index_at(text: str, line: int, character: int) -> int | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    source_line = lines[line]
    for match in WORD_RE.finditer(source_line):
        if match.start() <= character <= match.end():
            prefix = source_line[match.start() : character + 1]
            return prefix.count(".")
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
        if parsed.netloc:
            return Path(url2pathname(f"//{parsed.netloc}{parsed.path}"))
        decoded = url2pathname(unquote(parsed.path))
        if len(decoded) >= 3 and decoded[0] == "/" and decoded[2] == ":":
            decoded = decoded[1:]
        return Path(decoded)
    return Path(uri or "<memory>").resolve()
