# SymbolicLight v0.12 Security Review

This document records the v0.12 beta hardening review for generated Python apps and local tooling. It is not a formal third-party audit.

## Scope

- Generated Python HTTP server.
- Generated SQLite and Postgres store helpers.
- `read_text` and `write_text` built-ins.
- IntentSpec warnings and doctor output.
- Local packaging and release smoke scripts.

## HTTP Boundary

Generated HTTP handlers now enforce a fixed request body limit of `1_000_000` bytes. Oversized requests return:

```json
{
  "error": {
    "code": "payload_too_large",
    "message": "Request body exceeds the 1000000 byte limit."
  }
}
```

Malformed JSON, non-object JSON bodies, missing required body fields, unsupported generated methods, and uncaught route exceptions use the same `{"error": {"code": ..., "message": ...}}` envelope.

Uncaught route exceptions return `500` with `internal_error`. Tracebacks are printed to stderr for local debugging, but they are not included in the HTTP response body.

## File Built-ins

`read_text` and `write_text` reject empty paths and directory paths before opening files. The runtime does not implement a sandbox or permission model in v0.12. Applications should treat file access as an explicit boundary and keep file paths controlled by commands, tests, or validated route inputs.

## Database Boundary

SQLite and Postgres helpers use parameterized values for user data. Generated identifier names are quoted by the compiler. Store helper driver exceptions are wrapped with stable operation names such as `database items.insert failed`.

`slc doctor --db` and `slc migrate plan` are read-only. They inspect metadata and structure, but they do not modify `sl_migrations`, tables, columns, or data.

Postgres support remains optional through `symboliclight[postgres]`. If the dependency is missing, doctor and migration planning return actionable diagnostics instead of Python import tracebacks.

## IntentSpec Boundary

IntentSpec integration remains advisory unless strict flags or acceptance tests are explicitly used. Missing IntentSpec validation libraries are warnings by default. `slc doctor` highlights route, command, and permission mismatches, but it does not enforce deployment policy.

## Remaining Risks

- The generated HTTP server is based on Python `http.server` and is intended for local development and small app validation, not hardened internet-facing production hosting.
- There is no file-system sandbox in v0.12.
- There is no automatic database migration engine.
- Authentication remains explicit app code. SL does not provide middleware, sessions, cookies, password hashing, or token rotation in v0.12.
