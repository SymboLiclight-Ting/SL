# SL VS Code Support

The local VS Code extension lives in `editors/vscode`.

It provides:

- `.sl` file association,
- TextMate syntax highlighting,
- snippets for common SL declarations,
- LSP startup through `slc lsp`.

Local development:

```bash
cd editors/vscode
npm install
code --extensionDevelopmentPath .
```

Make sure `slc` is available on `PATH` before starting the extension host.
