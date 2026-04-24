# SL Example Gallery

These examples are the v0.5 public-preview gallery. Each folder contains an SL source file, an IntentSpec file, and a short README.

Run any example from its folder:

```bash
slc check app.sl
slc build app.sl --out build/app.py
slc test app.sl
slc schema app.sl --out build/schema.json
slc doctor app.sl
```

## Examples

- `todo-api-cli`: Todo API + CLI smoke app.
- `notes-api`: typed route bodies, fixtures, golden tests, and schema generation.
- `issue-tracker`: explicit imports, enum status, filtering, and IntentSpec declarations.
