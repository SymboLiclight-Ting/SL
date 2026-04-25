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
python scripts/release_notes.py --from v0.10.0-rc1 --to HEAD --out build/release-notes.md
```
