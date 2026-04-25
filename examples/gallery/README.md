# SL Example Gallery

These examples are the public-preview gallery. Each folder contains an SL source file, an IntentSpec file, and a short README.

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
- `customer-brief-generator`: command alignment, file input, and Markdown output.
- `small-admin-backend`: v0.8 real-app hardening for auth helper extraction, `ErrorBody`, schema diff checks, multiple stores, routes, and commands.

`ErrorBody` is the recommended gallery name for application errors, not a required built-in type name. Custom error record names are supported when they provide `code: Text` and `message: Text`.
