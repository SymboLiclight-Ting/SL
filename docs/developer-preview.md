# SL Local v1.0 Baseline

SL v1.0 is the local stable baseline for the current compiler, app kit, CLI, and developer tooling. Public redistribution is a separate owner decision.

## What Is Ready

- Compile `.sl` apps to readable Python 3.11.
- Build small CLI and JSON HTTP applications.
- Use SQLite stores, optional Postgres stores, typed routes, fixtures, golden tests, and JSON schema generation.
- Run `slc lsp` for editor diagnostics and navigation.
- Try the local VS Code extension and playground.
- Run `slc doctor` to compare SL route and command hints against implementation.
- Run `slc migrate plan` for read-only database structure planning.
- Generate starter apps with `slc new api --template ... --backend ...`.
- Run local docs, VS Code, and release notes checks.

## What Is Not Part Of The v1.0 Guarantee

- VS Code support is local-only and is not published to the marketplace.
- The playground is local-only and not a hosted product.
- Postgres support requires optional dependencies.
- Generated Python internals may change when documented behavior remains stable.

## Recommended Smoke Test

```bash
pytest -q
slc check examples/notes_api.sl
slc build examples/notes_api.sl --out build/notes_api.py
python -m py_compile build/notes_api.py
python build/notes_api.py test
python scripts/freeze_check.py
python scripts/example_matrix.py
python scripts/release_check.py --skip-package
```
