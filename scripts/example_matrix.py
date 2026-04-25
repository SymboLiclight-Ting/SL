from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "examples" / "gallery"
DOC_PATHS = [ROOT / "README.md", ROOT / "docs" / "site", ROOT / "examples" / "gallery"]

EXPECTED_GALLERY = {
    "todo-api-cli",
    "notes-api",
    "issue-tracker",
    "customer-brief-generator",
    "small-admin-backend",
    "project-ops-api",
}


def main() -> int:
    errors: list[str] = []
    check_gallery_shape(errors)
    check_documented_example_paths(errors)
    check_documented_slc_commands(errors)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("ok - example matrix check passed")
    return 0


def check_gallery_shape(errors: list[str]) -> None:
    actual = {path.name for path in GALLERY.iterdir() if path.is_dir()}
    missing = EXPECTED_GALLERY - actual
    extra = actual - EXPECTED_GALLERY
    for name in sorted(missing):
        errors.append(f"missing gallery example: {name}")
    for name in sorted(extra):
        errors.append(f"unexpected gallery example: {name}")
    for name in sorted(EXPECTED_GALLERY & actual):
        directory = GALLERY / name
        required = [directory / "app.sl", directory / "README.md"]
        for path in required:
            if not path.exists():
                errors.append(f"{relative(directory)} missing {path.name}")
        if not list(directory.glob("*.intent.yaml")):
            errors.append(f"{relative(directory)} missing IntentSpec yaml")
        if name == "project-ops-api" and not (directory / "app_postgres.sl").exists():
            errors.append("project-ops-api missing app_postgres.sl")


def check_documented_example_paths(errors: list[str]) -> None:
    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in re.findall(r"examples/[A-Za-z0-9_./-]+", text):
            candidate = (ROOT / match.rstrip("`.,)")).resolve()
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                errors.append(f"{relative(path)} references path outside repo: {match}")
                continue
            if not candidate.exists():
                errors.append(f"{relative(path)} references missing example path: {match}")


def check_documented_slc_commands(errors: list[str]) -> None:
    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("slc "):
                continue
            if "examples/" in stripped:
                for match in re.findall(r"examples/[A-Za-z0-9_./-]+", stripped):
                    candidate = ROOT / match.rstrip("`.,)")
                    if not candidate.exists():
                        errors.append(f"{relative(path)} command references missing path: {match}")


def iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for root in DOC_PATHS:
        if root.is_file() and root.suffix == ".md":
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.glob("*.md")))
    return files


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
