# SymbolicLight v0.10 Semantics

SymbolicLight v0.10 is an application language that compiles to Python.

## Unit Boundary

Each source file is either an `app` or a `module`.

- `app` files are executable.
- `module` files are reusable declaration units.
- imports are explicit and aliased.
- no declaration leaks into another file without `import`.
- import aliases must be unique and must not collide with local declarations.
- cyclic imports are rejected with an import-chain diagnostic.

## Type Boundary

Records and enums define the stable application data surface.

`Option<T>` represents nullable or absent values. SQLite stores encode absent optional fields as `NULL`. `some(value)` produces `Option<typeof value>` and `none()` can satisfy any `Option<T>` target.

`Result<T, E>` is reserved for explicit error-returning APIs. `ok(value)` produces `Result<typeof value, Unknown>` and `err(value)` produces `Result<Unknown, typeof value>`. Broader control-flow helpers are planned for later releases.

Named arguments are checked against declared function and command parameters. Unknown, duplicate, and missing arguments are rejected. Positional arguments may not follow named arguments.

`Response<T>` represents a JSON HTTP response wrapper. In v0.4 it carries status, optional headers, and body only. Inline record bodies are checked against the declared `T`; the same target-aware check applies through `ok(...)`, `err(...)`, and `some(...)` wrappers where the expected type is known.

## Function Boundary

`fn` is pure application logic. The checker rejects store access inside `fn`. Pure functions declared in imported modules may be called through their import alias and are emitted into generated Python.

`command` is a CLI boundary. Commands may call pure functions and store methods.

`route` is an HTTP boundary. Routes may call pure functions and store methods, but may not call commands directly.

Generated route handlers return a stable JSON error envelope for framework-level failures such as malformed JSON, missing typed body fields, oversized bodies, unsupported generated methods, and uncaught route exceptions. The envelope is `{"error": {"code": Text, "message": Text}}`. Route exceptions are logged to stderr with best-effort `.sl` source backreferences, but generated HTTP responses do not include Python tracebacks.

`test` blocks may call commands so tests can exercise the public CLI-shaped application behavior.

## Store Semantics

`store items: Item` creates a SQLite-backed table for the record type. `store items: Item using postgres` creates a Postgres-backed table and requires installing `symboliclight[postgres]` before running generated apps that connect to Postgres.

One app may use only one store backend in v0.10. This keeps generated connection lifecycle and migration planning explicit.

Supported store methods:

- `insert(record) -> Item`
- `all() -> List<Item>`
- `get(id) -> Option<Item>`
- `update(id, record) -> Item`
- `try_update(id, record) -> Option<Item>`
- `delete(id) -> Bool`
- `filter(field: value) -> List<Item>`

`insert` and `update` require record literals in v0.4. The checker validates unknown fields, duplicate fields, missing required fields, and obvious field type mismatches.

`get`, `update`, and `delete` require an `Int` or `Id<T>` id argument. `Id<T>` is preferred at command and request-body boundaries because it preserves the target store identity while still compiling to an integer in generated Python.

`update(id, record)` raises a runtime error if no row exists for the id. This keeps the declared return type `T` honest without introducing a breaking `Option<T>` return in v0.8.

`try_update(id, record)` has the same validation rules as `update`, but returns `none()` when no row exists for the id.

`filter` requires named arguments and validates field value types.

`count()` returns the number of rows in a store. `exists(id)` checks whether an item exists. `clear()` deletes all rows and is allowed only in `test` blocks.

Generated Python records a schema hash in `sl_migrations`. If the stored hash differs from the generated hash, startup prints a schema drift warning. v0.12 does not automatically migrate data and does not replace the stored hash on drift. A matching hash is metadata evidence only; it is not a substitute for structural inspection.

`slc doctor --db path-or-url` can inspect the same metadata without running the generated app. SQLite paths and Postgres URLs are supported. The report is read-only. It separates hash state from table structure: `schema drift: up to date` means the hash matches, `schema diff: no structural difference detected` means table structure matches, `schema drift: structural drift detected` means the hash matches but the actual schema differs, and `schema drift: drift detected` means the stored hash differs from the generated hash. Drift reports include summary schema differences and a manual migration suggestion; v0.10 never modifies application data.

`slc migrate plan <file.sl> --db path-or-url` uses the same schema model to emit a read-only migration plan. The plan is advisory. It does not generate destructive SQL and does not execute changes.

## Request Body Semantics

Routes may declare `body TypeName` for typed JSON request bodies. `GET` and `DELETE` routes may not declare a body in v0.4.

