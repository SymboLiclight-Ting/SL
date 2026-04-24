# SymbolicLight v0.2 Semantics

SymbolicLight v0.2 is an application language that compiles to Python.

## Unit Boundary

Each source file is either an `app` or a `module`.

- `app` files are executable.
- `module` files are reusable declaration units.
- imports are explicit and aliased.
- no declaration leaks into another file without `import`.

## Type Boundary

Records and enums define the stable application data surface.

`Option<T>` represents nullable or absent values. SQLite stores encode absent optional fields as `NULL`.

`Result<T, E>` is reserved for explicit error-returning APIs. The parser and checker accept it in v0.2; broader control-flow helpers are planned for later releases.

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

`insert` and `update` require record literals in v0.2. The checker validates unknown fields, missing required fields, and obvious field type mismatches.

`get`, `update`, and `delete` require an `Int` or `Id<T>` id argument.

`filter` requires named arguments and validates field value types.

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

These comments are the v0.2 source-map seed. Later releases should use them to improve Python exception backreferences.

## Formatting Boundary

The v0.2 formatter is the official style source for comment-free `.sl` files.

Files containing `//` comments are not rewritten in v0.2. The formatter exits with an error instead of deleting comments, because comment-preserving formatting requires lexer trivia support.
