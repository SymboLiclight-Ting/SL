# SL Language Server

`slc lsp` starts the v0.5 developer-preview language server over JSON-RPC stdio.

Supported capabilities:

- diagnostics from parser and checker,
- hover for simple type information,
- go to definition for local declarations and imported module declarations,
- document symbols,
- whole-document formatting.

Formatting refuses files containing `//` comments because the formatter does not preserve comments yet.

The server is intentionally dependency-free and reuses the existing compiler modules.
