from __future__ import annotations

import keyword as py_keyword
from dataclasses import dataclass, field
from pathlib import Path

from symboliclight.ast import (
    App,
    Arg,
    AssertStmt,
    BinaryExpr,
    CallExpr,
    ConfigDecl,
    EnumDecl,
    Expr,
    FieldDecl,
    FixtureDecl,
    FunctionDecl,
    IfStmt,
    LetStmt,
    ListExpr,
    LiteralExpr,
    Module,
    Param,
    PathExpr,
    RecordExpr,
    ReturnStmt,
    RouteDecl,
    Stmt,
    TypeDecl,
    TypeRef,
    Unit,
)
from symboliclight.diagnostics import Diagnostic, SourceLocation, SymbolicLightError
from symboliclight.parser import parse_source

PRIMITIVES = {"Bool", "Int", "Float", "Text"}
GENERIC_ARITY = {"Id": 1, "List": 1, "Option": 1, "Result": 2}
STORE_METHODS = {"insert", "all", "get", "update", "try_update", "delete", "filter", "count", "exists", "clear"}
PYTHON_RESERVED_IDENTIFIERS = set(py_keyword.kwlist)
GENERATED_CLI_COMMANDS = {"serve", "test"}


@dataclass(slots=True)
class CheckResult:
    diagnostics: list[Diagnostic]
    unit: Unit
    imports: dict[str, Module] = field(default_factory=dict)
    symbol_table: dict[str, str] = field(default_factory=dict)
    dependency_paths: set[Path] = field(default_factory=set)
    missing_dependency_paths: set[Path] = field(default_factory=set)


