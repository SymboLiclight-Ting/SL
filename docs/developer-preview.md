# SL Developer Preview

SL v0.10 is a public developer preview. It is usable for experiments, examples, and early feedback, but v0.x remains compatibility-flexible until v1.0.

## What Is Ready

- Compile `.sl` apps to readable Python 3.11.
- Build small CLI and JSON HTTP applications.
- Use SQLite stores, optional Postgres stores, typed routes, fixtures, golden tests, and JSON schema generation.
- Run `slc lsp` for editor diagnostics and basic navigation.
- Try the local VS Code preview extension and playground.
- Run `slc doctor` to compare SL route and command hints against implementation.
- Run `slc migrate plan` for read-only database structure planning.

## What Is Not Stable Yet

- Syntax and standard library APIs may still change before v1.0.
- VS Code support is local-preview only and is not published to the marketplace.
- The playground is local-only and not a hosted product.
- Postgres support requires optional dependencies and remains preview quality.

## Recommended Smoke Test

```bash
pytest -q
slc check examples/notes_api.sl
slc build examples/notes_api.sl --out build/notes_api.py
python -m py_compile build/notes_api.py
python build/notes_api.py test
python scripts/release_check.py --skip-package
```
