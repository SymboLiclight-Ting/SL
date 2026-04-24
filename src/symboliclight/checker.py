from __future__ import annotations

from pathlib import Path

from symboliclight.ast import (
    App,
    AssertStmt,
    BinaryExpr,
    CallExpr,
    EnumDecl,
    Expr,
    FieldDecl,
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
STORE_METHODS = {"insert", "all", "get", "update", "delete", "filter"}


class Checker:
    def __init__(
        self,
        unit: Unit,
        *,
        source_path: Path,
        strict_intent: bool = False,
        seen: set[Path] | None = None,
    ) -> None:
        self.unit = unit
        self.source_path = source_path.resolve()
        self.strict_intent = strict_intent
        self.seen = seen or set()
        self.diagnostics: list[Diagnostic] = []
        self.context_kind = "fn"

        self.types = {type_decl.name: type_decl for type_decl in unit.types}
        self.enums = {enum_decl.name: enum_decl for enum_decl in unit.enums}
        self.functions = {function.name: function for function in unit.functions}
        self.imported_functions: dict[str, FunctionDecl] = {}

        if isinstance(unit, App):
            self.stores = {store.name: store for store in unit.stores}
        else:
            self.stores = {}

    def run(self) -> list[Diagnostic]:
        self.load_imports()
        self.check_duplicate_names()
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
        return self.diagnostics

    def load_imports(self) -> None:
        for import_decl in self.unit.imports:
            import_path = (self.source_path.parent / import_decl.path).resolve()
            if import_path in self.seen:
                self.error(
                    f"Cyclic import detected for `{import_decl.path}`.",
                    import_decl.location,
                    "Break the import cycle or move shared declarations into a lower-level module.",
                )
                continue
            if not import_path.exists():
                self.error(
                    f"Import file not found: {import_decl.path}",
                    import_decl.location,
                    "Create the module file or fix the import path.",
                )
                continue
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
                )
                continue
            nested_checker = Checker(
                imported,
                source_path=import_path,
                strict_intent=self.strict_intent,
                seen={*self.seen, self.source_path},
            )
            self.diagnostics.extend(nested_checker.run())
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

    def check_intents(self) -> None:
        assert isinstance(self.unit, App)
        for intent in self.unit.intents:
            path = (self.source_path.parent / intent).resolve()
            if not path.exists():
                self.error(
                    f"IntentSpec file not found: {intent}",
                    self.unit.location,
                    "Create the intent file or remove the intent declaration.",
                )
                continue
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
                    "Use `permissions from intent.permissions` in v0.2.",
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
                "Use `test from intent.acceptance` in v0.2.",
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
                "Use GET, POST, PUT, PATCH, or DELETE in v0.2.",
            )
        self.check_type_ref(route.return_type, route.location)
        env = {"request": TypeRef("Request")}
        self.check_block(route.body, expected_return=route.return_type, local_env=env, context_kind="route")

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
                    env[statement.name] = self.infer_expr(statement.expr, env)
                elif isinstance(statement, ReturnStmt):
                    if expected_return is not None and isinstance(statement.expr, RecordExpr):
                        self.validate_record_expr(
                            statement.expr,
                            expected_return,
                            allow_missing_id=False,
                            env=env,
                        )
                    actual = self.infer_expr(statement.expr, env)
                    if expected_return is not None and not self.type_matches(expected_return, actual):
                        self.error(
                            f"Return type mismatch: expected `{expected_return.render()}`, found `{actual.render()}`.",
                            statement.location,
                            "Return a value that matches the declared type.",
                        )
                elif isinstance(statement, AssertStmt):
                    actual = self.infer_expr(statement.expr, env)
                    if actual.name != "Bool":
                        self.error("assert requires Bool.", statement.location, "Compare values or return a Bool.")
                elif isinstance(statement, IfStmt):
                    actual = self.infer_expr(statement.condition, env)
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
                    self.infer_expr(statement.expr, env)
        finally:
            self.context_kind = previous_context

    def infer_expr(self, expr: Expr, env: dict[str, TypeRef]) -> TypeRef:
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
            first = self.infer_expr(expr.items[0], env)
            for item in expr.items[1:]:
                actual = self.infer_expr(item, env)
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
            self.infer_expr(expr.left, env)
            self.infer_expr(expr.right, env)
            return TypeRef("Bool")
        if isinstance(expr, PathExpr):
            return self.infer_path(expr.parts, env, expr.location)
        if isinstance(expr, CallExpr):
            return self.infer_call(expr, env)
        return TypeRef("Unknown")

    def infer_path(
        self, parts: list[str], env: dict[str, TypeRef], location: SourceLocation
    ) -> TypeRef:
        enum_type = self.enum_variant_type(parts, location)
        if enum_type is not None:
            return enum_type
        if len(parts) == 3 and parts[0] == "request" and parts[1] == "body":
            return TypeRef("Text")
        if not parts:
            return TypeRef("Unknown")
        root = env.get(parts[0])
        if root is None:
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

    def infer_call(self, expr: CallExpr, env: dict[str, TypeRef]) -> TypeRef:
        name = ".".join(expr.callee)
        if len(expr.callee) == 2 and expr.callee[0] in self.stores:
            return self.infer_store_call(expr, env)
        if len(expr.callee) == 1 and expr.callee[0] in {"some", "none", "ok", "err"}:
            return self.infer_wrapper_constructor(expr, env)
        function = self.functions.get(name) or self.imported_functions.get(name)
        if function is not None:
            if function.kind == "command" and self.context_kind != "test":
                self.error(
                    f"Command `{function.name}` cannot be called from `{self.context_kind}`.",
                    expr.location,
                    "Move shared logic into a pure `fn`, then call it from commands, routes, or tests.",
                )
            positional = [arg for arg in expr.args if arg.name is None]
            if len(positional) != len(function.params):
                self.error(
                    f"Function `{function.name}` called with wrong argument count.",
                    expr.location,
                    "Pass one positional argument for each declared parameter.",
                )
            for arg, param in zip(positional, function.params):
                actual = self.infer_expr(arg.expr, env)
                if not self.type_matches(param.type_ref, actual):
                    self.error(
                        f"Argument `{param.name}` expected `{param.type_ref.render()}`, found `{actual.render()}`.",
                        arg.location,
                        "Pass a value with the declared parameter type.",
                    )
            return function.return_type
        if len(expr.callee) == 1 and expr.callee[0] in self.types:
            return TypeRef(expr.callee[0])
        self.error(f"Unknown function or constructor `{name}`.", expr.location, "Declare it before use.")
        return TypeRef("Unknown")

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
                "Use insert, all, get, update, delete, or filter.",
            )
            return TypeRef("Unknown")
        if method == "insert":
            self.expect_arg_count(expr, 1)
            if expr.args:
                if isinstance(expr.args[0].expr, RecordExpr):
                    self.validate_record_expr(expr.args[0].expr, item_type, allow_missing_id=True, env=env)
                else:
                    self.error(
                        "Store insert requires a record literal in v0.2.",
                        expr.args[0].location,
                        "Use `items.insert({ field: value })`.",
                    )
            return item_type
        if method == "all":
            self.expect_arg_count(expr, 0)
            return TypeRef("List", [item_type])
        if method == "get":
            self.expect_arg_count(expr, 1)
            self.check_store_id_arg(expr, env, item_type)
            return TypeRef("Option", [item_type])
        if method == "update":
            self.expect_arg_count(expr, 2)
            self.check_store_id_arg(expr, env, item_type)
            if len(expr.args) >= 2:
                if isinstance(expr.args[1].expr, RecordExpr):
                    self.validate_record_expr(expr.args[1].expr, item_type, allow_missing_id=True, env=env)
                else:
                    self.error(
                        "Store update requires a record literal in v0.2.",
                        expr.args[1].location,
                        "Use `items.update(id, { field: value })`.",
                    )
            return item_type
        if method == "delete":
            self.expect_arg_count(expr, 1)
            self.check_store_id_arg(expr, env, item_type)
            return TypeRef("Bool")
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
                    actual = self.infer_expr(arg.expr, env)
                    expected = fields[arg.name].type_ref
                    if not self.type_matches(expected, actual):
                        self.error(
                            f"Filter `{arg.name}` expected `{expected.render()}`, found `{actual.render()}`.",
                            arg.location,
                            "Use a filter value that matches the field type.",
                        )
            return TypeRef("List", [item_type])
        return TypeRef("Unknown")

    def check_store_id_arg(self, expr: CallExpr, env: dict[str, TypeRef], item_type: TypeRef) -> None:
        if not expr.args:
            return
        actual = self.infer_expr(expr.args[0].expr, env)
        expected = TypeRef("Id", [item_type])
        if actual.name != "Int" and not self.type_matches(expected, actual):
            self.error(
                f"`{'.'.join(expr.callee)}` id expected `Int` or `{expected.render()}`, found `{actual.render()}`.",
                expr.args[0].location,
                "Pass a store id value.",
            )

    def infer_wrapper_constructor(self, expr: CallExpr, env: dict[str, TypeRef]) -> TypeRef:
        callee = expr.callee[0]
        if callee == "none":
            self.expect_arg_count(expr, 0)
            return TypeRef("Option", [TypeRef("Unknown")])
        self.expect_arg_count(expr, 1)
        value_type = self.infer_expr(expr.args[0].expr, env) if expr.args else TypeRef("Unknown")
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
        provided = {field.name: field for field in expr.fields}
        for field in expr.fields:
            expected_field = fields.get(field.name)
            if expected_field is None:
                self.error(
                    f"Type `{expected.render()}` has no field `{field.name}`.",
                    field.location,
                    "Remove the field or add it to the type declaration.",
                )
                continue
            actual = self.infer_expr(field.expr, env)
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

    def error(self, message: str, location: SourceLocation, suggestion: str) -> None:
        self.diagnostics.append(Diagnostic(message, location, suggestion))


def check_program(unit: Unit, *, source_path: Path, strict_intent: bool = False) -> list[Diagnostic]:
    return Checker(unit, source_path=source_path, strict_intent=strict_intent).run()
