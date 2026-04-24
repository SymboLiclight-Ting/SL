from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the built SL wheel and run smoke checks.")
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args(argv)
    wheel = args.wheel or latest_wheel()
    if wheel is None:
        print("error: no wheel found in dist; run `python -m build` first", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        venv_dir = temp / "venv"
        app = temp / "smoke.sl"
        built = temp / "smoke.py"
        app.write_text(SMOKE_SOURCE, encoding="utf-8")
        run([sys.executable, "-m", "venv", str(venv_dir)])
        python = venv_python(venv_dir)
        run([str(python), "-m", "pip", "install", "--force-reinstall", "--no-index", str(wheel)], isolated=True)
        run([str(python), "-m", "symboliclight.cli", "check", str(app)], isolated=True)
        run([str(python), "-m", "symboliclight.cli", "build", str(app), "--out", str(built)], isolated=True)
        run([str(python), "-m", "py_compile", str(built)], isolated=True)
        run([str(python), str(built), "test"], isolated=True)
        run([str(slc_command(venv_dir)), "--help"], isolated=True)
    print(f"ok - package smoke passed for {wheel.name}")
    return 0


def latest_wheel() -> Path | None:
    wheels = sorted((ROOT / "dist").glob("symboliclight-*.whl"), key=lambda path: path.stat().st_mtime)
    return wheels[-1] if wheels else None


def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def slc_command(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "slc.exe"
    return venv_dir / "bin" / "slc"


def run(command: list[str], *, isolated: bool = False) -> None:
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=isolated_env() if isolated else None, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def isolated_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


SMOKE_SOURCE = """
app PackageSmoke {
  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  command add(title: Text) -> Item {
    return items.insert({ title: title })
  }

  test "add" {
    let item = add("ok")
    assert item.title == "ok"
  }
}
""".lstrip()


if __name__ == "__main__":
    raise SystemExit(main())
