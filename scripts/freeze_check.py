from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_DOC = ROOT / "docs" / "freeze-candidate.md"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

REQUIRED_DOC_TERMS = [
    "top-level items",
    "type syntax",
    "store helpers",
    "route syntax",
    "Response/Result helpers",
    "CLI commands",
    "diagnostics JSON",
    "doctor JSON",
    "migrate plan JSON",
    "generated HTTP error envelope",
]

REQUIRED_CLI_COMMANDS = [
    "check",
    "build",
    "schema",
    "run",
    "test",
    "fmt",
    "doctor",
    "migrate",
    "lsp",
    "init",
    "new",
    "add",
]

REQUIRED_JSON_SURFACES = [
    '"severity"',
    '"code"',
    '"message"',
    '"file"',
    '"line"',
    '"column"',
    '"suggestion"',
    '"schema"',
    '"drift"',
    '"diff"',
]


def main() -> int:
    errors: list[str] = []
    if not FREEZE_DOC.exists():
        errors.append("docs/freeze-candidate.md is missing")
    else:
        text = FREEZE_DOC.read_text(encoding="utf-8")
        for term in REQUIRED_DOC_TERMS:
            if term not in text:
                errors.append(f"freeze doc missing required surface: {term}")
        for command in REQUIRED_CLI_COMMANDS:
            if f"`slc {command}" not in text and f"`{command}`" not in text:
                errors.append(f"freeze doc missing CLI command: {command}")
        for surface in REQUIRED_JSON_SURFACES:
            if surface not in text:
                errors.append(f"freeze doc missing JSON field: {surface}")

    pyproject = PYPROJECT.read_text(encoding="utf-8")
    if 'version = "0.13.0rc2"' not in pyproject:
        errors.append("pyproject.toml version must be 0.13.0rc2 for v0.13 RC")
    changelog = CHANGELOG.read_text(encoding="utf-8")
    if "## v0.13.0rc2" not in changelog:
        errors.append("CHANGELOG.md missing v0.13.0rc2 entry")

    release_process = (ROOT / "docs" / "release-process.md").read_text(encoding="utf-8")
    if "v0.13.0-rc2" not in release_process:
        errors.append("docs/release-process.md must mention v0.13.0-rc2")

    compatibility = (ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
    if "v0.13" not in compatibility:
        errors.append("docs/compatibility.md missing v0.13 compatibility notes")

    for path in sorted((ROOT / "tests" / "compat").glob("v0_12/*/app.sl")):
        if not re.match(r"^[a-z0-9_-]+$", path.parent.name):
            errors.append(f"compat fixture has unstable directory name: {path.parent.name}")

    if not list((ROOT / "tests" / "compat").glob("v0_12/*/app.sl")):
        errors.append("tests/compat/v0_12 has no app.sl fixtures")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("ok - freeze candidate check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
