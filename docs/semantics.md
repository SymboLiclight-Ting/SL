# SymbolicLight v0.6 Semantics

SymbolicLight v0.6 is an application language that compiles to Python.

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

`Response<T>` represents a JSON HTTP response wrapper. In v0.4 it carries status, optional headers, and body only.

## Function Boundary

`fn` is pure application logic. The checker rejects store access inside `fn`. Pure functions declared in imported modules may be called through their import alias and are emitted into generated Python.

`command` is a CLI boundary. Commands may call pure functions and store methods.

`route` is an HTTP boundary. Routes may call pure functions and store methods, but may not call commands directly.

`test` blocks may call commands so tests can exercise the public CLI-shaped application behavior.

## Store Semantics

`store items: Item` creates a SQLite-backed table for the record type.

Supported store methods:

- `insert(record) -> Item`
- `all() -> List<Item>`
- `get(id) -> Option<Item>`
- `update(id, record) -> Item`
- `delete(id) -> Bool`
- `filter(field: value) -> List<Item>`

`insert` and `update` require record literals in v0.4. The checker validates unknown fields, duplicate fields, missing required fields, and obvious field type mismatches.

`get`, `update`, and `delete` require an `Int` or `Id<T>` id argument.

`filter` requires named arguments and validates field value types.

`count()` returns the number of rows in a store. `exists(id)` checks whether an item exists. `clear()` deletes all rows and is allowed only in `test` blocks.

Generated Python records a schema hash in `sl_migrations`. If the stored hash differs from the generated hash, startup prints a schema drift warning. v0.4 does not automatically migrate data.

## Request Body Semantics

Routes may declare `body TypeName` for typed JSON request bodies. `GET` and `DELETE` routes may not declare a body in v0.4.

When a route has a body type, `request.body.field` is checked against that record type. Generated Python returns `400` for malformed JSON and for missing required non-optional body fields.

Routes without a declared body keep the v0.3 compatibility behavior where `request.body.field` is treated as `Text`.

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

`read_text` is allowed from commands, routes, and tests. `write_text` is allowed only from commands and tests.

## Enum Semantics

Enum values compile to stable text values in generated Python and SQLite.

Local enum variants use `Status.open`. Imported enum variants use `models.Status.open`.

## Intent Boundary

`intent "./file.intent.yaml"` links the implementation to an IntentSpec contract.

`permissions from intent.permissions` and `test from intent.acceptance` are declarative hooks. `slc doctor` reports whether they are present. Full offline acceptance execution remains an integration target.

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

The v0.5 formatter is the official style source for comment-free `.sl` files.

Files containing `//` comments are not rewritten in v0.5. The formatter exits with an error instead of deleting comments, because comment-preserving formatting requires lexer trivia support.

## Developer Preview Tooling

`slc lsp` exposes compiler diagnostics and basic source navigation through JSON-RPC over stdio. The LSP does not change language semantics; it reuses the parser, checker, and formatter.

The local playground compiles submitted `.sl` source to Python or diagnostics JSON. It is a preview tool and not a production runtime.

## IntentSpec Doctor Hints

`slc doctor` may read SL-specific hints from IntentSpec comments:

```yaml
# sl: route GET /items
# sl: command add
```

The comments are intentionally outside the IntentSpec schema. They let SL compare implementation routes and commands without making IntentSpec validation fail in stricter environments.
