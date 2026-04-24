import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_check", ROOT / "scripts" / "release_check.py")
assert SPEC is not None and SPEC.loader is not None
release_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_check)
release_commands = release_check.release_commands


def test_release_check_dry_run_includes_gallery_and_core_checks() -> None:
    commands = [" ".join(command) for command in release_commands(skip_package=True)]

    assert any("pytest -q" in command for command in commands)
    assert any("examples/gallery/customer-brief-generator/app.sl" in command for command in commands)
    assert any("symboliclight.cli doctor" in command for command in commands)
    assert not any(command.endswith(" -m build") for command in commands)
    assert not any("scripts/package_smoke.py" in command for command in commands)


def test_release_check_includes_package_smoke_when_not_skipped() -> None:
    commands = [" ".join(command) for command in release_commands(skip_package=False)]

    assert any(command.endswith(" -m build") for command in commands)
    assert any("scripts/package_smoke.py --gallery" in command for command in commands)
