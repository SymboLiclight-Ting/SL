from __future__ import annotations

from symboliclight.ast import (
    App,
    AssertStmt,
    BinaryExpr,
    CallExpr,
    Expr,
    ExprStmt,
    FunctionDecl,
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


def format_unit(unit: Unit) -> str:
    formatter = Formatter()
    return formatter.unit(unit)


class Formatter:
    def unit(self, unit: Unit) -> str:
        if isinstance(unit, App):
            lines = [f"app {unit.name} {{"]
            lines.extend(self.app_items(unit))
            lines.append("}")
            return "\n".join(lines) + "\n"
        lines = [f"module {unit.name} {{"]
        lines.extend(self.module_items(unit))
        lines.append("}")
        return "\n".join(lines) + "\n"

    def app_items(self, app: App) -> list[str]:
        groups: list[list[str]] = []
        groups.extend([[f'  import "{item.path}" as {item.alias}'] for item in app.imports])
        groups.extend([[f'  intent "{path}"'] for path in app.intents])
        groups.extend([[f"  permissions from {source}"] for source in app.permissions_from])
        groups.extend([self.enum_decl(enum.name, enum.variants, indent="  ") for enum in app.enums])
        groups.extend([self.type_decl(type_decl.name, type_decl.fields, indent="  ") for type_decl in app.types])
        groups.extend([[f"  store {store.name}: {store.type_ref.render()}"] for store in app.stores])
        groups.extend([self.function(function, indent="  ") for function in app.functions])
        groups.extend([self.route(route, indent="  ") for route in app.routes])
        groups.extend([self.test(test, indent="  ") for test in app.tests])
        return self.join_groups(groups)

    def module_items(self, module: Module) -> list[str]:
        groups: list[list[str]] = []
        groups.extend([[f'  import "{item.path}" as {item.alias}'] for item in module.imports])
        groups.extend([self.enum_decl(enum.name, enum.variants, indent="  ") for enum in module.enums])
        groups.extend([self.type_decl(type_decl.name, type_decl.fields, indent="  ") for type_decl in module.types])
        groups.extend([self.function(function, indent="  ") for function in module.functions])
        return self.join_groups(groups)

    def enum_decl(self, name: str, variants: list[str], *, indent: str) -> list[str]:
        return [f"{indent}enum {name} {{ {', '.join(variants)} }}"]

    def type_decl(self, name, fields, *, indent: str) -> list[str]:
        lines = [f"{indent}type {name} = {{"]
        for field in fields:
            lines.append(f"{indent}  {field.name}: {field.type_ref.render()},")
        lines.append(f"{indent}}}")
        return lines

    def function(self, function: FunctionDecl, *, indent: str) -> list[str]:
        params = ", ".join(f"{param.name}: {param.type_ref.render()}" for param in function.params)
        lines = [f"{indent}{function.kind} {function.name}({params}) -> {function.return_type.render()} {{"]
        lines.extend(self.block(function.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def route(self, route: RouteDecl, *, indent: str) -> list[str]:
        lines = [f'{indent}route {route.method} "{route.path}" -> {route.return_type.render()} {{']
        lines.extend(self.block(route.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def test(self, test: TestDecl, *, indent: str) -> list[str]:
        if test.external_ref is not None:
            return [f"{indent}test from {test.external_ref}"]
        lines = [f'{indent}test "{test.name}" {{']
        lines.extend(self.block(test.body, indent=indent + "  "))
        lines.append(f"{indent}}}")
        return lines

    def block(self, statements: list[Stmt], *, indent: str) -> list[str]:
        return [self.stmt(statement, indent=indent) for statement in statements]

    def stmt(self, stmt: Stmt, *, indent: str) -> str:
        if isinstance(stmt, LetStmt):
            return f"{indent}let {stmt.name} = {self.expr(stmt.expr)}"
        if isinstance(stmt, ReturnStmt):
            return f"{indent}return {self.expr(stmt.expr)}"
        if isinstance(stmt, AssertStmt):
            return f"{indent}assert {self.expr(stmt.expr)}"
        if isinstance(stmt, ExprStmt):
            return f"{indent}{self.expr(stmt.expr)}"
        if isinstance(stmt, IfStmt):
            then_body = "\n".join(self.block(stmt.then_body, indent=indent + "  "))
            rendered = f"{indent}if {self.expr(stmt.condition)} {{\n{then_body}\n{indent}}}"
            if stmt.else_body:
                else_body = "\n".join(self.block(stmt.else_body, indent=indent + "  "))
                rendered += f" else {{\n{else_body}\n{indent}}}"
            return rendered
        raise TypeError(f"Unsupported statement: {stmt!r}")

    def expr(self, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr):
            if expr.value is True:
                return "true"
            if expr.value is False:
                return "false"
            if isinstance(expr.value, str):
                return repr(expr.value).replace("'", '"')
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
