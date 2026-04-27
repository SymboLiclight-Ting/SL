from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local SL release announcement draft.")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_announcement(args.version), encoding="utf-8")
    print(f"wrote {output}")
    return 0


def render_announcement(version: str) -> str:
    return "\n".join(
        [
            f"# SL {version} Announcement Draft",
            "",
            "SL is the developer-facing language name for the SymbolicLight project.",
            "",
            "This local v1.0 release baseline freezes the current application-focused surface for typed CLI and backend apps: models, stores, commands, JSON HTTP routes, tests, schema metadata, doctor reports, and migration planning.",
            "",
            "Generated Python remains the implementation target and ecosystem bridge. Public package uploads, public repository publication, hosted docs, production HTTP process management, automatic migrations, a package registry, macros, auth/session middleware, and native compiler work remain explicit future decisions.",
            "",
            "Local release artifacts:",
            "",
            "- `dist/symboliclight-1.0.0.tar.gz`",
            "- `dist/symboliclight-1.0.0-py3-none-any.whl`",
            "- `build/release-notes-v1.0.0.md`",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
