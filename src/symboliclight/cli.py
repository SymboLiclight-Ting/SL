from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from symboliclight.ast import App, Unit
from symboliclight.cache import read_check_cache, write_check_cache
from symboliclight.checker import check_program_result
from symboliclight.codegen import generate_python, generate_python_artifact
from symboliclight.diagnostics import Diagnostic, SourceLocation, SymbolicLightError, raise_if_errors
from symboliclight.formatter import format_unit
from symboliclight.parser import parse_source, parse_source_result


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
            app, diagnostics, _ = load_checked_app(Path(args.source), strict_intent=False, use_cache=False)
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            with tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "app.py"
                output.write_text(generate_python(app), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(output), "test"],
                    check=False,
                )
                return completed.returncode
        if args.command == "fmt":
            return format_file(Path(args.source), check_only=args.check)
        if args.command == "doctor":
            unit, diagnostics, cache_hit = load_checked_unit(Path(args.source), strict_intent=args.strict_intent)
            print_diagnostics(diagnostics)
            print(doctor_report(unit, diagnostics, Path(args.source), cache_hit=cache_hit))
            return 1 if any(diagnostic.severity == "error" for diagnostic in diagnostics) else 0
        if args.command == "init":
            init_project(Path(args.directory))
            print(f"initialized {args.directory}")
            return 0
        if args.command == "new" and args.new_kind == "api":
            new_api_project(args.name, Path.cwd())
            print(f"created {args.name}.sl")
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
    in_string = False
    escaped = False
    for index, char in enumerate(source):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string and char == "/" and index + 1 < len(source) and source[index + 1] == "/":
            return True
    return False


def doctor_report(unit: Unit, diagnostics: list[Diagnostic], source_path: Path, *, cache_hit: bool) -> str:
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
        if any(test.external_ref == "intent.acceptance" for test in unit.tests):
            lines.append("- intent acceptance: declared")
        elif unit.intents:
            lines.append("- intent acceptance: not declared")
        if unit.permissions_from:
            lines.append("- permissions: imported from intent")
        elif unit.intents:
            lines.append("- permissions: not imported")
    else:
        lines.append(f"- imports: {len(unit.imports)}")
        lines.append(f"- types: {len(unit.types)}")
        lines.append(f"- enums: {len(unit.enums)}")
    return "\n".join(lines)


def init_project(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    app_name = directory.name.replace("-", "_").replace(" ", "_").title().replace("_", "")
    source = directory / "app.sl"
    intent = directory / "app.intent.yaml"
    readme = directory / "README.md"
    write_new_file(source, sample_app(app_name, "./app.intent.yaml"))
    write_new_file(intent, sample_intent(app_name))
    write_new_file(readme, f"# {app_name}\n\nRun `slc check app.sl`.\n")


def new_api_project(name: str, directory: Path) -> None:
    app_name = name.replace("-", "_").replace(" ", "_").title().replace("_", "")
    source = directory / f"{name}.sl"
    intent = directory / f"{name}.intent.yaml"
    write_new_file(source, sample_app(app_name, f"./{name}.intent.yaml"))
    write_new_file(intent, sample_intent(app_name))


def add_route_to_file(source_path: Path, method: str, route_path: str) -> None:
    source = source_path.read_text(encoding="utf-8")
    insertion = (
        f'\n  route {method.upper()} "{route_path}" -> Text {{\n'
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
