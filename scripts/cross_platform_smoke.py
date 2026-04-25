from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = [
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "-m", "compileall", "-q", "src", "playground", "scripts"],
        [sys.executable, "scripts/docs_check.py"],
        [sys.executable, "scripts/vscode_check.py"],
        [sys.executable, "scripts/release_check.py", "--skip-package"],
    ]
    print(f"SL cross-platform smoke using {sys.executable}")
    print(f"platform: {sys.platform}")
    for command in commands:
        print("$ " + " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=ROOT, env=release_env(), check=False)
        if completed.returncode != 0:
            return completed.returncode
    print("ok - cross-platform smoke passed")
    return 0


def release_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else src
    return env


if __name__ == "__main__":
    raise SystemExit(main())
