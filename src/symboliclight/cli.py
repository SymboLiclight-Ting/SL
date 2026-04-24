from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from symboliclight.ast import App, TypeRef, Unit
from symboliclight.cache import read_check_cache, write_check_cache
from symboliclight.checker import check_program_result
from symboliclight.codegen import generate_python, generate_python_artifact, generate_schema_hash
from symboliclight.diagnostics import Diagnostic, SourceLocation, SymbolicLightError, raise_if_errors
from symboliclight.formatter import format_unit
from symboliclight.intent import IntentContract, load_intent_contract
from symboliclight.lsp import run_lsp_server
from symboliclight.parser import parse_source, parse_source_result
from symboliclight.schema import generate_schema
from symboliclight.cli_support import contains_line_comment_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slc")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check")
    check_parser.add_argument("source")
    check_parser.add_argument("--strict-intent", action="store_true")
    check_parser.add_argument("--json", action="store_true")
    check_parser.add_argument("--no-cache", action="store_true")

    build_parser = sub.add_parser("build")
    build_parser.add_argument("source")
    build_parser.add_argument("--out", required=True)
    build_parser.add_argument("--strict-intent", action="store_true")
    build_parser.add_argument("--no-source-map", action="store_true")

    schema_parser = sub.add_parser("schema")
    schema_parser.add_argument("source")
    schema_parser.add_argument("--out", required=True)
    schema_parser.add_argument("--strict-intent", action="store_true")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("source")
    run_parser.add_argument("args", nargs=argparse.REMAINDER)

    test_parser = sub.add_parser("test")
    test_parser.add_argument("source")

    fmt_parser = sub.add_parser("fmt")
    fmt_parser.add_argument("source")
    fmt_parser.add_argument("--check", action="store_true")

    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("source")
    doctor_parser.add_argument("--strict-intent", action="store_true")
    doctor_parser.add_argument("--db")

    sub.add_parser("lsp")

    init_parser = sub.add_parser("init")
    init_parser.add_argument("directory")

    new_parser = sub.add_parser("new")
    new_sub = new_parser.add_subparsers(dest="new_kind", required=True)
    new_api = new_sub.add_parser("api")
    new_api.add_argument("name")

    add_parser = sub.add_parser("add")
    add_sub = add_parser.add_subparsers(dest="add_kind", required=True)
    add_route = add_sub.add_parser("route")
    add_route.add_argument("method")
    add_route.add_argument("path")
    add_route.add_argument("source", nargs="?")

    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            _, diagnostics, _ = load_checked_unit(
                Path(args.source),
                strict_intent=args.strict_intent,
                use_cache=not args.no_cache,
            )
            print_diagnostics(diagnostics, json_output=args.json)
            if any(diagnostic.severity == "error" for diagnostic in diagnostics):
                return 1
            if not args.json:
                print("ok")
            return 0
        if args.command == "build":
            app, diagnostics, _ = load_checked_app(
                Path(args.source),
                strict_intent=args.strict_intent,
                use_cache=False,
            )
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            output = Path(args.out)
            artifact = generate_python_artifact(app, generated_path=str(output))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(artifact.code, encoding="utf-8")
            source_map_path = Path(str(output) + ".slmap.json")
            if not args.no_source_map:
                source_map_path.write_text(json.dumps(artifact.source_map, indent=2), encoding="utf-8")
            elif source_map_path.exists():
                source_map_path.unlink()
            print(f"wrote {output}")
            return 0
        if args.command == "schema":
            app, diagnostics, _ = load_checked_app(
                Path(args.source),
                strict_intent=args.strict_intent,
                use_cache=False,
            )
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(generate_schema(app), indent=2), encoding="utf-8")
            print(f"wrote {output}")
            return 0
        if args.command == "run":
            app, diagnostics, _ = load_checked_app(Path(args.source), strict_intent=False, use_cache=False)
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            app_args = args.args[1:] if args.args[:1] == ["--"] else args.args
            with tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "app.py"
                output.write_text(generate_python(app), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(output), *app_args],
                    check=False,
                )
                return completed.returncode
        if args.command == "test":
            source_path = Path(args.source)
            app, diagnostics, _ = load_checked_app(source_path, strict_intent=False, use_cache=False)
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            with tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "app.py"
                output.write_text(generate_python(app), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(output), "test"],
                    check=False,
                )
                if completed.returncode != 0:
                    return completed.returncode
            return run_intent_acceptance(app, source_path)
        if args.command == "fmt":
            return format_file(Path(args.source), check_only=args.check)
        if args.command == "doctor":
            unit, diagnostics, cache_hit = load_checked_unit(Path(args.source), strict_intent=args.strict_intent)
            print_diagnostics(diagnostics)
            print(doctor_report(unit, diagnostics, Path(args.source), cache_hit=cache_hit, db_path=Path(args.db) if args.db else None))
            return 1 if any(diagnostic.severity == "error" for diagnostic in diagnostics) else 0
        if args.command == "lsp":
            run_lsp_server()
            return 0
        if args.command == "init":
            init_project(Path(args.directory))
            print(f"initialized {args.directory}")
            return 0
        if args.command == "new" and args.new_kind == "api":
            new_api_project(args.name, Path.cwd())
            print(f"created {args.name}")
            return 0
        if args.command == "add" and args.add_kind == "route":
            source = Path(args.source) if args.source else discover_source(Path.cwd())
            add_route_to_file(source, args.method, args.path)
            print(f"added route {args.method.upper()} {args.path} to {source}")
            return 0
    except SymbolicLightError as exc:
        print_diagnostics(exc.diagnostics, json_output=getattr(args, "json", False))
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


