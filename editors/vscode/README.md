# SL VS Code Support

This folder contains the local VS Code support for `.sl` files.

## Local Install

```bash
cd editors/vscode
npm install
code --extensionDevelopmentPath .
```

The extension starts the language server with:

```bash
slc lsp
```

Make sure `slc` is available on your `PATH`, for example by running `pip install -e ".[dev]"` from the repository root.