class Checker:
    def __init__(
        self,
        unit: Unit,
        *,
        source_path: Path,
        strict_intent: bool = False,
        seen: set[Path] | None = None,
        import_chain: list[Path] | None = None,
    ) -> None:
        self.unit = unit
        self.source_path = source_path.resolve()
        self.strict_intent = strict_intent
        self.seen = seen or set()
        self.import_chain = import_chain or [self.source_path]
        self.diagnostics: list[Diagnostic] = []
        self.dependency_paths: set[Path] = set()
        self.missing_dependency_paths: set[Path] = set()
        self.context_kind = "fn"

        self.types = {type_decl.name: type_decl for type_decl in unit.types}
        self.enums = {enum_decl.name: enum_decl for enum_decl in unit.enums}
        self.functions = {function.name: function for function in unit.functions}
        self.configs = {config.name: config for config in unit.configs} if isinstance(unit, App) else {}
        self.imported_functions: dict[str, FunctionDecl] = {}

        if isinstance(unit, App):
            self.stores = {store.name: store for store in unit.stores}
        else:
            self.stores = {}

    def run(self) -> list[Diagnostic]:
        return self.run_result().diagnostics

    def run_result(self) -> CheckResult:
        self.load_imports()
        self.check_duplicate_names()
        self.check_codegen_reserved_identifiers()
        if isinstance(self.unit, App):
            self.check_duplicate_routes()
        if isinstance(self.unit, App):
            self.check_intents()
            self.check_permissions()
        for enum_decl in self.unit.enums:
            self.check_enum_decl(enum_decl)
        for type_decl in self.unit.types:
            self.check_type_decl(type_decl)
        if isinstance(self.unit, App):
            for store in self.unit.stores:
                self.check_type_ref(store.type_ref, store.location)
                if store.type_ref.name not in self.types:
                    self.error(
                        f"Store `{store.name}` must reference a record type, found `{store.type_ref.render()}`.",
                        store.location,
                        "Declare a record type and use it as the store item type.",
                    )
            for config in self.unit.configs:
                self.check_config(config)
            for fixture in self.unit.fixtures:
                self.check_fixture(fixture)
            for function in self.unit.functions:
                self.check_function(function)
            for route in self.unit.routes:
                self.check_route(route)
            for test in self.unit.tests:
                if test.external_ref is not None:
                    self.check_external_test(test)
                else:
                    self.check_block(test.body, expected_return=None, local_env={}, context_kind="test")
        else:
            for function in self.unit.functions:
                self.check_function(function)
        return CheckResult(
            diagnostics=self.diagnostics,
            unit=self.unit,
            imports=dict(self.unit.imported_modules),
            symbol_table=self.symbol_table(),
            dependency_paths=set(self.dependency_paths),
            missing_dependency_paths=set(self.missing_dependency_paths),
        )

    def load_imports(self) -> None:
        aliases: set[str] = set()
        local_names = self.local_decl_names()
        for import_decl in self.unit.imports:
            if import_decl.alias in aliases:
                self.error(
                    f"Duplicate import alias `{import_decl.alias}`.",
                    import_decl.location,
                    "Use a unique alias for each import.",
                    code="SLC010",
                )
                continue
            aliases.add(import_decl.alias)
            if import_decl.alias in local_names:
                self.error(
                    f"Import alias `{import_decl.alias}` conflicts with a local declaration.",
                    import_decl.location,
                    "Rename the import alias or the local declaration.",
                    code="SLC011",
                )
            import_path = (self.source_path.parent / import_decl.path).resolve()
            if import_path in self.seen:
                chain = " -> ".join(str(path) for path in [*self.import_chain, import_path])
                self.error(
                    f"Cyclic import detected: {chain}",
                    import_decl.location,
                    "Break the import cycle or move shared declarations into a lower-level module.",
                    code="SLC012",
                )
                continue
            if not import_path.exists():
                self.missing_dependency_paths.add(import_path)
                self.error(
                    f"Import file not found: {import_decl.path}",
                    import_decl.location,
                    "Create the module file or fix the import path.",
                    code="SLC013",
                )
                continue
            self.dependency_paths.add(import_path)
            try:
                imported = parse_source(import_path.read_text(encoding="utf-8"), path=str(import_path))
            except SymbolicLightError as exc:
                self.diagnostics.extend(exc.diagnostics)
                continue
            if not isinstance(imported, Module):
                self.error(
                    f"Import `{import_decl.path}` must point to a module file.",
                    import_decl.location,
                    "Use `module Name { ... }` in files imported by an app.",
                    code="SLC014",
                )
                continue
            nested_checker = Checker(
                imported,
                source_path=import_path,
                strict_intent=self.strict_intent,
                seen={*self.seen, self.source_path},
                import_chain=[*self.import_chain, import_path],
            )
            nested_result = nested_checker.run_result()
            self.diagnostics.extend(nested_result.diagnostics)
            self.dependency_paths.update(nested_result.dependency_paths)
            self.missing_dependency_paths.update(nested_result.missing_dependency_paths)
            self.unit.imported_modules[import_decl.alias] = imported
            for type_decl in imported.types:
                self.types[f"{import_decl.alias}.{type_decl.name}"] = self.qualify_type_decl(
                    type_decl,
                    import_decl.alias,
                    imported,
                )
            for enum_decl in imported.enums:
                self.enums[f"{import_decl.alias}.{enum_decl.name}"] = enum_decl
            for function in imported.functions:
                self.imported_functions[f"{import_decl.alias}.{function.name}"] = self.qualify_function_decl(
                    function,
                    import_decl.alias,
                    imported,
                )

    def local_decl_names(self) -> set[str]:
        names = {type_decl.name for type_decl in self.unit.types}
        names.update(enum_decl.name for enum_decl in self.unit.enums)
        names.update(function.name for function in self.unit.functions)
        if isinstance(self.unit, App):
            names.update(store.name for store in self.unit.stores)
            names.update(config.name for config in self.unit.configs)
            names.update(fixture.store_name for fixture in self.unit.fixtures)
        return names

    def symbol_table(self) -> dict[str, str]:
        symbols: dict[str, str] = {}
        for type_decl in self.unit.types:
            symbols[type_decl.name] = "type"
        for enum_decl in self.unit.enums:
            symbols[enum_decl.name] = "enum"
        for function in self.unit.functions:
            symbols[function.name] = function.kind
        for alias in self.unit.imported_modules:
            symbols[alias] = "import"
        if isinstance(self.unit, App):
            for store in self.unit.stores:
                symbols[store.name] = "store"
            for config in self.unit.configs:
                symbols[config.name] = "config"
        return symbols

    def qualify_type_decl(self, type_decl: TypeDecl, alias: str, module: Module) -> TypeDecl:
        fields = [
            FieldDecl(
                field.name,
                self.qualify_type_ref(field.type_ref, alias, module),
                field.location,
            )
            for field in type_decl.fields
        ]
        return TypeDecl(f"{alias}.{type_decl.name}", fields, type_decl.location)

    def qualify_type_ref(self, type_ref: TypeRef, alias: str, module: Module) -> TypeRef:
        local_names = {item.name for item in module.types} | {item.name for item in module.enums}
        name = f"{alias}.{type_ref.name}" if type_ref.name in local_names else type_ref.name
        return TypeRef(name, [self.qualify_type_ref(arg, alias, module) for arg in type_ref.args])

    def qualify_function_decl(self, function: FunctionDecl, alias: str, module: Module) -> FunctionDecl:
        params = [
            Param(param.name, self.qualify_type_ref(param.type_ref, alias, module), param.location)
            for param in function.params
        ]
        return FunctionDecl(
            function.kind,
            function.name,
            params,
            self.qualify_type_ref(function.return_type, alias, module),
            function.body,
            function.location,
        )

    def check_duplicate_names(self) -> None:
        names: set[str] = set()
        for name, location in [
            *[(type_decl.name, type_decl.location) for type_decl in self.unit.types],
            *[(enum_decl.name, enum_decl.location) for enum_decl in self.unit.enums],
            *[(function.name, function.location) for function in self.unit.functions],
        ]:
            if name in names:
                self.error(f"Duplicate declaration `{name}`.", location, "Use unique names in one file.")
            names.add(name)
        if isinstance(self.unit, App):
            for store in self.unit.stores:
                if store.name in names:
                    self.error(f"Duplicate declaration `{store.name}`.", store.location, "Use unique names in one app.")
                names.add(store.name)
            for config in self.unit.configs:
                if config.name in names:
                    self.error(f"Duplicate declaration `{config.name}`.", config.location, "Use unique names in one app.")
                names.add(config.name)

    def check_codegen_reserved_identifiers(self) -> None:
        if isinstance(self.unit, App):
            for config in self.unit.configs:
                self.check_python_identifier(config.name, config.location, "Config")
        for function in self.unit.functions:
            if isinstance(self.unit, App) and function.kind == "command":
                if function.name in GENERATED_CLI_COMMANDS:
                    self.error(
                        f"Command `{function.name}` conflicts with a generated CLI command.",
                        function.location,
                        "Choose a command name other than `serve` or `test`.",
                        code="SLC090",
                    )
                self.check_python_identifier(function.name, function.location, "Command")
            for param in function.params:
                self.check_python_identifier(param.name, param.location, "Parameter")
            self.check_statement_identifiers(function.body)
        if isinstance(self.unit, App):
            for route in self.unit.routes:
                self.check_statement_identifiers(route.body)
            for test in self.unit.tests:
                if test.external_ref is None:
                    self.check_statement_identifiers(test.body)

    def check_statement_identifiers(self, statements: list[Stmt]) -> None:
        for statement in statements:
            if isinstance(statement, LetStmt):
                self.check_python_identifier(statement.name, statement.location, "Local variable")
            elif isinstance(statement, IfStmt):
                self.check_statement_identifiers(statement.then_body)
                self.check_statement_identifiers(statement.else_body)

    def check_python_identifier(self, name: str, location: SourceLocation, kind: str) -> None:
        if name not in PYTHON_RESERVED_IDENTIFIERS:
            return
        self.error(
            f"{kind} `{name}` conflicts with a Python reserved word.",
            location,
            "Choose a different identifier so generated Python remains valid.",
            code="SLC091",
        )

    def check_duplicate_routes(self) -> None:
        assert isinstance(self.unit, App)
        seen: dict[tuple[str, str], RouteDecl] = {}
        for route in self.unit.routes:
            key = (route.method, route.path)
            previous = seen.get(key)
            if previous is not None:
                self.error(
                    f"Duplicate route `{route.method} {route.path}`.",
                    route.location,
                    "Use one handler for each method and path pair.",
                    code="SLC092",
                )
                continue
            seen[key] = route

    def check_intents(self) -> None:
        assert isinstance(self.unit, App)
        for intent in self.unit.intents:
            path = (self.source_path.parent / intent).resolve()
            if not path.exists():
                self.missing_dependency_paths.add(path)
                self.error(
                    f"IntentSpec file not found: {intent}",
                    self.unit.location,
                    "Create the intent file or remove the intent declaration.",
                )
                continue
            self.dependency_paths.add(path)
            try:
                from intentspec_core.spec.parser import load_spec  # type: ignore
            except Exception:
                severity = "error" if self.strict_intent else "warning"
                self.diagnostics.append(
                    Diagnostic(
                        "IntentSpec package is not installed; skipped intent validation.",
                        self.unit.location,
                        "Install intentspec or pass --strict-intent only where it is available.",
                        severity,
                    )
                )
                continue
            try:
                load_spec(path)
            except Exception as exc:
                self.error(f"IntentSpec validation failed: {exc}", self.unit.location, "Fix the intent file.")

    def check_permissions(self) -> None:
        assert isinstance(self.unit, App)
        for source in self.unit.permissions_from:
            if source != "intent.permissions":
                self.error(
                    f"Unsupported permissions source `{source}`.",
                    self.unit.location,
                    "Use `permissions from intent.permissions` in v0.4.",
                )
            if not self.unit.intents:
                self.error(
                    "`permissions from intent.permissions` requires an intent declaration.",
                    self.unit.location,
                    "Add `intent \"./file.intent.yaml\"` before importing permissions.",
                )

    def check_external_test(self, test: object) -> None:
        assert isinstance(self.unit, App)
        external_ref = getattr(test, "external_ref", None)
        location = getattr(test, "location")
        if external_ref != "intent.acceptance":
            self.error(
                f"Unsupported external test source `{external_ref}`.",
                location,
                "Use `test from intent.acceptance` in v0.4.",
            )
            return
        if not self.unit.intents:
            self.error(
                "`test from intent.acceptance` requires an intent declaration.",
                location,
                "Add an app-level intent declaration.",
            )

    def check_enum_decl(self, enum_decl: EnumDecl) -> None:
        variants: set[str] = set()
        for variant in enum_decl.variants:
            if variant in variants:
                self.error(
                    f"Duplicate enum variant `{variant}`.",
                    enum_decl.location,
                    "Use unique variant names inside an enum.",
                )
            variants.add(variant)

    def check_type_decl(self, type_decl: TypeDecl) -> None:
        names: set[str] = set()
        for field in type_decl.fields:
            if field.name in names:
                self.error(f"Duplicate field `{field.name}`.", field.location, "Use unique field names.")
            names.add(field.name)
            self.check_type_ref(field.type_ref, field.location)

    def check_function(self, function: FunctionDecl) -> None:
        env = {param.name: param.type_ref for param in function.params}
        for param in function.params:
            self.check_type_ref(param.type_ref, param.location)
        self.check_type_ref(function.return_type, function.location)
        self.check_block(function.body, expected_return=function.return_type, local_env=env, context_kind=function.kind)

    def check_route(self, route: RouteDecl) -> None:
        if route.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            self.error(
                f"Unsupported route method `{route.method}`.",
                route.location,
                "Use GET, POST, PUT, PATCH, or DELETE in v0.4.",
            )
        if route.method in {"GET", "DELETE"} and route.body_type is not None:
            self.error(
                f"{route.method} routes cannot declare a request body in v0.4.",
                route.location,
                f"Remove `body Type` from the {route.method} route.",
                code="SLC060",
            )
        if route.body_type is not None:
            self.check_type_ref(route.body_type, route.location)
            if route.body_type.name not in self.types:
                self.error(
                    f"Route body type `{route.body_type.render()}` must be a record type.",
                    route.location,
                    "Declare a record type and use it as the route body.",
                    code="SLC061",
                )
        self.check_type_ref(route.return_type, route.location)
        if not self.is_json_encodable(route.return_type):
            self.error(
                f"Route return type `{route.return_type.render()}` is not JSON encodable.",
                route.location,
                "Return a primitive, enum, record, Option, Result, or List of JSON encodable values.",
                code="SLC040",
            )
        env = {"request": TypeRef("Request", [route.body_type] if route.body_type is not None else [])}
        self.check_block(route.body, expected_return=route.return_type, local_env=env, context_kind="route")

    def check_config(self, config: ConfigDecl) -> None:
        names: set[str] = set()
        env: dict[str, TypeRef] = {}
        for field in config.fields:
            if field.name in names:
                self.error(f"Duplicate config field `{field.name}`.", field.location, "Use unique config field names.")
            names.add(field.name)
            self.check_type_ref(field.type_ref, field.location)
            actual = self.infer_expr(field.default, env, context_kind="config")
            if not self.type_matches(field.type_ref, actual):
                self.error(
                    f"Config field `{field.name}` expected `{field.type_ref.render()}`, found `{actual.render()}`.",
                    field.location,
                    "Use a default expression matching the declared config field type.",
                    code="SLC070",
                )
            env[field.name] = field.type_ref

    def check_fixture(self, fixture: FixtureDecl) -> None:
        store = self.stores.get(fixture.store_name)
        if store is None:
            self.error(
                f"Fixture references unknown store `{fixture.store_name}`.",
                fixture.location,
                "Use a declared store name after `fixture`.",
                code="SLC080",
            )
            return
        for record in fixture.records:
            self.validate_record_expr(record, store.type_ref, allow_missing_id=True, env={})

    def check_block(
        self,
        statements: list[Stmt],
        *,
        expected_return: TypeRef | None,
        local_env: dict[str, TypeRef],
        context_kind: str,
    ) -> None:
        previous_context = self.context_kind
        self.context_kind = context_kind
        try:
            env = dict(local_env)
            for statement in statements:
                if isinstance(statement, LetStmt):
                    env[statement.name] = self.infer_expr(statement.expr, env, context_kind=context_kind)
                elif isinstance(statement, ReturnStmt):
                    if expected_return is not None:
                        self.validate_targeted_return_expr(statement.expr, expected_return, env)
                    actual = self.infer_expr(statement.expr, env, context_kind=context_kind)
                    if expected_return is not None and not self.type_matches(expected_return, actual):
                        self.error(
                            f"Return type mismatch: expected `{expected_return.render()}`, found `{actual.render()}`.",
                            statement.location,
                            "Return a value that matches the declared type.",
                        )
                elif isinstance(statement, AssertStmt):
                    actual = self.infer_expr(statement.expr, env, context_kind=context_kind)
                    if actual.name != "Bool":
                        self.error("assert requires Bool.", statement.location, "Compare values or return a Bool.")
                elif isinstance(statement, IfStmt):
                    actual = self.infer_expr(statement.condition, env, context_kind=context_kind)
                    if actual.name != "Bool":
                        self.error("if condition requires Bool.", statement.location, "Use a boolean expression.")
                    self.check_block(
                        statement.then_body,
                        expected_return=expected_return,
                        local_env=dict(env),
                        context_kind=context_kind,
                    )
                    self.check_block(
                        statement.else_body,
                        expected_return=expected_return,
                        local_env=dict(env),
                        context_kind=context_kind,
                    )
                else:
                    self.infer_expr(statement.expr, env, context_kind=context_kind)
        finally:
            self.context_kind = previous_context

    def validate_targeted_return_expr(
        self,
        expr: Expr,
        expected_return: TypeRef,
        env: dict[str, TypeRef],
    ) -> None:
        self.validate_expr_against_target(expr, expected_return, env=env, allow_missing_id=False)

    def validate_expr_against_target(
        self,
        expr: Expr,
        expected: TypeRef,
        *,
        env: dict[str, TypeRef],
        allow_missing_id: bool,
    ) -> None:
        if isinstance(expr, RecordExpr):
            self.validate_record_expr(
                expr,
                expected,
                allow_missing_id=allow_missing_id,
                env=env,
            )
            return
        if not isinstance(expr, CallExpr):
            return
        if expected.name == "Response" and expected.args:
            if expr.callee == ["response"]:
                response_body = self.response_body_expr(expr)
                if response_body is not None:
                    self.validate_expr_against_target(
                        response_body,
                        expected.args[0],
                        env=env,
                        allow_missing_id=False,
                    )
            elif expr.callee == ["response_ok"]:
                self.validate_response_ok_target(expr, expected.args[0], env)
            elif expr.callee == ["response_err"]:
                self.validate_response_err_target(expr, expected.args[0])
            return
        if expected.name == "Result" and len(expected.args) == 2:
            if expr.callee == ["ok"]:
                wrapper_arg = self.first_positional_expr(expr)
                if wrapper_arg is not None:
                    self.validate_expr_against_target(
                        wrapper_arg,
                        expected.args[0],
                        env=env,
                        allow_missing_id=False,
                    )
            elif expr.callee == ["err"]:
                wrapper_arg = self.first_positional_expr(expr)
                if wrapper_arg is not None:
                    self.validate_expr_against_target(
                        wrapper_arg,
                        expected.args[1],
                        env=env,
                        allow_missing_id=False,
                    )
            return
        if expected.name == "Option" and expected.args and expr.callee == ["some"]:
            wrapper_arg = self.first_positional_expr(expr)
            if wrapper_arg is not None:
                self.validate_expr_against_target(
                    wrapper_arg,
                    expected.args[0],
                    env=env,
                    allow_missing_id=False,
                )

    def response_body_expr(self, expr: Expr) -> Expr | None:
        if not isinstance(expr, CallExpr) or expr.callee != ["response"]:
            return None
        positional_index = 0
        for arg in expr.args:
            if arg.name == "body":
                return arg.expr
            if arg.name is None:
                if positional_index == 1:
                    return arg.expr
                positional_index += 1
        return None

    def first_positional_expr(self, expr: CallExpr) -> Expr | None:
        for arg in expr.args:
            if arg.name is None:
                return arg.expr
        return None

    def validate_response_ok_target(
        self,
        expr: CallExpr,
        expected_body: TypeRef,
        env: dict[str, TypeRef],
    ) -> None:
        if expected_body.name != "Result" or len(expected_body.args) != 2:
            return
        body_arg = self.builtin_arg_expr(expr, "body", positional_index=1)
        if body_arg is None:
            return
        self.validate_expr_against_target(
            body_arg,
            expected_body.args[0],
            env=env,
            allow_missing_id=False,
        )

    def validate_response_err_target(self, expr: CallExpr, expected_body: TypeRef) -> None:
        if expected_body.name != "Result" or len(expected_body.args) != 2:
            return
        error_type = expected_body.args[1]
        record = self.types.get(error_type.name)
        if record is None:
            return
        fields = {field.name: field for field in record.fields}
        code = fields.get("code")
        message = fields.get("message")
        if code is None or message is None:
            self.error(
                f"`response_err` requires `{error_type.render()}` to declare `code` and `message` fields.",
                expr.location,
                "Use an ErrorBody-style record with `code: Text` and `message: Text`.",
            )
            return
        if code.type_ref.name != "Text" or message.type_ref.name != "Text":
            self.error(
                f"`response_err` requires `{error_type.render()}.code` and `.message` to be `Text`.",
                expr.location,
                "Use text fields for response error code and message.",
            )
        extra_required = [
            field.name
            for field in record.fields
            if field.name not in {"code", "message"} and not self.is_optional(field.type_ref)
        ]
        if extra_required:
            self.error(
                f"`response_err` cannot construct `{error_type.render()}` because it has extra required fields: {', '.join(extra_required)}.",
                expr.location,
                "Use only `code` and `message` as required error fields, or call `response(status, body: err(...))` directly.",
            )

    def builtin_arg_expr(self, expr: CallExpr, name: str, *, positional_index: int) -> Expr | None:
        current_positional = 0
        for arg in expr.args:
            if arg.name == name:
                return arg.expr
            if arg.name is None:
                if current_positional == positional_index:
                    return arg.expr
                current_positional += 1
        return None

    def infer_expr(self, expr: Expr, env: dict[str, TypeRef], *, context_kind: str | None = None) -> TypeRef:
        if isinstance(expr, LiteralExpr):
            if expr.value is None:
                return TypeRef("Unknown")
            if isinstance(expr.value, bool):
                return TypeRef("Bool")
            if isinstance(expr.value, int):
                return TypeRef("Int")
            if isinstance(expr.value, float):
                return TypeRef("Float")
            return TypeRef("Text")
        if isinstance(expr, ListExpr):
            if not expr.items:
                return TypeRef("List", [TypeRef("Unknown")])
            first = self.infer_expr(expr.items[0], env, context_kind=context_kind)
            for item in expr.items[1:]:
                actual = self.infer_expr(item, env, context_kind=context_kind)
                if not self.type_matches(first, actual):
                    self.error(
                        f"List item type mismatch: expected `{first.render()}`, found `{actual.render()}`.",
                        item.location,
                        "Use one item type per list literal in v0.",
                    )
            return TypeRef("List", [first])
        if isinstance(expr, RecordExpr):
            return TypeRef("RecordLiteral")
        if isinstance(expr, BinaryExpr):
            self.infer_expr(expr.left, env, context_kind=context_kind)
            self.infer_expr(expr.right, env, context_kind=context_kind)
            return TypeRef("Bool")
        if isinstance(expr, PathExpr):
            return self.infer_path(expr.parts, env, expr.location)
        if isinstance(expr, CallExpr):
            return self.infer_call(expr, env, context_kind=context_kind)
        return TypeRef("Unknown")

    def infer_path(
        self, parts: list[str], env: dict[str, TypeRef], location: SourceLocation
    ) -> TypeRef:
        enum_type = self.enum_variant_type(parts, location)
        if enum_type is not None:
            return enum_type
        if not parts:
            return TypeRef("Unknown")
        root = env.get(parts[0])
        if parts[0] == "request" and len(parts) >= 2 and parts[1] == "body":
            request_type = root or TypeRef("Request")
            body_type = request_type.args[0] if request_type.args else None
            if len(parts) == 2:
                return body_type or TypeRef("Unknown")
            if body_type is None:
                return TypeRef("Text")
            current = body_type
            for field in parts[2:]:
                record = self.types.get(current.name)
                if record is None:
                    return TypeRef("Unknown")
                match = next((decl for decl in record.fields if decl.name == field), None)
                if match is None:
                    self.error(
                        f"Type `{current.render()}` has no field `{field}`.",
                        location,
                        "Check the route body record declaration.",
                        code="SLC062",
                    )
                    return TypeRef("Unknown")
                current = match.type_ref
            return current
        if parts[0] in self.configs:
            config = self.configs[parts[0]]
            if len(parts) == 1:
                return TypeRef(config.name)
            current_fields = {field.name: field.type_ref for field in config.fields}
            field_type = current_fields.get(parts[1])
            if field_type is None:
                self.error(
                    f"Config `{config.name}` has no field `{parts[1]}`.",
                    location,
                    "Check the config declaration.",
                    code="SLC071",
                )
                return TypeRef("Unknown")
            return field_type
        if root is None:
            if parts[0] in self.unit.imported_modules:
                self.error(
                    f"Unresolved imported symbol `{'.'.join(parts)}`.",
                    location,
                    "Check the imported module declarations and the qualified name.",
                    code="SLC020",
                )
                return TypeRef("Unknown")
            self.error(f"Unknown value `{parts[0]}`.", location, "Declare it with `let` or as a parameter.")
            return TypeRef("Unknown")
        current = root
        for field in parts[1:]:
            record = self.types.get(current.name)
            if record is None:
                return TypeRef("Unknown")
            match = next((decl for decl in record.fields if decl.name == field), None)
            if match is None:
                self.error(
                    f"Type `{current.render()}` has no field `{field}`.",
                    location,
                    "Check the record declaration.",
                )
                return TypeRef("Unknown")
            current = match.type_ref
        return current

    def infer_call(self, expr: CallExpr, env: dict[str, TypeRef], *, context_kind: str | None = None) -> TypeRef:
        name = ".".join(expr.callee)
        if expr.callee == ["request", "header"]:
            return self.infer_request_header_call(expr, env, context_kind=context_kind or self.context_kind)
        if len(expr.callee) == 2 and expr.callee[0] in self.stores:
            return self.infer_store_call(expr, env)
        if len(expr.callee) == 1 and expr.callee[0] in {"some", "none", "ok", "err"}:
            return self.infer_wrapper_constructor(expr, env)
        if len(expr.callee) == 1 and expr.callee[0] in {
            "response",
            "response_ok",
            "response_err",
            "env",
            "env_int",
            "uuid",
            "now",
            "read_text",
            "write_text",
        }:
            return self.infer_builtin_call(expr, env, context_kind=context_kind or self.context_kind)
        function = self.functions.get(name) or self.imported_functions.get(name)
        if function is not None:
            if function.kind == "command" and self.context_kind != "test":
                self.error(
                    f"Command `{function.name}` cannot be called from `{self.context_kind}`.",
                    expr.location,
                    "Move shared logic into a pure `fn`, then call it from commands, routes, or tests.",
                )
            ordered_args = self.bind_call_args(expr, function)
            for arg, param in ordered_args:
                actual = self.infer_expr(arg.expr, env, context_kind=context_kind)
                if not self.type_matches(param.type_ref, actual):
                    self.error(
                        f"Argument `{param.name}` expected `{param.type_ref.render()}`, found `{actual.render()}`.",
                        arg.location,
                        "Pass a value with the declared parameter type.",
                    )
            return function.return_type
        if len(expr.callee) == 1 and expr.callee[0] in self.types:
            return TypeRef(expr.callee[0])
        if expr.callee and expr.callee[0] in self.unit.imported_modules:
            self.error(
                f"Unresolved imported symbol `{name}`.",
                expr.location,
                "Check the imported module declarations and the qualified function name.",
                code="SLC020",
            )
        else:
            self.error(f"Unknown function or constructor `{name}`.", expr.location, "Declare it before use.")
        return TypeRef("Unknown")

    def infer_request_header_call(
        self,
        expr: CallExpr,
        env: dict[str, TypeRef],
        *,
        context_kind: str,
    ) -> TypeRef:
        if context_kind != "route":
            self.error(
                "`request.header` is only allowed in route blocks.",
                expr.location,
                "Read HTTP headers inside a route, then pass validated values to shared logic.",
                code="SLC080",
            )
        if "request" not in env:
            self.error(
                "`request.header` requires a route request context.",
                expr.location,
                "Use `request.header` only inside route bodies.",
                code="SLC081",
            )
        args = self.bind_builtin_args(expr, ["name"], required=["name"])
        self.check_bound_arg_type(args, env, "name", TypeRef("Text"), context_kind)
        return TypeRef("Option", [TypeRef("Text")])

    def bind_call_args(self, expr: CallExpr, function: FunctionDecl) -> list[tuple[Arg, Param]]:
        params_by_name = {param.name: param for param in function.params}
        bound: dict[str, Arg] = {}
        ordered: list[tuple[Arg, Param]] = []
        seen_named = False
        positional_index = 0
        for arg in expr.args:
            if arg.name is None:
                if seen_named:
                    self.error(
                        "Positional arguments cannot follow named arguments.",
                        arg.location,
                        "Move positional arguments before named arguments.",
                        code="SLC021",
                    )
                    continue
                if positional_index >= len(function.params):
                    self.error(
                        f"Function `{function.name}` called with too many arguments.",
                        arg.location,
                        "Remove extra arguments or update the function signature.",
                        code="SLC022",
                    )
                    continue
                param = function.params[positional_index]
                bound[param.name] = arg
                ordered.append((arg, param))
                positional_index += 1
                continue
            seen_named = True
            param = params_by_name.get(arg.name)
            if param is None:
                self.error(
                    f"Function `{function.name}` has no parameter `{arg.name}`.",
                    arg.location,
                    "Use a declared parameter name.",
                    code="SLC023",
                )
                continue
            if arg.name in bound:
                self.error(
                    f"Argument `{arg.name}` is provided more than once.",
                    arg.location,
                    "Provide each argument once.",
                    code="SLC024",
                )
                continue
            bound[arg.name] = arg
        for param in function.params:
            arg = bound.get(param.name)
            if arg is None:
                self.error(
                    f"Missing argument `{param.name}` for function `{function.name}`.",
                    expr.location,
                    "Pass every required argument.",
                    code="SLC025",
                )
                continue
            if (arg, param) not in ordered:
                ordered.append((arg, param))
        return ordered

    def infer_store_call(self, expr: CallExpr, env: dict[str, TypeRef]) -> TypeRef:
        store = self.stores[expr.callee[0]]
        method = expr.callee[1]
        item_type = store.type_ref
        if self.context_kind == "fn":
            self.error(
                f"Pure fn cannot call store method `{expr.callee[0]}.{method}`.",
                expr.location,
                "Use store methods only from `command`, `route`, or `test` blocks.",
            )
        if method not in STORE_METHODS:
            self.error(
                f"Unknown store method `{'.'.join(expr.callee)}`.",
                expr.location,
                "Use insert, all, get, update, try_update, delete, filter, count, exists, or clear.",
            )
            return TypeRef("Unknown")
        if method != "filter":
            for arg in expr.args:
                if arg.name is not None:
                    self.error(
                        f"Store method `{'.'.join(expr.callee)}` does not accept named arguments.",
                        arg.location,
                        "Use positional arguments for this store method.",
                        code="SLC050",
                    )
        if method == "insert":
            self.expect_arg_count(expr, 1)
            if expr.args:
                if isinstance(expr.args[0].expr, RecordExpr):
                    self.validate_record_expr(expr.args[0].expr, item_type, allow_missing_id=True, env=env)
                else:
                    self.error(
                        "Store insert requires a record literal in v0.4.",
                        expr.args[0].location,
                        "Use `items.insert({ field: value })`.",
                    )
            return item_type
        if method == "all":
            self.expect_arg_count(expr, 0)
            return TypeRef("List", [item_type])
        if method == "count":
            self.expect_arg_count(expr, 0)
            return TypeRef("Int")
        if method == "get":
            self.expect_arg_count(expr, 1)
            self.check_store_id_arg(expr, env, item_type)
            return TypeRef("Option", [item_type])
        if method == "exists":
            self.expect_arg_count(expr, 1)
            self.check_store_id_arg(expr, env, item_type)
            return TypeRef("Bool")
        if method == "update":
            self.expect_arg_count(expr, 2)
            self.check_store_id_arg(expr, env, item_type)
            if len(expr.args) >= 2:
                if isinstance(expr.args[1].expr, RecordExpr):
                    self.validate_record_expr(expr.args[1].expr, item_type, allow_missing_id=True, env=env)
                else:
                    self.error(
                        "Store update requires a record literal in v0.4.",
                        expr.args[1].location,
                        "Use `items.update(id, { field: value })`.",
                    )
            return item_type
        if method == "try_update":
            self.expect_arg_count(expr, 2)
            self.check_store_id_arg(expr, env, item_type)
            if len(expr.args) >= 2:
                if isinstance(expr.args[1].expr, RecordExpr):
                    self.validate_record_expr(expr.args[1].expr, item_type, allow_missing_id=True, env=env)
                else:
                    self.error(
                        "Store try_update requires a record literal.",
                        expr.args[1].location,
                        "Use `items.try_update(id, { field: value })`.",
                    )
            return TypeRef("Option", [item_type])
        if method == "delete":
            self.expect_arg_count(expr, 1)
            self.check_store_id_arg(expr, env, item_type)
            return TypeRef("Bool")
        if method == "clear":
            self.expect_arg_count(expr, 0)
            if self.context_kind != "test":
                self.error(
                    f"Store method `{'.'.join(expr.callee)}` is only allowed in tests.",
                    expr.location,
                    "Use `clear()` only from test blocks.",
                    code="SLC051",
                )
            return TypeRef("Int")
        if method == "filter":
            record = self.types.get(item_type.name)
            fields = {field.name: field for field in record.fields} if record else {}
            for arg in expr.args:
                if arg.name is None:
                    self.error(
                        "Store filter requires named arguments.",
                        arg.location,
                        "Use `items.filter(field: value)`.",
                    )
                elif arg.name not in fields:
                    self.error(
                        f"Type `{item_type.render()}` has no field `{arg.name}`.",
                        arg.location,
                        "Filter by a declared record field.",
                    )
                else:
                    actual = self.infer_expr(arg.expr, env, context_kind=self.context_kind)
                    expected = fields[arg.name].type_ref
                    if not self.type_matches(expected, actual):
                        self.error(
                            f"Filter `{arg.name}` expected `{expected.render()}`, found `{actual.render()}`.",
                            arg.location,
                            "Use a filter value that matches the field type.",
                        )
            return TypeRef("List", [item_type])
        return TypeRef("Unknown")

    def infer_builtin_call(
        self,
        expr: CallExpr,
        env: dict[str, TypeRef],
        *,
        context_kind: str,
    ) -> TypeRef:
        name = expr.callee[0]
        if name == "response":
            args = self.bind_builtin_args(expr, ["status", "body", "headers"], required=["status", "body"])
            status_arg = args.get("status")
            body_arg = args.get("body")
            if status_arg is None or body_arg is None:
                return TypeRef("Response", [TypeRef("Unknown")])
            status_type = self.infer_expr(status_arg.expr, env, context_kind=context_kind)
            if status_type.name != "Int":
                self.error("response status requires Int.", status_arg.location, "Pass an integer HTTP status.")
            body_type = self.infer_expr(body_arg.expr, env, context_kind=context_kind)
            headers_arg = args.get("headers")
            if headers_arg is not None:
                if not isinstance(headers_arg.expr, RecordExpr):
                    self.error("response headers require a record literal.", headers_arg.location, "Use `{ name: value }` headers.")
                else:
                    for field in headers_arg.expr.fields:
                        header_type = self.infer_expr(field.expr, env, context_kind=context_kind)
                        if header_type.name != "Text":
                            self.error(
                                f"response header `{field.name}` expected `Text`, found `{header_type.render()}`.",
                                field.location,
                                "Use text values for response headers.",
                            )
            return TypeRef("Response", [body_type])
        if name == "response_ok":
            args = self.bind_builtin_args(expr, ["status", "body", "headers"], required=["status", "body"])
            status_arg = args.get("status")
            body_arg = args.get("body")
            if status_arg is None or body_arg is None:
                return TypeRef("Response", [TypeRef("Result", [TypeRef("Unknown"), TypeRef("Unknown")])])
            status_type = self.infer_expr(status_arg.expr, env, context_kind=context_kind)
            if status_type.name != "Int":
                self.error("response_ok status requires Int.", status_arg.location, "Pass an integer HTTP status.")
            body_type = self.infer_expr(body_arg.expr, env, context_kind=context_kind)
            self.check_response_headers(args, env, context_kind)
            return TypeRef("Response", [TypeRef("Result", [body_type, TypeRef("Unknown")])])
        if name == "response_err":
            args = self.bind_builtin_args(
                expr,
                ["status", "code", "message", "headers"],
                required=["status", "code", "message"],
            )
            status_arg = args.get("status")
            if status_arg is None:
                return TypeRef("Response", [TypeRef("Result", [TypeRef("Unknown"), TypeRef("Unknown")])])
            status_type = self.infer_expr(status_arg.expr, env, context_kind=context_kind)
            if status_type.name != "Int":
                self.error("response_err status requires Int.", status_arg.location, "Pass an integer HTTP status.")
            self.check_bound_arg_type(args, env, "code", TypeRef("Text"), context_kind)
            self.check_bound_arg_type(args, env, "message", TypeRef("Text"), context_kind)
            self.check_response_headers(args, env, context_kind)
            return TypeRef("Response", [TypeRef("Result", [TypeRef("Unknown"), TypeRef("Unknown")])])
        if name == "env":
            args = self.bind_builtin_args(expr, ["name", "default"], required=["name", "default"])
            self.check_bound_arg_type(args, env, "name", TypeRef("Text"), context_kind)
            self.check_bound_arg_type(args, env, "default", TypeRef("Text"), context_kind)
            return TypeRef("Text")
        if name == "env_int":
            args = self.bind_builtin_args(expr, ["name", "default"], required=["name", "default"])
            self.check_bound_arg_type(args, env, "name", TypeRef("Text"), context_kind)
            self.check_bound_arg_type(args, env, "default", TypeRef("Int"), context_kind)
            return TypeRef("Int")
        if name in {"uuid", "now"}:
            self.bind_builtin_args(expr, [], required=[])
            return TypeRef("Text")
        if name == "read_text":
            if context_kind not in {"command", "route", "test"}:
                self.error("`read_text` is only allowed in command, route, and test blocks.", expr.location, "Move file reads out of pure functions and config defaults.")
            args = self.bind_builtin_args(expr, ["path"], required=["path"])
            self.check_bound_arg_type(args, env, "path", TypeRef("Text"), context_kind)
            return TypeRef("Text")
        if name == "write_text":
            if context_kind not in {"command", "test"}:
                self.error("`write_text` is only allowed in command and test blocks.", expr.location, "Move file writes out of pure functions and routes.")
            args = self.bind_builtin_args(expr, ["path", "content"], required=["path", "content"])
            self.check_bound_arg_type(args, env, "path", TypeRef("Text"), context_kind)
            self.check_bound_arg_type(args, env, "content", TypeRef("Text"), context_kind)
            return TypeRef("Bool")
        return TypeRef("Unknown")

    def check_response_headers(
        self,
        args: dict[str, Arg],
        env: dict[str, TypeRef],
        context_kind: str,
    ) -> None:
        headers_arg = args.get("headers")
        if headers_arg is None:
            return
        if not isinstance(headers_arg.expr, RecordExpr):
            self.error("response headers require a record literal.", headers_arg.location, "Use `{ name: value }` headers.")
            return
        for field in headers_arg.expr.fields:
            header_type = self.infer_expr(field.expr, env, context_kind=context_kind)
            if header_type.name != "Text":
                self.error(
                    f"response header `{field.name}` expected `Text`, found `{header_type.render()}`.",
                    field.location,
                    "Use text values for response headers.",
                )

    def bind_builtin_args(self, expr: CallExpr, allowed: list[str], *, required: list[str]) -> dict[str, Arg]:
        builtin_name = ".".join(expr.callee)
        bound: dict[str, Arg] = {}
        seen_named = False
        positional_index = 0
        for arg in expr.args:
            if arg.name is None:
                if seen_named:
                    self.error(
                        "Positional arguments cannot follow named arguments.",
                        arg.location,
                        "Move positional arguments before named arguments.",
                        code="SLC021",
                    )
                    continue
                if positional_index >= len(allowed):
                    self.error(
                        f"Builtin `{builtin_name}` called with too many arguments.",
                        arg.location,
                        "Remove extra arguments.",
                        code="SLC022",
                    )
                    continue
                bound[allowed[positional_index]] = arg
                positional_index += 1
                continue
            seen_named = True
            if arg.name not in allowed:
                self.error(
                    f"Builtin `{builtin_name}` has no argument `{arg.name}`.",
                    arg.location,
                    "Use a documented builtin argument name.",
                    code="SLC023",
                )
                continue
            if arg.name in bound:
                self.error(
                    f"Argument `{arg.name}` is provided more than once.",
                    arg.location,
                    "Provide each argument once.",
                    code="SLC024",
                )
                continue
            bound[arg.name] = arg
        for name in required:
            if name not in bound:
                self.error(
                    f"Missing argument `{name}` for builtin `{builtin_name}`.",
                    expr.location,
                    "Pass every required argument.",
                    code="SLC025",
                )
        return bound

    def check_bound_arg_type(
        self,
        args: dict[str, Arg],
        env: dict[str, TypeRef],
        name: str,
        expected: TypeRef,
        context_kind: str,
    ) -> None:
        arg = args.get(name)
        if arg is None:
            return
        actual = self.infer_expr(arg.expr, env, context_kind=context_kind)
        if not self.type_matches(expected, actual):
            self.error(
                f"Argument `{name}` expected `{expected.render()}`, found `{actual.render()}`.",
                arg.location,
                "Pass a value with the expected type.",
            )

    def named_arg(self, expr: CallExpr, name: str) -> Arg | None:
        return next((arg for arg in expr.args if arg.name == name), None)

    def check_arg_type(
        self,
        expr: CallExpr,
        env: dict[str, TypeRef],
        index: int,
        expected: TypeRef,
        context_kind: str,
    ) -> None:
        if len(expr.args) <= index:
            return
        actual = self.infer_expr(expr.args[index].expr, env, context_kind=context_kind)
        if not self.type_matches(expected, actual):
            self.error(
                f"Argument {index + 1} expected `{expected.render()}`, found `{actual.render()}`.",
                expr.args[index].location,
                "Pass a value with the expected type.",
            )

    def check_store_id_arg(self, expr: CallExpr, env: dict[str, TypeRef], item_type: TypeRef) -> None:
        if not expr.args:
            return
        actual = self.infer_expr(expr.args[0].expr, env)
        expected = TypeRef("Id", [item_type])
        if actual.name == "Int":
            if not isinstance(expr.args[0].expr, LiteralExpr):
                self.warn(
                    f"`{'.'.join(expr.callee)}` id accepts `Int`, but `{expected.render()}` is more precise.",
                    expr.args[0].location,
                    f"Prefer declaring ids at command or request-body boundaries as `{expected.render()}`.",
                    code="SLC052",
                )
            return
        if not self.type_matches(expected, actual):
            self.error(
                f"`{'.'.join(expr.callee)}` id expected `Int` or `{expected.render()}`, found `{actual.render()}`.",
                expr.args[0].location,
                "Pass a store id value.",
            )

    def infer_wrapper_constructor(self, expr: CallExpr, env: dict[str, TypeRef]) -> TypeRef:
        callee = expr.callee[0]
        for arg in expr.args:
            if arg.name is not None:
                self.error(
                    f"`{callee}` does not accept named arguments.",
                    arg.location,
                    "Use positional arguments for wrapper constructors.",
                    code="SLC053",
                )
        if callee == "none":
            self.expect_arg_count(expr, 0)
            return TypeRef("Option", [TypeRef("Unknown")])
        self.expect_arg_count(expr, 1)
        value_type = self.infer_expr(expr.args[0].expr, env, context_kind=self.context_kind) if expr.args else TypeRef("Unknown")
        if callee == "some":
            return TypeRef("Option", [value_type])
        if callee == "ok":
            return TypeRef("Result", [value_type, TypeRef("Unknown")])
        return TypeRef("Result", [TypeRef("Unknown"), value_type])

    def validate_record_expr(
        self,
        expr: RecordExpr,
        expected: TypeRef,
        *,
        allow_missing_id: bool,
        env: dict[str, TypeRef],
    ) -> None:
        record = self.types.get(expected.name)
        if record is None:
            return
        fields = {field.name: field for field in record.fields}
        provided: dict[str, object] = {}
        seen_fields: set[str] = set()
        for field in expr.fields:
            if field.name in seen_fields:
                self.error(
                    f"Field `{field.name}` is provided more than once.",
                    field.location,
                    "Provide each record field once.",
                    code="SLC030",
                )
                continue
            seen_fields.add(field.name)
            provided[field.name] = field
            expected_field = fields.get(field.name)
            if expected_field is None:
                self.error(
                    f"Type `{expected.render()}` has no field `{field.name}`.",
                    field.location,
                    "Remove the field or add it to the type declaration.",
                )
                continue
            actual = self.infer_expr(field.expr, env, context_kind=self.context_kind)
            if not self.type_matches(expected_field.type_ref, actual):
                self.error(
                    f"Field `{field.name}` expected `{expected_field.type_ref.render()}`, found `{actual.render()}`.",
                    field.location,
                    "Use a value matching the declared field type.",
                )
        for field in record.fields:
            if allow_missing_id and field.name == "id":
                continue
            if field.name not in provided and not self.is_optional(field.type_ref):
                self.error(
                    f"Missing required field `{field.name}` for `{expected.render()}`.",
                    expr.location,
                    "Provide all required record fields.",
                )

    def enum_variant_type(self, parts: list[str], location: SourceLocation) -> TypeRef | None:
        if len(parts) == 2:
            enum_name, variant = parts
        elif len(parts) == 3:
            enum_name, variant = ".".join(parts[:2]), parts[2]
        else:
            return None
        enum_decl = self.enums.get(enum_name)
        if enum_decl is None:
            return None
        if variant not in enum_decl.variants:
            self.error(
                f"Enum `{enum_name}` has no variant `{variant}`.",
                location,
                "Use one of the declared enum variants.",
            )
            return TypeRef("Unknown")
        return TypeRef(enum_name)

    def check_type_ref(self, type_ref: TypeRef, location: SourceLocation) -> None:
        if type_ref.name in PRIMITIVES or type_ref.name in self.types or type_ref.name in self.enums:
            if type_ref.args:
                self.error(
                    f"`{type_ref.name}` does not accept type arguments.",
                    location,
                    "Remove the generic arguments.",
                )
            return
        if type_ref.name in {"Request", "Response"}:
            if len(type_ref.args) > 1:
                self.error(f"`{type_ref.name}` expects at most one type argument.", location, "Use zero or one argument.")
            for arg in type_ref.args:
                self.check_type_ref(arg, location)
            return
        if type_ref.name in GENERIC_ARITY:
            expected = GENERIC_ARITY[type_ref.name]
            if len(type_ref.args) != expected:
                self.error(
                    f"`{type_ref.name}` expects {expected} type argument(s).",
                    location,
                    f"Use exactly {expected} generic argument(s).",
                )
            for arg in type_ref.args:
                self.check_type_ref(arg, location)
            return
        if type_ref.name == "Unknown":
            return
        self.error(f"Unknown type `{type_ref.render()}`.", location, "Declare the type or use a built-in type.")

    def type_matches(self, expected: TypeRef, actual: TypeRef) -> bool:
        if actual.name in {"Unknown", "RecordLiteral"}:
            return True
        if expected.name == "Float" and actual.name == "Int":
            return True
        if expected.name != actual.name:
            return False
        if len(expected.args) != len(actual.args):
            return False
        return all(self.type_matches(left, right) for left, right in zip(expected.args, actual.args))

    def expect_arg_count(self, expr: CallExpr, count: int) -> None:
        if len(expr.args) != count:
            self.error(
                f"`{'.'.join(expr.callee)}` expects {count} argument(s), found {len(expr.args)}.",
                expr.location,
                f"Pass exactly {count} argument(s).",
            )

    def is_optional(self, type_ref: TypeRef) -> bool:
        return type_ref.name == "Option"

    def is_json_encodable(self, type_ref: TypeRef) -> bool:
        if type_ref.name in PRIMITIVES or type_ref.name == "Unknown":
            return True
        if type_ref.name == "Id":
            return bool(type_ref.args)
        if type_ref.name in self.enums:
            return True
        if type_ref.name in self.types:
            record = self.types[type_ref.name]
            return all(self.is_json_encodable(field.type_ref) for field in record.fields)
        if type_ref.name in {"List", "Option"} and len(type_ref.args) == 1:
            return self.is_json_encodable(type_ref.args[0])
        if type_ref.name == "Result" and len(type_ref.args) == 2:
            return self.is_json_encodable(type_ref.args[0]) and self.is_json_encodable(type_ref.args[1])
        if type_ref.name == "Response" and len(type_ref.args) <= 1:
            return not type_ref.args or self.is_json_encodable(type_ref.args[0])
        return False

    def error(
        self,
        message: str,
        location: SourceLocation,
        suggestion: str,
        *,
        code: str = "SLC001",
    ) -> None:
        self.diagnostics.append(Diagnostic(message, location, suggestion, code=code))

    def warn(
        self,
        message: str,
        location: SourceLocation,
        suggestion: str,
        *,
        code: str = "SLCW001",
    ) -> None:
        self.diagnostics.append(Diagnostic(message, location, suggestion, severity="warning", code=code))


def check_program(unit: Unit, *, source_path: Path, strict_intent: bool = False) -> list[Diagnostic]:
    return check_program_result(unit, source_path=source_path, strict_intent=strict_intent).diagnostics


def check_program_result(unit: Unit, *, source_path: Path, strict_intent: bool = False) -> CheckResult:
    return Checker(unit, source_path=source_path, strict_intent=strict_intent).run_result()