def load_checked_app(
    source_path: Path,
    *,
    strict_intent: bool,
    use_cache: bool = False,
) -> tuple[App, list[Diagnostic], bool]:
    unit, diagnostics, cache_hit = load_checked_unit(source_path, strict_intent=strict_intent, use_cache=use_cache)
    if not isinstance(unit, App):
        diagnostics.append(
            Diagnostic(
                "Only app files can be built, run, or tested.",
                unit.location,
                "Use `app Name { ... }` for executable programs.",
            )
        )
    raise_if_errors(diagnostics)
    assert isinstance(unit, App)
    return unit, diagnostics, cache_hit


def load_checked_unit(
    source_path: Path,
    *,
    strict_intent: bool,
    use_cache: bool = True,
) -> tuple[Unit, list[Diagnostic], bool]:
    source = source_path.read_text(encoding="utf-8")
    parse_result = parse_source_result(source, path=str(source_path))
    if parse_result.unit is None or any(diagnostic.severity == "error" for diagnostic in parse_result.diagnostics):
        raise SymbolicLightError(parse_result.diagnostics)
    if use_cache:
        cached = read_check_cache(source_path, source, strict_intent=strict_intent)
        if cached is not None:
            return parse_result.unit, cached.diagnostics, True
    check_result = check_program_result(parse_result.unit, source_path=source_path, strict_intent=strict_intent)
    diagnostics = [*parse_result.diagnostics, *check_result.diagnostics]
    write_check_cache(
        source_path,
        source,
        diagnostics,
        dependency_paths=check_result.dependency_paths,
        missing_dependency_paths=check_result.missing_dependency_paths,
        strict_intent=strict_intent,
    )
    return parse_result.unit, diagnostics, False


def format_file(source_path: Path, *, check_only: bool) -> int:
    source = source_path.read_text(encoding="utf-8")
    if contains_line_comment(source):
        print(
            f"{source_path}: cannot format files with // comments without dropping comments",
            file=sys.stderr,
        )
        return 1
    formatted = format_unit(parse_source(source, path=str(source_path)))
    if check_only:
        if formatted != source:
            print(f"{source_path}: needs formatting", file=sys.stderr)
            return 1
        print("ok")
        return 0
    source_path.write_text(formatted, encoding="utf-8")
    print(f"formatted {source_path}")
    return 0


def contains_line_comment(source: str) -> bool:
    return contains_line_comment_source(source)


