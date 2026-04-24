from __future__ import annotations

from symboliclight.ast import (
    App,
    Arg,
    AssertStmt,
    BinaryExpr,
    CallExpr,
    EnumDecl,
    Expr,
    ExprStmt,
    FieldDecl,
    FunctionDecl,
    IfStmt,
    ImportDecl,
    LetStmt,
    ListExpr,
    LiteralExpr,
    Module,
    Param,
    PathExpr,
    RecordExpr,
    RecordField,
    ReturnStmt,
    RouteDecl,
    Stmt,
    StoreDecl,
    TestDecl,
    TypeDecl,
    TypeRef,
    Unit,
)
from symboliclight.diagnostics import Diagnostic, SymbolicLightError
from symboliclight.lexer import Token, lex


def parse_source(source: str, *, path: str = "<memory>") -> Unit:
    return Parser(lex(source, path=path)).parse_unit()


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.diagnostics: list[Diagnostic] = []

    def parse_unit(self) -> Unit:
        if self.check_keyword("app"):
            return self.parse_app()
        if self.check_keyword("module"):
            return self.parse_module()
        self.error("Expected `app` or `module`.")
        raise SymbolicLightError(self.diagnostics)

    def parse_app(self) -> App:
        app_location = self.current().location
        self.expect_keyword("app")
        name = self.expect_ident("Expected app name.")
        self.expect_symbol("{")

        intents: list[str] = []
        permissions_from: list[str] = []
        imports: list[ImportDecl] = []
        types: list[TypeDecl] = []
        enums: list[EnumDecl] = []
        stores: list[StoreDecl] = []
        functions: list[FunctionDecl] = []
        routes: list[RouteDecl] = []
        tests: list[TestDecl] = []

        while not self.check_symbol("}") and not self.at_end():
            if self.match_keyword("import"):
                imports.append(self.parse_import_decl())
            elif self.match_keyword("intent"):
                intents.append(self.expect_string("Expected intent path string."))
            elif self.match_keyword("permissions"):
                self.expect_keyword("from")
                permissions_from.append(self.parse_dotted_name("Expected permissions source."))
            elif self.match_keyword("enum"):
                enums.append(self.parse_enum_decl())
            elif self.match_keyword("type"):
                types.append(self.parse_type_decl())
            elif self.match_keyword("store"):
                stores.append(self.parse_store_decl())
            elif self.match_keyword("fn"):
                functions.append(self.parse_function("fn"))
            elif self.match_keyword("command"):
                functions.append(self.parse_function("command"))
            elif self.match_keyword("route"):
                routes.append(self.parse_route())
            elif self.match_keyword("test"):
                tests.append(self.parse_test())
            else:
                self.error("Expected app item.")
                self.synchronize_item()

        self.expect_symbol("}")
        self.expect_kind("eof", "Expected end of file.")
        if self.diagnostics:
            raise SymbolicLightError(self.diagnostics)
        return App(
            name,
            intents,
            permissions_from,
            imports,
            types,
            enums,
            stores,
            functions,
            routes,
            tests,
            app_location,
        )

    def parse_module(self) -> Module:
        module_location = self.current().location
        self.expect_keyword("module")
        name = self.expect_ident("Expected module name.")
        self.expect_symbol("{")

        imports: list[ImportDecl] = []
        types: list[TypeDecl] = []
        enums: list[EnumDecl] = []
        functions: list[FunctionDecl] = []

        while not self.check_symbol("}") and not self.at_end():
            if self.match_keyword("import"):
                imports.append(self.parse_import_decl())
            elif self.match_keyword("enum"):
                enums.append(self.parse_enum_decl())
            elif self.match_keyword("type"):
                types.append(self.parse_type_decl())
            elif self.match_keyword("fn"):
                functions.append(self.parse_function("fn"))
            else:
                self.error("Expected module item.")
                self.synchronize_item()

        self.expect_symbol("}")
        self.expect_kind("eof", "Expected end of file.")
        if self.diagnostics:
            raise SymbolicLightError(self.diagnostics)
        return Module(name, imports, types, enums, functions, module_location)

    def parse_import_decl(self) -> ImportDecl:
        location = self.previous().location
        path = self.expect_string("Expected import path string.")
        self.expect_keyword("as")
        alias = self.expect_ident("Expected import alias.")
        return ImportDecl(path, alias, location)

    def parse_enum_decl(self) -> EnumDecl:
        location = self.previous().location
        name = self.expect_ident("Expected enum name.")
        self.expect_symbol("{")
        variants: list[str] = []
        if self.match_symbol("}"):
            return EnumDecl(name, variants, location)
        while True:
            variants.append(self.expect_ident("Expected enum variant."))
            if self.match_symbol("}"):
                break
            self.expect_symbol(",")
        return EnumDecl(name, variants, location)

    def parse_type_decl(self) -> TypeDecl:
        location = self.previous().location
        name = self.expect_ident("Expected type name.")
        self.expect_symbol("=")
        self.expect_symbol("{")
        fields: list[FieldDecl] = []
        while not self.check_symbol("}") and not self.at_end():
            field_location = self.current().location
            field_name = self.expect_ident("Expected field name.")
            self.expect_symbol(":")
            fields.append(FieldDecl(field_name, self.parse_type_ref(), field_location))
            self.match_symbol(",")
        self.expect_symbol("}")
        return TypeDecl(name, fields, location)

    def parse_store_decl(self) -> StoreDecl:
        location = self.previous().location
        name = self.expect_ident("Expected store name.")
        self.expect_symbol(":")
        return StoreDecl(name, self.parse_type_ref(), location)

    def parse_function(self, kind: str) -> FunctionDecl:
        location = self.previous().location
        name = self.expect_ident("Expected function name.")
        params = self.parse_params()
        self.expect_symbol("->")
        return_type = self.parse_type_ref()
        body = self.parse_block()
        return FunctionDecl(kind, name, params, return_type, body, location)

    def parse_route(self) -> RouteDecl:
        location = self.previous().location
        method = self.expect_ident("Expected HTTP method.").upper()
        path = self.expect_string("Expected route path string.")
        self.expect_symbol("->")
        return_type = self.parse_type_ref()
        body = self.parse_block()
        return RouteDecl(method, path, return_type, body, location)

    def parse_test(self) -> TestDecl:
        location = self.previous().location
        if self.match_keyword("from"):
            external_ref = self.parse_dotted_name("Expected external test source.")
            return TestDecl(external_ref, [], location, external_ref)
        name = self.expect_string("Expected test name.")
        return TestDecl(name, self.parse_block(), location)

    def parse_params(self) -> list[Param]:
        self.expect_symbol("(")
        params: list[Param] = []
        if self.match_symbol(")"):
            return params
        while True:
            location = self.current().location
            name = self.expect_ident("Expected parameter name.")
            self.expect_symbol(":")
            params.append(Param(name, self.parse_type_ref(), location))
            if self.match_symbol(")"):
                break
            self.expect_symbol(",")
        return params

    def parse_type_ref(self) -> TypeRef:
        name = self.parse_dotted_name("Expected type name.")
        args: list[TypeRef] = []
        if self.match_symbol("<"):
            while True:
                args.append(self.parse_type_ref())
                if self.match_symbol(">"):
                    break
                self.expect_symbol(",")
        return TypeRef(name, args)

    def parse_block(self) -> list[Stmt]:
        self.expect_symbol("{")
        statements: list[Stmt] = []
        while not self.check_symbol("}") and not self.at_end():
            statements.append(self.parse_stmt())
        self.expect_symbol("}")
        return statements

    def parse_stmt(self) -> Stmt:
        if self.match_keyword("let"):
            location = self.previous().location
            name = self.expect_ident("Expected binding name.")
            self.expect_symbol("=")
            return LetStmt(name, self.parse_expr(), location)
        if self.match_keyword("return"):
            return ReturnStmt(self.parse_expr(), self.previous().location)
        if self.match_keyword("assert"):
            return AssertStmt(self.parse_expr(), self.previous().location)
        if self.match_keyword("if"):
            location = self.previous().location
            condition = self.parse_expr()
            then_body = self.parse_block()
            else_body = self.parse_block() if self.match_keyword("else") else []
            return IfStmt(condition, then_body, else_body, location)
        return ExprStmt(self.parse_expr(), self.current().location)

    def parse_expr(self) -> Expr:
        return self.parse_binary()

    def parse_binary(self) -> Expr:
        expr = self.parse_primary()
        while (
            self.check_symbol("==")
            or self.check_symbol("!=")
            or self.check_symbol("<")
            or self.check_symbol(">")
            or self.check_symbol("<=")
            or self.check_symbol(">=")
            or self.check_symbol("&&")
            or self.check_symbol("||")
        ):
            op = self.advance().value
            right = self.parse_primary()
            expr = BinaryExpr(expr, op, right, expr.location)
        return expr

    def parse_primary(self) -> Expr:
        token = self.current()
        if self.match_keyword("true"):
            return LiteralExpr(True, token.location)
        if self.match_keyword("false"):
            return LiteralExpr(False, token.location)
        if self.match_kind("number"):
            value: object = float(token.value) if "." in token.value else int(token.value)
            return LiteralExpr(value, token.location)
        if self.match_kind("string"):
            return LiteralExpr(token.value, token.location)
        if self.match_symbol("{"):
            return self.parse_record(token.location)
        if self.match_symbol("["):
            return self.parse_list(token.location)
        if self.match_symbol("("):
            expr = self.parse_expr()
            self.expect_symbol(")")
            return expr
        if self.check_kind("ident") or self.check_kind("keyword"):
            return self.parse_path_or_call()
        self.error("Expected expression.")
        self.advance()
        return LiteralExpr(None, token.location)

    def parse_record(self, location) -> RecordExpr:
        fields: list[RecordField] = []
        if self.match_symbol("}"):
            return RecordExpr(fields, location)
        while True:
            field_location = self.current().location
            name = self.expect_ident("Expected record field name.")
            self.expect_symbol(":")
            fields.append(RecordField(name, self.parse_expr(), field_location))
            if self.match_symbol("}"):
                break
            self.expect_symbol(",")
        return RecordExpr(fields, location)

    def parse_list(self, location) -> ListExpr:
        items: list[Expr] = []
        if self.match_symbol("]"):
            return ListExpr(items, location)
        while True:
            items.append(self.parse_expr())
            if self.match_symbol("]"):
                break
            self.expect_symbol(",")
        return ListExpr(items, location)

    def parse_path_or_call(self) -> Expr:
        location = self.current().location
        parts = [self.advance().value]
        while self.match_symbol("."):
            parts.append(self.expect_ident("Expected field or method name."))
        if not self.match_symbol("("):
            return PathExpr(parts, location)
        args: list[Arg] = []
        if self.match_symbol(")"):
            return CallExpr(parts, args, location)
        while True:
            arg_location = self.current().location
            if (self.check_kind("ident") or self.check_kind("keyword")) and self.peek_symbol(":"):
                name = self.advance().value
                self.expect_symbol(":")
                args.append(Arg(name, self.parse_expr(), arg_location))
            else:
                args.append(Arg(None, self.parse_expr(), arg_location))
            if self.match_symbol(")"):
                break
            self.expect_symbol(",")
        return CallExpr(parts, args, location)

    def parse_dotted_name(self, message: str) -> str:
        parts = [self.expect_ident(message)]
        while self.match_symbol("."):
            parts.append(self.expect_ident(message))
        return ".".join(parts)

    def expect_keyword(self, value: str) -> None:
        if not self.match_keyword(value):
            self.error(f"Expected keyword `{value}`.")

    def check_keyword(self, value: str) -> bool:
        return self.current().kind == "keyword" and self.current().value == value

    def match_keyword(self, value: str) -> bool:
        if self.current().kind == "keyword" and self.current().value == value:
            self.advance()
            return True
        return False

    def expect_symbol(self, value: str) -> None:
        if not self.match_symbol(value):
            self.error(f"Expected `{value}`.")

    def match_symbol(self, value: str) -> bool:
        if self.check_symbol(value):
            self.advance()
            return True
        return False

    def check_symbol(self, value: str) -> bool:
        return self.current().kind == "symbol" and self.current().value == value

    def peek_symbol(self, value: str) -> bool:
        if self.index + 1 >= len(self.tokens):
            return False
        token = self.tokens[self.index + 1]
        return token.kind == "symbol" and token.value == value

    def expect_ident(self, message: str) -> str:
        if self.current().kind in {"ident", "keyword"}:
            return self.advance().value
        self.error(message)
        return "<missing>"

    def expect_string(self, message: str) -> str:
        if self.current().kind == "string":
            return self.advance().value
        self.error(message)
        return ""

    def expect_kind(self, kind: str, message: str) -> None:
        if not self.match_kind(kind):
            self.error(message)

    def match_kind(self, kind: str) -> bool:
        if self.current().kind == kind:
            self.advance()
            return True
        return False

    def check_kind(self, kind: str) -> bool:
        return self.current().kind == kind

    def current(self) -> Token:
        return self.tokens[self.index]

    def previous(self) -> Token:
        return self.tokens[max(0, self.index - 1)]

    def advance(self) -> Token:
        token = self.current()
        if not self.at_end():
            self.index += 1
        return token

    def at_end(self) -> bool:
        return self.current().kind == "eof"

    def error(self, message: str) -> None:
        self.diagnostics.append(
            Diagnostic(message, self.current().location, "Check the SymbolicLight v0 syntax.")
        )

    def synchronize_item(self) -> None:
        if not self.at_end():
            self.advance()
        while not self.at_end():
            if self.check_symbol("}"):
                return
            if self.current().kind == "keyword" and self.current().value in {
                "import",
                "intent",
                "permissions",
                "enum",
                "type",
                "store",
                "fn",
                "command",
                "route",
                "test",
            }:
                return
            self.advance()
