from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from symboliclight.diagnostics import SourceLocation


@dataclass(slots=True)
class TypeRef:
    name: str
    args: list["TypeRef"] = field(default_factory=list)

    def render(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}<{', '.join(arg.render() for arg in self.args)}>"


@dataclass(slots=True)
class FieldDecl:
    name: str
    type_ref: TypeRef
    location: SourceLocation


@dataclass(slots=True)
class TypeDecl:
    name: str
    fields: list[FieldDecl]
    location: SourceLocation


@dataclass(slots=True)
class EnumDecl:
    name: str
    variants: list[str]
    location: SourceLocation


@dataclass(slots=True)
class ImportDecl:
    path: str
    alias: str
    location: SourceLocation


@dataclass(slots=True)
class StoreDecl:
    name: str
    type_ref: TypeRef
    location: SourceLocation


@dataclass(slots=True)
class ConfigFieldDecl:
    name: str
    type_ref: TypeRef
    default: "Expr"
    location: SourceLocation


@dataclass(slots=True)
class ConfigDecl:
    name: str
    fields: list[ConfigFieldDecl]
    location: SourceLocation


@dataclass(slots=True)
class FixtureDecl:
    store_name: str
    records: list["RecordExpr"]
    location: SourceLocation


@dataclass(slots=True)
class Param:
    name: str
    type_ref: TypeRef
    location: SourceLocation


@dataclass(slots=True)
class FunctionDecl:
    kind: Literal["fn", "command"]
    name: str
    params: list[Param]
    return_type: TypeRef
    body: list["Stmt"]
    location: SourceLocation


@dataclass(slots=True)
class RouteDecl:
    method: str
    path: str
    body_type: TypeRef | None
    return_type: TypeRef
    body: list["Stmt"]
    location: SourceLocation

    @property
    def function_name(self) -> str:
        safe = self.path.strip("/").replace("/", "_").replace("-", "_") or "root"
        return f"route_{self.method.lower()}_{safe}"


@dataclass(slots=True)
class TestDecl:
    name: str
    body: list["Stmt"]
    location: SourceLocation
    external_ref: str | None = None
    golden_path: str | None = None


@dataclass(slots=True)
class App:
    name: str
    intents: list[str]
    permissions_from: list[str]
    imports: list[ImportDecl]
    types: list[TypeDecl]
    enums: list[EnumDecl]
    stores: list[StoreDecl]
    configs: list[ConfigDecl]
    fixtures: list[FixtureDecl]
    functions: list[FunctionDecl]
    routes: list[RouteDecl]
    tests: list[TestDecl]
    location: SourceLocation
    imported_modules: dict[str, "Module"] = field(default_factory=dict)


@dataclass(slots=True)
class Module:
    name: str
    imports: list[ImportDecl]
    types: list[TypeDecl]
    enums: list[EnumDecl]
    functions: list[FunctionDecl]
    location: SourceLocation
    imported_modules: dict[str, "Module"] = field(default_factory=dict)


Unit = App | Module


Stmt = "LetStmt | ReturnStmt | AssertStmt | IfStmt | ExprStmt"


@dataclass(slots=True)
class LetStmt:
    name: str
    expr: "Expr"
    location: SourceLocation


@dataclass(slots=True)
class ReturnStmt:
    expr: "Expr"
    location: SourceLocation


@dataclass(slots=True)
class AssertStmt:
    expr: "Expr"
    location: SourceLocation


@dataclass(slots=True)
class IfStmt:
    condition: "Expr"
    then_body: list[Stmt]
    else_body: list[Stmt]
    location: SourceLocation


@dataclass(slots=True)
class ExprStmt:
    expr: "Expr"
    location: SourceLocation


Expr = "LiteralExpr | PathExpr | CallExpr | RecordExpr | ListExpr | BinaryExpr"


@dataclass(slots=True)
class LiteralExpr:
    value: object
    location: SourceLocation


@dataclass(slots=True)
class PathExpr:
    parts: list[str]
    location: SourceLocation


@dataclass(slots=True)
class Arg:
    name: str | None
    expr: Expr
    location: SourceLocation


@dataclass(slots=True)
class CallExpr:
    callee: list[str]
    args: list[Arg]
    location: SourceLocation


@dataclass(slots=True)
class RecordField:
    name: str
    expr: Expr
    location: SourceLocation


@dataclass(slots=True)
class RecordExpr:
    fields: list[RecordField]
    location: SourceLocation


@dataclass(slots=True)
class ListExpr:
    items: list[Expr]
    location: SourceLocation


@dataclass(slots=True)
class BinaryExpr:
    left: Expr
    op: str
    right: Expr
    location: SourceLocation
