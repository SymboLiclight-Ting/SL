from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from symboliclight.ast import App, Unit
from symboliclight.cache import write_check_cache
from symboliclight.checker import check_program
from symboliclight.codegen import generate_python
from symboliclight.diagnostics import Diagnostic, SourceLocation, SymbolicLightError, raise_if_errors
from symboliclight.formatter import format_unit
from symboliclight.parser import parse_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slc")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check")
    check_parser.add_argument("source")
    check_parser.add_argument("--strict-intent", action="store_true")

    build_parser = sub.add_parser("build")
    build_parser.add_argument("source")
    build_parser.add_argument("--out", required=True)
    build_parser.add_argument("--strict-intent", action="store_true")

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
            _, diagnostics = load_checked_unit(Path(args.source), strict_intent=args.strict_intent)
            print_diagnostics(diagnostics)
            if any(diagnostic.severity == "error" for diagnostic in diagnostics):
                return 1
            print("ok")
            return 0
        if args.command == "build":
            app, diagnostics = load_checked_app(Path(args.source), strict_intent=args.strict_intent)
            print_diagnostics(diagnostics)
            raise_if_errors(diagnostics)
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(generate_python(app), encoding="utf-8")
            print(f"wrote {output}")
            return 0
        if args.command == "run":
            app, diagnostics = load_checked_app(Path(args.source), strict_intent=False)
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
            app, diagnostics = load_checked_app(Path(args.source), strict_intent=False)
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
            unit, diagnostics = load_checked_unit(Path(args.source), strict_intent=args.strict_intent)
            print_diagnostics(diagnostics)
            print(doctor_report(unit, diagnostics, Path(args.source)))
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
        print_diagnostics(exc.diagnostics)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


def load_checked_app(source_path: Path, *, strict_intent: bool) -> tuple[App, list[Diagnostic]]:
    unit, diagnostics = load_checked_unit(source_path, strict_intent=strict_intent)
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
    return unit, diagnostics


def load_checked_unit(source_path: Path, *, strict_intent: bool) -> tuple[Unit, list[Diagnostic]]:
    source = source_path.read_text(encoding="utf-8")
    unit = parse_source(source, path=str(source_path))
    diagnostics = check_program(unit, source_path=source_path, strict_intent=strict_intent)
    write_check_cache(source_path, source, diagnostics)
    return unit, diagnostics


def format_file(source_path: Path, *, check_only: bool) -> int:
    source = source_path.read_text(encoding="utf-8")
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


def doctor_report(unit: Unit, diagnostics: list[Diagnostic], source_path: Path) -> str:
    lines = ["SymbolicLight doctor"]
    lines.append(f"- source: {source_path}")
    lines.append(f"- unit: {'app' if isinstance(unit, App) else 'module'} {unit.name}")
    lines.append(f"- diagnostics: {len(diagnostics)}")
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


def print_diagnostics(diagnostics: list[Diagnostic]) -> None:
    for diagnostic in diagnostics:
        stream = sys.stderr if diagnostic.severity == "error" else sys.stdout
        print(diagnostic.format(), file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
