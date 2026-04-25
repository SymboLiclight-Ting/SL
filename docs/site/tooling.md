# Tooling

Core commands:

```bash
slc check <file.sl>
slc build <file.sl> --out build/app.py
slc run <file.sl> -- <args>
slc test <file.sl>
slc fmt <file.sl>
slc schema <file.sl> --out build/schema.json
slc doctor <file.sl>
slc doctor <file.sl> --json
slc migrate plan <file.sl> --db path-or-url
slc migrate plan <file.sl> --db path-or-url --json
slc lsp
slc new api <name> --template todo --backend sqlite
```

The formatter preserves common `//` comment trivia in v0.9.

The language server provides diagnostics, hover, definition, document symbols, and formatting through JSON-RPC stdio.

The VS Code preview extension lives under `editors/vscode/`.

Maintenance scripts:

```bash
python scripts/docs_check.py
python scripts/vscode_check.py
python scripts/compat_check.py
python scripts/release_check.py --fast
python scripts/cross_platform_smoke.py
python scripts/package_smoke.py --gallery --python path/to/python
python scripts/release_notes.py --to HEAD --out build/release-notes.md
```

v0.12 CI runs the main gate on Windows, macOS, and Linux with Python 3.11 and 3.12. Local smoke scripts mirror that checklist as closely as possible without requiring multiple operating systems on one machine.

`slc` uses stable exit codes in v0.12: `0` for success or warnings, `1` for compiler/runtime/test/doctor/migrate failures, and `2` for CLI argument errors from `argparse`.