When a route has a body type, `request.body.field` is checked against that record type. Generated Python returns `400` for malformed JSON and for missing required non-optional body fields.

Routes without a declared body keep the v0.3 compatibility behavior where `request.body.field` is treated as `Text`.

## Request Header Semantics

Routes may call `request.header(name: Text) -> Option<Text>` to read an HTTP header. The helper is route-only and is checked as an explicit boundary operation. It returns `some(text)` when the header is present and `none()` when absent, represented as `Text` or `None` in generated Python.

v0.8 intentionally does not add auth middleware, cookies, sessions, password handling, or implicit authorization policy. Applications must keep token checks visible in route logic.

## Fixture And Golden Test Semantics

Fixtures are app-level store seeds. Each inline test runs with a fresh in-memory SQLite database and loads fixtures before executing test statements.

Golden tests compare a returned value with a file. If the value differs, generated Python writes an `.actual` file and fails the test with a path-aware message.

## Config And Thin Stdlib Semantics

Config declarations produce typed app config dictionaries. Defaults are checked against declared field types.

Thin standard-library built-ins are mapped to Python stdlib:

- `env` and `env_int` read environment variables,
- `uuid` uses Python `uuid4`,
- `now` uses UTC ISO timestamps,
- `read_text` and `write_text` use UTF-8 text files.

`read_text` is allowed from commands, routes, and tests. `write_text` is allowed only from commands and tests. The generated runtime rejects empty paths and directory paths before opening files. File-system failures are re-raised as runtime errors that include the failing builtin name, so command-line debugging remains explicit.

## Enum Semantics

Enum values compile to stable text values in generated Python and SQLite.

Local enum variants use `Status.open`. Imported enum variants use `models.Status.open`.

## Intent Boundary

`intent "./file.intent.yaml"` links the implementation to an IntentSpec contract.

`permissions from intent.permissions` imports the app's declared permission contract for diagnostics and acceptance checks.

`test from intent.acceptance` asks `slc test` to run the v0.6 offline acceptance bridge after generated app tests pass. The bridge checks:

- SL-specific IntentSpec hints such as `# sl: route GET /items` and `# sl: command add`,
- permission mismatches for routes, file reads, and local state writes,
- IntentSpec `required_sections` assertions against `output.sections`.

Generated Python cannot run IntentSpec acceptance by itself. Direct `python app.py test` treats external tests as skipped; `slc test` is the acceptance-aware entrypoint.

## Traceability

Generated Python includes source comments:

```python
# source: examples/todo_app.sl:12
```

`slc build` also writes a sidecar `.slmap.json` file by default. Generated tests and top-level app execution use an inline runtime map to print best-effort `SL source: file.sl:line:column` backreferences for Python exceptions.

## Incremental Checking

`slc check` caches diagnostics under `.slcache/`. A cache entry is valid only when the root source hash, imported module hashes, intent file hashes, missing dependency state, strict IntentSpec mode, and compiler cache version match. `--no-cache` forces a fresh parse and check.

## Diagnostics

Compiler diagnostics carry a stable shape for tools and AI repair loops:

- `severity`
- `code`
- `message`
- `file`
- `line`
- `column`
- `suggestion`

## Formatting Boundary

The v0.9 formatter is the official style source for `.sl` files.

Files containing `//` comments are rewritten only when comments can be preserved in stable trivia positions. v0.9 supports file header comments, comments before top-level items, comments before statements, and trailing comments. Formatting is intended to be idempotent.

## Developer Preview Tooling

`slc lsp` exposes compiler diagnostics and basic source navigation through JSON-RPC over stdio. The LSP does not change language semantics; it reuses the parser, checker, and formatter.

`slc doctor --json` is the machine-readable doctor interface. Its schema separates compiler diagnostics, IntentSpec alignment, schema drift, schema diff, cache status, and source-map status so external tools can consume the same checks without parsing human text output.

The local playground compiles submitted `.sl` source to Python or diagnostics JSON. It is a preview tool and not a production runtime.

## v0.13 Release Candidate Boundary

v0.13 is a compatibility and release-candidate phase. It does not add semantic constructs. The v0.13 work treats the existing route, store, response, diagnostics, doctor, migrate, and generated HTTP error behavior as a freeze candidate for v1.0.

If implementation hardening changes observable behavior, the change must be documented as a compatibility note and covered by a regression fixture before release.

## IntentSpec Doctor Hints

`slc doctor` may read SL-specific hints from IntentSpec comments:

```yaml
# sl: route GET /items
# sl: command add
```

The comments are intentionally outside the IntentSpec schema. They let SL compare implementation routes and commands without making IntentSpec validation fail in stricter environments.
