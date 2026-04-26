from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_SITE = ROOT / "docs" / "site"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    errors: list[str] = []
    if not DOCS_SITE.exists():
        errors.append("docs/site is missing")
    for path in sorted(DOCS_SITE.glob("*.md")):
        check_markdown_file(path, errors)
    for required in [
        "index.md",
        "quickstart.md",
        "tutorial.md",
        "language-tour.md",
        "app-kit.md",
        "database.md",
        "intentspec.md",
        "testing.md",
        "tooling.md",
        "error-handling.md",
        "ai-assisted-development.md",
        "roadmap.md",
    ]:
        if not (DOCS_SITE / required).exists():
            errors.append(f"missing docs/site/{required}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("ok - docs site check passed")
    return 0


def check_markdown_file(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count("```") % 2 != 0:
        errors.append(f"{relative(path)} has an unclosed fenced code block")
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        if is_external_or_anchor(target):
            continue
        target_path = (path.parent / target.split("#", 1)[0]).resolve()
        try:
            target_path.relative_to(ROOT)
        except ValueError:
            errors.append(f"{relative(path)} links outside repository: {target}")
            continue
        if not target_path.exists():
            errors.append(f"{relative(path)} has broken link: {target}")
    for example in re.findall(r"examples/[A-Za-z0-9_./-]+", text):
        example_path = (ROOT / example.rstrip("`.,)")).resolve()
        if not example_path.exists():
            errors.append(f"{relative(path)} references missing path: {example}")


def is_external_or_anchor(target: str) -> bool:
    return (
        target.startswith("#")
        or target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
    )


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
