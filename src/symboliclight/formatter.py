from __future__ import annotations

import json
from dataclasses import dataclass, field

from symboliclight.ast import (
    App,
    AssertStmt,
    BinaryExpr,
    CallExpr,
    ConfigDecl,
    Expr,
    ExprStmt,
    FunctionDecl,
    FixtureDecl,
    IfStmt,
    LetStmt,
    ListExpr,
    LiteralExpr,
    Module,
    PathExpr,
    RecordExpr,
    ReturnStmt,
    RouteDecl,
    Stmt,
    TestDecl,
    TypeRef,
    Unit,
)
from symboliclight.diagnostics import SourceLocation
from symboliclight.parser import parse_source


def format_unit(unit: Unit) -> str:
    formatter = Formatter()
    return formatter.unit(unit)


def format_source(source: str, *, path: str = "<memory>") -> str:
    formatter = Formatter(collect_comment_trivia(source))
    return formatter.unit(parse_source(source, path=path))


@dataclass(slots=True)
class CommentTrivia:
    leading: dict[int, list[str]] = field(default_factory=dict)
    trailing: dict[int, str] = field(default_factory=dict)
    source_lines: dict[str, list[int]] = field(default_factory=dict)


def collect_comment_trivia(source: str) -> CommentTrivia:
    lines = source.splitlines()
    standalone: dict[int, str] = {}
    trailing: dict[int, str] = {}
    code_lines: set[int] = set()
    source_lines: dict[str, list[int]] = {}
    for index, line in enumerate(lines, start=1):
        comment_index = line_comment_index(line)
        if comment_index is None:
            if line.strip():
                code_lines.add(index)
                source_lines.setdefault(line.strip(), []).append(index)
            continue
        before = line[:comment_index]
        comment = line[comment_index:].strip()
        if before.strip():
            code_lines.add(index)
            trailing[index] = comment
            source_lines.setdefault(before.strip(), []).append(index)
        else:
            standalone[index] = comment

    leading: dict[int, list[str]] = {}
    for line_number in sorted(standalone):
        target = next_code_line(lines, code_lines, line_number + 1)
        if target is not None:
            leading.setdefault(target, []).append(standalone[line_number])
    return CommentTrivia(leading, trailing, source_lines)


def next_code_line(lines: list[str], code_lines: set[int], start: int) -> int | None:
    for line_number in range(start, len(lines) + 1):
        if line_number in code_lines:
            return line_number
    return None


def line_comment_index(line: str) -> int | None:
    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string and char == "/" and index + 1 < len(line) and line[index + 1] == "/":
            return index
    return None


