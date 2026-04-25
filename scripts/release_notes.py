from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local SL release notes.")
    parser.add_argument("--from", dest="from_ref", default="v0.12.0-rc1")
    parser.add_argument("--to", dest="to_ref", default="HEAD")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    notes = render_release_notes(args.from_ref, args.to_ref)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(notes, encoding="utf-8")
    print(f"wrote {output}")
    return 0


def render_release_notes(from_ref: str, to_ref: str) -> str:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    commits = subprocess.check_output(
        ["git", "log", "--oneline", f"{from_ref}..{to_ref}"],
        cwd=ROOT,
        text=True,
    ).strip()
    version_block = current_changelog_entry(changelog)
    lines = [
        "# SymbolicLight Release Notes Draft",
        "",
        "## Changelog",
        "",
        "## " + version_block,
        "",
        "## Commits",
        "",
    ]
    if commits:
        lines.extend(f"- {line}" for line in commits.splitlines())
    else:
        lines.append("- No commits in range.")
    lines.append("")
    return "\n".join(lines)


def current_changelog_entry(changelog: str) -> str:
    if "## " not in changelog:
        return changelog.strip()
    entry = changelog.split("## ", 1)[1]
    return entry.split("\n## ", 1)[0].strip()


if __name__ == "__main__":
    raise SystemExit(main())
