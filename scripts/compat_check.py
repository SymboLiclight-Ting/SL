from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    apps = sorted((ROOT / "tests" / "compat").glob("v0_*/*/app.sl"))
    if not apps:
        print("error: no compat fixtures found", file=sys.stderr)
        return 1
    for source in apps:
        status = check_app(source)
        if status != 0:
            return status
    print(f"ok - compat check passed for {len(apps)} fixture(s)")
    return 0


def check_app(source: Path) -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / f"{source.parent.name}.py"
        commands = [
            [sys.executable, "-m", "symboliclight.cli", "check", str(source)],
            [sys.executable, "-m", "symboliclight.cli", "build", str(source), "--out", str(output)],
            [sys.executable, "-m", "py_compile", str(output)],
            [sys.executable, "-m", "symboliclight.cli", "test", str(source)],
        ]
        for command in commands:
            print("$ " + " ".join(command), flush=True)
            completed = subprocess.run(command, cwd=ROOT, env=release_env(), check=False)
            if completed.returncode != 0:
                return completed.returncode
        postgres_source = source.parent / "app_postgres.sl"
        if postgres_source.exists():
            postgres_output = Path(temp_dir) / f"{source.parent.name}-postgres.py"
            postgres_commands = [
                [sys.executable, "-m", "symboliclight.cli", "check", str(postgres_source)],
                [sys.executable, "-m", "symboliclight.cli", "build", str(postgres_source), "--out", str(postgres_output)],
                [sys.executable, "-m", "py_compile", str(postgres_output)],
                [
                    sys.executable,
                    "-m",
                    "symboliclight.cli",
                    "migrate",
                    "plan",
                    str(postgres_source),
                    "--db",
                    "postgresql://localhost/symboliclight",
                ],
            ]
            for command in postgres_commands:
                print("$ " + " ".join(command), flush=True)
                completed = subprocess.run(command, cwd=ROOT, env=release_env(), check=False)
                if completed.returncode != 0:
                    return completed.returncode
    return 0


def release_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else src
    return env


if __name__ == "__main__":
    raise SystemExit(main())