class Formatter:
    def __init__(self, trivia: CommentTrivia | None = None) -> None:
        self.trivia = trivia or CommentTrivia()
        self.used_leading: set[int] = set()
        self.used_source_lines: dict[str, int] = {}

    def unit(self, unit: Unit) -> str:
        if isinstance(unit, App):
            lines = self.line(f"app {unit.name} {{", unit.location, indent="")
            lines.extend(self.app_items(unit))
            lines.append("}")
            return "\n".join(lines) + "\n"
        lines = self.line(f"module {unit.name} {{", unit.location, indent="")
        lines.extend(self.module_items(unit))
        lines.append("}")
        return "\n".join(lines) + "\n"

    def app_items(self, app: App) -> list[str]:
        groups: list[list[str]] = []
        groups.extend([self.line(f'import "{item.path}" as {item.alias}', item.location, indent="  ") for item in app.imports])
        groups.extend([self.source_line(f'intent "{path}"', indent="  ") for path in app.intents])
        groups.extend([self.source_line(f"permissions from {source}", indent="  ") for source in app.permissions_from])
        groups.extend([self.enum_decl(enum, indent="  ") for enum in app.enums])
        groups.extend([self.type_decl(type_decl, indent="  ") for type_decl in app.types])
        groups.extend([self.line(f"store {store.name}: {store.type_ref.render()}", store.location, indent="  ") for store in app.stores])
        groups.extend([self.config(config, indent="  ") for config in app.configs])
        groups.extend([self.fixture(fixture, indent="  ") for fixture in app.fixtures])
        groups.extend([self.function(function, indent="  ") for function in app.functions])
        groups.extend([self.route(route, indent="  ") for route in app.routes])
        groups.extend([self.test(test, indent="  ") for test in app.tests])
        return self.join_groups(groups)

    def module_items(self, module: Module) -> list[str]:
        groups: list[list[str]] = []
        groups.extend([self.line(f'import "{item.path}" as {item.alias}', item.location, indent="  ") for item in module.imports])
        groups.extend([self.enum_decl(enum, indent="  ") for enum in module.enums])
        groups.extend([self.type_decl(type_decl, indent="  ") for type_decl in module.types])
        groups.extend([self.function(function, indent="  ") for function in module.functions])
        return self.join_groups(groups)

    def enum_decl(self, enum, *, indent: str) -> list[str]:
        return self.line(f"enum {enum.name} {{ {', '.join(enum.variants)} }}", enum.location, indent=indent)

    def type_decl(self, type_decl, *, indent: str) -> list[str]:
        lines = self.line(f"type {type_decl.name} = {{", type_decl.location, indent=indent)
        for field in type_decl.fields:
            lines.extend(self.line(f"{field.name}: {field.type_ref.render()},", field.location, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def function(self, function: FunctionDecl, *, indent: str) -> list[str]:
        params = ", ".join(f"{param.name}: {param.type_ref.render()}" for param in function.params)
        lines = self.line(
            f"{function.kind} {function.name}({params}) -> {function.return_type.render()} {{",
            function.location,
            indent=indent,
        )
        lines.extend(self.block(function.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def route(self, route: RouteDecl, *, indent: str) -> list[str]:
        body = f" body {route.body_type.render()}" if route.body_type is not None else ""
        lines = self.line(
            f'route {route.method} "{route.path}"{body} -> {route.return_type.render()} {{',
            route.location,
            indent=indent,
        )
        lines.extend(self.block(route.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def config(self, config: ConfigDecl, *, indent: str) -> list[str]:
        lines = self.line(f"config {config.name} = {{", config.location, indent=indent)
        for field in config.fields:
            lines.extend(
                self.line(
                    f"{field.name}: {field.type_ref.render()} = {self.expr(field.default)},",
                    field.location,
                    indent=indent + "  ",
                )
            )
        lines.append(f"{indent}}}")
        return lines

    def fixture(self, fixture: FixtureDecl, *, indent: str) -> list[str]:
        lines = self.line(f"fixture {fixture.store_name} {{", fixture.location, indent=indent)
        for record in fixture.records:
            lines.extend(self.line(f"{self.expr(record)},", record.location, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def test(self, test: TestDecl, *, indent: str) -> list[str]:
        if test.external_ref is not None:
            return self.line(f"test from {test.external_ref}", test.location, indent=indent)
        golden = f' golden "{test.golden_path}"' if test.golden_path is not None else ""
        lines = self.line(f'test "{test.name}"{golden} {{', test.location, indent=indent)
        lines.extend(self.block(test.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def block(self, statements: list[Stmt], *, indent: str) -> list[str]:
        lines: list[str] = []
        for statement in statements:
            lines.extend(self.stmt(statement, indent=indent))
        return lines

    def stmt(self, stmt: Stmt, *, indent: str) -> list[str]:
        if isinstance(stmt, LetStmt):
            return self.line(f"let {stmt.name} = {self.expr(stmt.expr)}", stmt.location, indent=indent)
        if isinstance(stmt, ReturnStmt):
            return self.line(f"return {self.expr(stmt.expr)}", stmt.location, indent=indent)
        if isinstance(stmt, AssertStmt):
            return self.line(f"assert {self.expr(stmt.expr)}", stmt.location, indent=indent)
        if isinstance(stmt, ExprStmt):
            return self.line(self.expr(stmt.expr), stmt.location, indent=indent)
        if isinstance(stmt, IfStmt):
            lines = self.line(f"if {self.expr(stmt.condition)} {{", stmt.location, indent=indent)
            lines.extend(self.block(stmt.then_body, indent=indent + "  "))
            lines.append(f"{indent}}}")
            if stmt.else_body:
                lines[-1] += " else {"
                lines.extend(self.block(stmt.else_body, indent=indent + "  "))
                lines.append(f"{indent}}}")
            return lines
        raise TypeError(f"Unsupported statement: {stmt!r}")

    def expr(self, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr):
            if expr.value is True:
                return "true"
            if expr.value is False:
                return "false"
            if isinstance(expr.value, str):
                return json.dumps(expr.value, ensure_ascii=False)
            return str(expr.value)
        if isinstance(expr, PathExpr):
            return ".".join(expr.parts)
        if isinstance(expr, CallExpr):
            args = []
            for arg in expr.args:
                rendered = self.expr(arg.expr)
                args.append(f"{arg.name}: {rendered}" if arg.name is not None else rendered)
            return f"{'.'.join(expr.callee)}({', '.join(args)})"
        if isinstance(expr, RecordExpr):
            return "{ " + ", ".join(f"{field.name}: {self.expr(field.expr)}" for field in expr.fields) + " }"
        if isinstance(expr, ListExpr):
            return "[" + ", ".join(self.expr(item) for item in expr.items) + "]"
        if isinstance(expr, BinaryExpr):
            return f"{self.expr(expr.left)} {expr.op} {self.expr(expr.right)}"
        raise TypeError(f"Unsupported expression: {expr!r}")

    def join_groups(self, groups: list[list[str]]) -> list[str]:
        lines: list[str] = []
        for group in groups:
            if not group:
                continue
            if lines:
                lines.append("")
            lines.extend(group)
        return lines

    def line(self, text: str, location: SourceLocation, *, indent: str) -> list[str]:
        return self.render_line(text, location.line, indent=indent)

    def source_line(self, text: str, *, indent: str) -> list[str]:
        line_number = self.next_source_line(text)
        return self.render_line(text, line_number, indent=indent)

    def next_source_line(self, text: str) -> int | None:
        index = self.used_source_lines.get(text, 0)
        matches = self.trivia.source_lines.get(text, [])
        if index >= len(matches):
            return None
        self.used_source_lines[text] = index + 1
        return matches[index]

    def render_line(self, text: str, line_number: int | None, *, indent: str) -> list[str]:
        lines: list[str] = []
        if line_number is not None and line_number not in self.used_leading:
            for comment in self.trivia.leading.get(line_number, []):
                lines.append(f"{indent}{comment}")
            self.used_leading.add(line_number)
        rendered = f"{indent}{text}"
        trailing = self.trivia.trailing.get(line_number) if line_number is not None else None
        if trailing:
            rendered = f"{rendered} {trailing}"
        lines.append(rendered)
        return lines