def doctor_report(
    unit: Unit,
    diagnostics: list[Diagnostic],
    source_path: Path,
    *,
    cache_hit: bool,
    db_path: Path | None = None,
) -> str:
    lines = ["SymbolicLight doctor"]
    lines.append(f"- source: {source_path}")
    lines.append(f"- unit: {'app' if isinstance(unit, App) else 'module'} {unit.name}")
    lines.append(f"- diagnostics: {len(diagnostics)}")
    lines.append(f"- check cache: {'hit' if cache_hit else 'miss'}")
    lines.append("- source map: generated by default during build")
    if isinstance(unit, App):
        lines.append(f"- intents: {len(unit.intents)}")
        lines.append(f"- imports: {len(unit.imports)}")
        lines.append(f"- stores: {len(unit.stores)}")
        lines.append(f"- commands: {len([fn for fn in unit.functions if fn.kind == 'command'])}")
        lines.append(f"- routes: {len(unit.routes)}")
        routes_with_body = len([route for route in unit.routes if route.body_type is not None])
        untyped_mutating = [
            route for route in unit.routes
            if route.method in {"POST", "PUT", "PATCH"} and route.body_type is None
        ]
        lines.append(f"- route schemas: {routes_with_body}/{len(unit.routes)} request bodies typed")
        if untyped_mutating:
            rendered = ", ".join(f"{route.method} {route.path}" for route in untyped_mutating)
            lines.append(f"- route body warning: missing typed body for {rendered}")
        if db_path is None:
            lines.append("- schema drift: checked by generated Python at startup")
        else:
            lines.extend(schema_drift_lines(unit, db_path))
        if any(test.external_ref == "intent.acceptance" for test in unit.tests):
            lines.append("- intent acceptance: declared")
        elif unit.intents:
            lines.append("- intent acceptance: not declared")
        if unit.permissions_from:
            lines.append("- permissions: imported from intent")
        elif unit.intents:
            lines.append("- permissions: not imported")
        for intent_path in unit.intents:
            contract_path = (source_path.parent / intent_path).resolve()
            if contract_path.exists():
                lines.extend(intent_doctor_lines(unit, load_intent_contract(contract_path)))
            else:
                lines.append(f"- intent contract: missing {intent_path}")
    else:
        lines.append(f"- imports: {len(unit.imports)}")
        lines.append(f"- types: {len(unit.types)}")
        lines.append(f"- enums: {len(unit.enums)}")
    return "\n".join(lines)


def schema_drift_lines(app: App, db_path: Path) -> list[str]:
    if not db_path.exists():
        return [f"- schema drift: not initialized ({db_path})"]
    try:
        database = sqlite3.connect(db_path)
        database.row_factory = sqlite3.Row
        try:
            table = database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sl_migrations'"
            ).fetchone()
            if table is None:
                return [f"- schema drift: not initialized ({db_path})"]
            row = database.execute(
                "SELECT schema_hash FROM sl_migrations WHERE version = ?",
                [1],
            ).fetchone()
            if row is None:
                return [f"- schema drift: not initialized ({db_path})"]
            expected = generate_schema_hash(app)
            actual = str(row["schema_hash"])
            if actual == expected:
                return [f"- schema drift: up to date ({db_path})"]
            return [
                f"- schema drift: drift detected ({db_path})",
                *schema_diff_lines(app, database),
                "- schema drift suggestion: back up the database, export data, then rebuild or migrate the schema manually.",
            ]
        finally:
            database.close()
    except sqlite3.Error as exc:
        return [
            f"- schema drift: unable to inspect ({db_path})",
            f"- schema drift error: {exc}",
        ]


def schema_diff_lines(app: App, database: sqlite3.Connection) -> list[str]:
    expected_tables = {
        store.name: expected_columns_for_store(app, store.type_ref)
        for store in app.stores
    }
    actual_tables = actual_schema(database)
    ignored_tables = {"sl_migrations", "sqlite_sequence"}
    lines: list[str] = []
    for table_name in sorted(expected_tables):
        expected_columns = expected_tables[table_name]
        actual_columns = actual_tables.get(table_name)
        if actual_columns is None:
            lines.append(f"- schema diff: missing table {table_name}")
            continue
        for column_name in sorted(expected_columns):
            expected_type = expected_columns[column_name]
            actual_type = actual_columns.get(column_name)
            if actual_type is None:
                lines.append(f"- schema diff: missing column {table_name}.{column_name}")
            elif normalize_sqlite_type(actual_type) != normalize_sqlite_type(expected_type):
                lines.append(
                    f"- schema diff: type mismatch {table_name}.{column_name} expected {expected_type} found {actual_type}"
                )
        for column_name in sorted(set(actual_columns) - set(expected_columns)):
            lines.append(f"- schema diff: extra column {table_name}.{column_name}")
    for table_name in sorted(set(actual_tables) - set(expected_tables) - ignored_tables):
        lines.append(f"- schema diff: extra table {table_name}")
    if not lines:
        lines.append("- schema diff: no structural difference detected")
    return lines


