from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the SL release smoke checks.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args(argv)
    commands = release_commands(skip_package=args.skip_package)
    for command in commands:
        print("$ " + " ".join(command), flush=True)
        if args.dry_run:
            continue
        completed = subprocess.run(command, cwd=ROOT, env=release_env(), check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def release_commands(*, skip_package: bool) -> list[list[str]]:
    python = sys.executable
    commands: list[list[str]] = [
        [python, "-m", "pytest", "-q"],
        [python, "-m", "compileall", "-q", "src", "playground", "scripts"],
        [python, "-m", "symboliclight.cli", "check", "--json", "examples/todo_app.sl"],
        [python, "-m", "symboliclight.cli", "test", "examples/todo_app.sl"],
        [python, "-m", "symboliclight.cli", "doctor", "examples/todo_app.sl"],
        [python, "-m", "symboliclight.cli", "test", "examples/issue_tracker.sl"],
        [python, "-m", "symboliclight.cli", "doctor", "examples/issue_tracker.sl"],
        [python, "-m", "symboliclight.cli", "build", "examples/notes_api.sl", "--out", "build/notes_api.py"],
        [python, "-m", "py_compile", "build/notes_api.py"],
        [python, "build/notes_api.py", "test"],
        [python, "-m", "symboliclight.cli", "doctor", "examples/notes_api.sl"],
        [python, "scripts/doctor_drift_smoke.py"],
        [python, "scripts/compat_check.py"],
    ]
    for source in [
        "examples/gallery/todo-api-cli/app.sl",
        "examples/gallery/notes-api/app.sl",
        "examples/gallery/issue-tracker/app.sl",
        "examples/gallery/customer-brief-generator/app.sl",
        "examples/gallery/small-admin-backend/app.sl",
    ]:
        stem = Path(source).parent.name
        commands.extend(
            [
                [python, "-m", "symboliclight.cli", "check", source],
                [python, "-m", "symboliclight.cli", "test", source],
                [python, "-m", "symboliclight.cli", "schema", source, "--out", f"build/{stem}_schema.json"],
                [python, "-m", "symboliclight.cli", "doctor", source],
            ]
        )
        if stem == "small-admin-backend":
            commands.append([python, "-m", "symboliclight.cli", "doctor", source, "--db", "build/small-admin-backend.sqlite"])
    if not skip_package:
        commands.append([python, "-m", "build"])
        commands.append([python, "scripts/package_smoke.py", "--gallery"])
    return commands


def release_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else src
    return env


if __name__ == "__main__":
    raise SystemExit(main())
