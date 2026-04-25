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
slc lsp
```

The formatter preserves common `//` comment trivia in v0.9.

The language server provides diagnostics, hover, definition, document symbols, and formatting through JSON-RPC stdio.

The VS Code preview extension lives under `editors/vscode/`.