def expected_columns_for_store(app: App, type_ref: TypeRef) -> dict[str, str]:
    type_decl = next((decl for decl in app.types if decl.name == type_ref.name), None)
    if type_decl is None:
        return {}
    columns: dict[str, str] = {}
    for field in type_decl.fields:
        columns[field.name] = "INTEGER" if field.name == "id" else sqlite_type_for_doctor(field.type_ref)
    return columns


def actual_schema(database: sqlite3.Connection) -> dict[str, dict[str, str]]:
    rows = database.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    schema: dict[str, dict[str, str]] = {}
    for row in rows:
        table_name = str(row["name"])
        pragma_rows = database.execute(f"PRAGMA table_info({sqlite_identifier(table_name)})").fetchall()
        schema[table_name] = {str(column["name"]): str(column["type"]) for column in pragma_rows}
    return schema


def sqlite_type_for_doctor(type_ref: TypeRef) -> str:
    if type_ref.name == "Option" and type_ref.args:
        return sqlite_type_for_doctor(type_ref.args[0])
    if type_ref.name in {"Bool", "Int", "Id"}:
        return "INTEGER"
    if type_ref.name == "Float":
        return "REAL"
    return "TEXT"


def normalize_sqlite_type(type_name: str) -> str:
    normalized = type_name.upper().strip()
    if "INT" in normalized:
        return "INTEGER"
    if any(token in normalized for token in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return normalized or "TEXT"


def sqlite_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def intent_doctor_lines(app: App, contract: IntentContract) -> list[str]:
    lines = [f"- intent contract: {contract.path.name}"]
    app_routes, intent_routes, missing, extra = route_alignment(app, contract)
    if contract.routes:
        lines.append(f"- intent routes: {len(app_routes & intent_routes)}/{len(intent_routes)} matched")
        if missing:
            lines.append("- intent missing routes: " + ", ".join(f"{method} {path}" for method, path in missing))
        if extra:
            lines.append("- intent extra routes: " + ", ".join(f"{method} {path}" for method, path in extra))
    elif app.routes:
        lines.append("- intent routes: not declared")
    app_commands, intent_commands, missing_commands, extra_commands = command_alignment(app, contract)
    if contract.commands:
        lines.append(f"- intent commands: {len(app_commands & intent_commands)}/{len(intent_commands)} matched")
        if missing_commands:
            lines.append("- intent missing commands: " + ", ".join(missing_commands))
        if extra_commands:
            lines.append("- intent extra commands: " + ", ".join(extra_commands))
    elif app_commands:
        lines.append("- intent commands: not declared")
    lines.extend(permission_doctor_lines(app, contract))
    if contract.acceptance_tests:
        lines.append(f"- intent acceptance tests: {len(contract.acceptance_tests)} declared")
    else:
        lines.append("- intent acceptance tests: not declared")
    if app.intents and not any(test.external_ref == "intent.acceptance" for test in app.tests):
        lines.append("- intent acceptance gap: `test from intent.acceptance` not declared")
    elif app.intents and not contract.acceptance_tests:
        lines.append("- intent acceptance gap: contract has no tests")
    return lines


def route_alignment(app: App, contract: IntentContract) -> tuple[set[tuple[str, str]], set[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    app_routes = {(route.method, route.path) for route in app.routes}
    intent_routes = {(route.method, route.path) for route in contract.routes}
    return app_routes, intent_routes, sorted(intent_routes - app_routes), sorted(app_routes - intent_routes)


def command_alignment(app: App, contract: IntentContract) -> tuple[set[str], set[str], list[str], list[str]]:
    app_commands = {function.name for function in app.functions if function.kind == "command"}
    intent_commands = set(contract.commands)
    return app_commands, intent_commands, sorted(intent_commands - app_commands), sorted(app_commands - intent_commands)


def permission_doctor_lines(app: App, contract: IntentContract) -> list[str]:
    lines: list[str] = []
    lines.extend(f"- {line}" for line in permission_mismatch_lines(app, contract))
    if contract.permissions.network is False:
        lines.append("- permission network: ok")
    return lines


def permission_mismatch_lines(app: App, contract: IntentContract) -> list[str]:
    lines: list[str] = []
    uses_web = bool(app.routes)
    uses_filesystem_read = app_uses_call(app, "read_text")
    uses_filesystem_write = bool(app.stores) or app_uses_call(app, "write_text")
    if contract.permissions.web is False and uses_web:
        lines.append("permission mismatch: IntentSpec permissions.web is false but app declares routes")
    if contract.permissions.filesystem_read is False and uses_filesystem_read:
        lines.append("permission mismatch: IntentSpec filesystem.read is false but app reads files")
    if contract.permissions.filesystem_write is False and uses_filesystem_write:
        lines.append("permission mismatch: IntentSpec filesystem.write is false but app writes local state")
    return lines


def run_intent_acceptance(app: App, source_path: Path) -> int:
    if not any(test.external_ref == "intent.acceptance" for test in app.tests):
        return 0
    failures: list[str] = []
    warnings: list[str] = []
    checked = 0
    for intent_path in app.intents:
        contract_path = (source_path.parent / intent_path).resolve()
        if not contract_path.exists():
            failures.append(f"intent acceptance failed: missing contract {intent_path}")
            continue
        contract = load_intent_contract(contract_path)
        _, _, missing_routes, extra_routes = route_alignment(app, contract)
        _, _, missing_commands, extra_commands = command_alignment(app, contract)
        failures.extend(f"intent acceptance failed: missing route {method} {path}" for method, path in missing_routes)
        failures.extend(f"intent acceptance failed: missing command {name}" for name in missing_commands)
        warnings.extend(f"intent acceptance warning: extra route {method} {path}" for method, path in extra_routes)
        warnings.extend(f"intent acceptance warning: extra command {name}" for name in extra_commands)
        failures.extend(f"intent acceptance failed: {line}" for line in permission_mismatch_lines(app, contract))
        if not contract.acceptance_tests:
            failures.append(f"intent acceptance failed: {contract.path.name} declares no acceptance tests")
            continue
        for test in contract.acceptance_tests:
            if not test.assert_types:
                warnings.append(f"intent acceptance warning: `{test.name}` has no assertions")
            for assert_type in test.assert_types:
                checked += 1
                if assert_type == "required_sections":
                    if not contract.output_sections:
                        failures.append(
                            f"intent acceptance failed: `{test.name}` requires output.sections"
                        )
                    continue
                failures.append(
                    f"intent acceptance failed: unsupported assertion `{assert_type}` in `{test.name}`"
                )
    for warning in warnings:
        print(warning)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"ok - intent acceptance: {checked} assertion(s) checked")
    return 0


def app_uses_call(app: App, name: str) -> bool:
    return name in app_source_call_names(app)


def app_source_call_names(app: App) -> set[str]:
    names: set[str] = set()
    for function in app.functions:
        for statement in function.body:
            collect_call_names_from_stmt(statement, names)
    for route in app.routes:
        for statement in route.body:
            collect_call_names_from_stmt(statement, names)
    for test in app.tests:
        for statement in test.body:
            collect_call_names_from_stmt(statement, names)
    for config in app.configs:
        for field in config.fields:
            collect_call_names_from_expr(field.default, names)
    return names


def collect_call_names_from_stmt(statement, names: set[str]) -> None:
    for attr in ("expr", "condition"):
        expr = getattr(statement, attr, None)
        if expr is not None:
            collect_call_names_from_expr(expr, names)
    for body_attr in ("then_body", "else_body"):
        for nested in getattr(statement, body_attr, []) or []:
            collect_call_names_from_stmt(nested, names)


def collect_call_names_from_expr(expr, names: set[str]) -> None:
    callee = getattr(expr, "callee", None)
    if callee:
        names.add(".".join(callee))
        names.add(callee[-1])
    for attr in ("left", "right"):
        nested = getattr(expr, attr, None)
        if nested is not None:
            collect_call_names_from_expr(nested, names)
    for item in getattr(expr, "items", []) or []:
        collect_call_names_from_expr(item, names)
    for arg in getattr(expr, "args", []) or []:
        collect_call_names_from_expr(arg.expr, names)
    for field in getattr(expr, "fields", []) or []:
        collect_call_names_from_expr(field.expr, names)


def init_project(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    app_name = directory.name.replace("-", "_").replace(" ", "_").title().replace("_", "")
    source_dir = directory / "src"
    intent_dir = directory / "intent"
    source_dir.mkdir(exist_ok=True)
    intent_dir.mkdir(exist_ok=True)
    source = source_dir / "app.sl"
    intent = intent_dir / "app.intent.yaml"
    readme = directory / "README.md"
    gitignore = directory / ".gitignore"
    write_new_file(source, sample_app(app_name, "../intent/app.intent.yaml"))
    write_new_file(intent, sample_intent(app_name))
    write_new_file(readme, f"# {app_name}\n\nRun `slc check src/app.sl`.\n")
    write_new_file(gitignore, ".slcache/\nbuild/\n*.sqlite\n__pycache__/\n")


def new_api_project(name: str, directory: Path) -> None:
    app_name = name.replace("-", "_").replace(" ", "_").title().replace("_", "")
    project = directory / name
    project.mkdir(parents=True, exist_ok=True)
    source_dir = project / "src"
    intent_dir = project / "intent"
    source_dir.mkdir(exist_ok=True)
    intent_dir.mkdir(exist_ok=True)
    source = source_dir / "app.sl"
    intent = intent_dir / f"{name}.intent.yaml"
    readme = project / "README.md"
    gitignore = project / ".gitignore"
    write_new_file(source, sample_app(app_name, f"../intent/{name}.intent.yaml"))
    write_new_file(intent, sample_intent(app_name))
    write_new_file(readme, f"# {app_name}\n\nRun `slc check src/app.sl`.\n")
    write_new_file(gitignore, ".slcache/\nbuild/\n*.sqlite\n__pycache__/\n")


def add_route_to_file(source_path: Path, method: str, route_path: str) -> None:
    source = source_path.read_text(encoding="utf-8")
    if contains_line_comment(source):
        raise OSError(f"Refusing to edit {source_path}: // comments require comment-preserving edits.")
    parse_result = parse_source_result(source, path=str(source_path))
    if parse_result.unit is None or any(diagnostic.severity == "error" for diagnostic in parse_result.diagnostics):
        raise OSError(f"Refusing to edit {source_path}: fix parse errors before adding a route.")
    if not isinstance(parse_result.unit, App):
        raise OSError(f"Refusing to edit {source_path}: routes can only be added to app files.")
    method = method.upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise OSError("Unsupported route method. Use GET, POST, PUT, PATCH, or DELETE.")
    insertion = (
        f'\n  route {method} "{route_path}" -> Text {{\n'
        '    return ""\n'
        "  }\n"
    )
    index = source.rfind("}")
    if index == -1:
        raise OSError(f"Cannot find closing app brace in {source_path}")
    source_path.write_text(source[:index] + insertion + source[index:], encoding="utf-8")


def discover_source(directory: Path) -> Path:
    sources = sorted(directory.glob("*.sl"))
    if len(sources) != 1:
        raise OSError("Pass a source file when the current directory does not contain exactly one .sl file.")
    return sources[0]


def sample_app(app_name: str, intent_path: str) -> str:
    return f'''app {app_name} {{
  intent "{intent_path}"

  type Item = {{
    id: Id<Item>,
    title: Text,
    done: Bool,
  }}

  store items: Item

  command add(title: Text) -> Item {{
    return items.insert({{ title: title, done: false }})
  }}

  route GET "/items" -> List<Item> {{
    return items.all()
  }}

  test "add creates item" {{
    let item = add("Example")
    assert item.done == false
  }}
}}
'''


def sample_intent(app_name: str) -> str:
    return f"""version: "0.1"
kind: "IntentSpec"

metadata:
  name: "{app_name.lower()}"
  title: "{app_name}"
  owner: "symboliclight"

task:
  goal: "Build a generated SymbolicLight API skeleton."
  audience:
    - "Application developer"
  priority: "medium"

permissions:
  web: false
  filesystem:
    read: true
    write: true
  network: false
  tools:
    create_file: true
    delete_file: false
    send_email: false
    purchase: false

constraints:
  - "Use local SQLite storage only."

output:
  format: "markdown"
  language: "en"
  max_words: 500
  sections:
    - "Build"
    - "Run"
    - "Test"

tests:
  - name: "Generated app smoke test"
    assert:
      - type: "required_sections"
"""


def write_new_file(path: Path, content: str) -> None:
    if path.exists():
        raise OSError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def print_diagnostics(diagnostics: list[Diagnostic], *, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps([diagnostic.to_dict() for diagnostic in diagnostics], indent=2))
        return
    for diagnostic in diagnostics:
        stream = sys.stderr if diagnostic.severity == "error" else sys.stdout
        print(diagnostic.format(), file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
