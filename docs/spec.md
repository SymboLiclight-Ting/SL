# SymbolicLight Language Specification v0.9

This document defines SymbolicLight v0.9 as a spec-native, AI-friendly application language that compiles to readable Python 3.11.

SymbolicLight is the formal project and brand name. Developer-facing language references should use SL. The compiler command is `slc`, and source files use the `.sl` extension.

## Source Units

Each `.sl` file contains exactly one top-level unit:

```sl
app Name { ... }
module name { ... }
```

An `app` is executable and can be built, run, tested, and served. A `module` is imported by an app or another module and may define shared records, enums, and pure `fn` logic.

## Keywords

```text
app module import as intent permissions from enum type config fn store fixture route body command test golden let return assert if else true false
```

## Imports

Imports are explicit and local to the current file:

```sl
import "./models.sl" as models
```

Imported declarations are referenced through the alias, for example `models.Issue`, `models.Status.open`, or `models.is_open(value)`. SymbolicLight has no implicit global sharing.

Import aliases must be unique in one source unit and must not collide with local `type`, `enum`, `fn`, `command`, or `store` declarations. Cyclic imports are rejected with an import-chain diagnostic.

## IntentSpec Declarations

Apps may declare an IntentSpec contract:

```sl
intent "./todo.intent.yaml"
permissions from intent.permissions
test from intent.acceptance
```

`slc check` validates the referenced intent file when the IntentSpec package is installed. Missing IntentSpec support is a warning unless `--strict-intent` is used.

When an app declares `test from intent.acceptance`, `slc test` runs a v0.6 offline acceptance bridge after generated app tests pass. The bridge reads the referenced IntentSpec file, checks SL route and command hints, checks permission mismatches, and supports the `required_sections` assertion against `output.sections`. Unsupported IntentSpec assertions fail with an explicit diagnostic.

## Types

Built-in scalar types:

```text
Bool Int Float Text
```

Built-in generic types:

```text
Id<T>
List<T>
Option<T>
Result<T, E>
Request<T>
Response<T>
```

Records:

```sl
type Todo = {
  id: Id<Todo>,
  title: Text,
  done: Bool,
}
```

Enums:

```sl
enum Status { open, closed }
```

Enum variants are referenced with `Status.open` or an imported path such as `models.Status.open`.

## App Items

### `store`

```sl
store todos: Todo
```

Stores are backed by SQLite in v0.4. Supported methods:

```text
todos.insert(record) -> Todo
todos.all() -> List<Todo>
todos.get(id) -> Option<Todo>
todos.update(id, record) -> Todo
todos.try_update(id, record) -> Option<Todo>
todos.delete(id) -> Bool
todos.filter(field: value) -> List<Todo>
todos.count() -> Int
todos.exists(id) -> Bool
todos.clear() -> Int
```

`insert` and `update` require record literals in v0.4. The checker validates unknown fields, duplicate fields, missing required fields, and obvious field type mismatches.

`get`, `update`, and `delete` require an `Int` or `Id<T>` id argument. `Id<T>` parameters at CLI boundaries are parsed as integers in generated Python. The checker accepts `Int` for compatibility but suggests `Id<T>` for named id values where it can preserve store identity.

`update(id, record)` returns `T` and raises a generated runtime error if the id does not exist.

`try_update(id, record)` returns `Option<T>` and produces `none()` when the id does not exist.

`filter` requires named arguments and validates each filter value against the matching record field type. Other store methods use positional arguments.

`clear()` is test-only in v0.4.

Generated Python includes schema metadata and records a schema hash in `sl_migrations`. v0.8 detects schema drift and prints a warning at startup; it does not perform automatic data migrations and does not overwrite stored drift metadata unless the database is first initialized.

### `config`

Apps may declare typed config values:

```sl
config AppConfig = {
  db_path: Text = env("SL_DB", "symboliclight.sqlite"),
  port: Int = env_int("PORT", 8000),
}
```

Config values compile to Python dictionaries and may be read as `AppConfig.port`.

### `fn`

`fn` is pure application logic. It must not call store methods, commands, routes, or runtime side effects. Imported module functions compile into generated Python with stable names such as `fn_models_is_open`.

Function and command calls support positional arguments and named arguments. Named arguments are matched to declared parameter names. Unknown, duplicate, or missing named arguments are rejected. Positional arguments may not follow named arguments.

### `command`

`command` compiles to a CLI subcommand. Commands may use stores and pure functions. Tests may call commands. Routes and pure functions may not call commands directly.

### `route`

`route` compiles to a JSON HTTP handler:

```sl
route GET "/todos" -> List<Todo> {
  return todos.all()
}
```

v0.4 supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`. Request body fields are read through `request.body.field`. Route return types must be JSON encodable: primitives, enums, records, `Id<T>`, `List<T>`, `Option<T>`, `Result<T, E>`, or `Response<T>`.

Routes may declare typed request bodies:

```sl
route POST "/todos" body CreateTodo -> Todo {
  return todos.insert({ title: request.body.title, done: false })
}
```

`GET` and `DELETE` routes may not declare a body in v0.4. `POST`, `PUT`, and `PATCH` routes may declare a record body. When a body type is declared, `request.body.field` is checked against that record. Generated Python returns `400` for malformed JSON and for missing required body fields.

Routes may return `Response<T>` by using the `response` built-in:

```sl
route POST "/todos" body CreateTodo -> Response<Todo> {
  let item = todos.insert({ title: request.body.title, done: false })
  return response(status: 201, body: item)
}
```

`Response<T>` supports `status`, optional `headers`, and `body`. v0.4 does not support streaming, cookies, middleware, or auth.

`response_ok(status: Int, body: T)` returns a `Response<Result<T, E>>` success response from the enclosing route target. `response_err(status: Int, code: Text, message: Text)` returns an error response using the route target's `ErrorBody`-style record, which must provide `code: Text` and `message: Text`. `ErrorBody` is the recommended gallery name, not a required built-in type name. These helpers do not introduce generic function syntax; their target types are checked from the enclosing route return type.

Routes may read HTTP headers through the minimal request helper:

```sl
request.header("Authorization") -> Option<Text>
```

`request.header` is route-only. It is intended for explicit token checks inside route bodies. v0.8 does not add middleware, cookies, sessions, or implicit auth policy.

### `fixture`

Fixtures seed stores before each inline test:

```sl
fixture todos {
  { title: "Buy milk", done: false }
}
```

Each executable test runs against a fresh in-memory SQLite database. Fixtures are app-only and must reference an existing store.

### `test`

Inline tests compile to generated Python assertions:

```sl
test "add creates todo" {
  let item = add("Buy milk")
  assert item.done == false
}
```

Golden tests compare returned values against a file:

```sl
test "list output" golden "./golden/list.json" {
  return list()
}
```

On mismatch, generated tests write an `.actual` file next to the golden file.

External IntentSpec tests are declared with:

```sl
test from intent.acceptance
```

Generated Python prints external tests as skipped. The `slc test` command owns IntentSpec acceptance execution because it has access to both the source app and the IntentSpec contract.

## Statements

```text
let name = expr
return expr
assert expr
if expr { ... } else { ... }
expr
```

## Expressions

v0.4 supports:

- text, number, and boolean literals,
- variable references,
- field access,
- function calls,
- named arguments,
- record literals,
- list literals,
- comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`,
- boolean operators: `&&`, `||`,
- wrapper constructors: `some(value)`, `none()`, `ok(value)`, `err(value)`.
- app-kit built-ins: `response`, `response_ok`, `response_err`, `env`, `env_int`, `uuid`, `now`, `read_text`, and `write_text`.
- route request helper: `request.header(name: Text) -> Option<Text>`.

`read_text` may be used in commands, routes, and tests. `write_text` may be used only in commands and tests.

## CLI

```bash
slc check <path>
slc check <path> --json
slc check <path> --no-cache
slc build <path> --out build/app.py
slc build <path> --out build/app.py --no-source-map
slc schema <path> --out build/schema.json
slc run <path> -- <generated-app-args>
slc test <path>
slc fmt <path>
slc doctor <path>
slc doctor <path> --json
slc doctor <path> --db path/to/app.sqlite
slc doctor <path> --db path/to/app.sqlite --json
slc lsp
slc init <dir>
slc new api <name>
slc add route GET /items <path>
```

`slc fmt` is the official formatter. v0.9 preserves `//` comments in common positions: file headers, comments before top-level items, comments before statements, and trailing comments. Formatting is intended to be idempotent. `slc add route` remains conservative and may still refuse to edit commented files when it cannot safely locate the app block.

`slc check --json` emits a machine-readable diagnostics array with `severity`, `code`, `message`, `file`, `line`, `column`, and `suggestion`.

`slc schema` emits deterministic JSON schema metadata for records, enums, route bodies, and route responses. It does not depend on generated Python.

`slc lsp` starts the developer-preview JSON-RPC language server over stdio. v0.9 supports diagnostics, hover, definition, document symbols, and whole-document formatting through the comment-preserving formatter.

`slc init <dir>` creates `src/app.sl`, `intent/app.intent.yaml`, `README.md`, and `.gitignore`. `slc new api <name>` creates the same project shape under `<name>/`. `slc add route` refuses to edit files that contain `//` comments or parser errors.

`slc doctor` reads optional SL-specific IntentSpec hints from comments:

```yaml
# sl: route GET /items
# sl: command add
```

These hints avoid adding nonstandard top-level fields to IntentSpec while still allowing doctor to compare declared routes and commands against the SL implementation.

The same hints are used by `slc test` when `test from intent.acceptance` is declared. Missing hinted routes or commands fail offline acceptance. Extra routes or commands are reported as warnings.

`slc doctor --db` inspects a SQLite database's `sl_migrations` metadata and the actual SQLite table structure. `schema drift: up to date` means the stored hash matches the generated hash. `schema diff: no structural difference detected` means the actual SQLite structure also matches. If the hash matches but the structure differs, doctor reports `schema drift: structural drift detected`. If the hash differs, doctor reports `schema drift: drift detected` and still includes summary schema differences. Diff lines use stable release-facing forms: `missing table`, `extra table`, `missing column`, `extra column`, and `type mismatch`. The command never mutates the database and does not perform automatic migrations.

`slc doctor --json` emits a machine-readable report with `source`, `unit`, `diagnostics`, `summary`, `intent`, `schema`, `cache`, and `source_map`. `schema.drift` uses stable enum values: `not_checked`, `not_initialized`, `up_to_date`, `structural_drift`, `hash_drift`, and `unable_to_inspect`. `schema.diff` is an array of objects with `kind` values such as `missing_table`, `extra_table`, `missing_column`, `extra_column`, and `type_mismatch`.

## Generated Python Contract

The compiler emits one Python 3.11 file using standard library modules first:

- `argparse`
- `sqlite3`
- `http.server`
- `json`

Generated code includes `# source: file.sl:line` comments for major functions, routes, and tests. `slc build` also emits a sidecar source map by default:

```text
build/app.py
build/app.py.slmap.json
```

The source map contains:

- `version`
- `source`
- `generated`
- `line_map`
- `symbols`

Generated test and runtime exceptions print a best-effort `SL source: file.sl:line:column` backreference when a mapped generated line is available. `slc build --no-source-map` suppresses the sidecar file but generated Python still contains the inline runtime map.

## Incremental Check Cache

`slc check` reuses cached diagnostics when the root source, imported module hashes, intent file hashes, missing dependency state, strict IntentSpec mode, and compiler cache version match. Creating a previously missing import or intent file invalidates the cached result. `slc check --no-cache` bypasses the cache. Cache files are stored under `.slcache/` and are not part of source control.

## Diagnostics

All compiler diagnostics use the same shape:

```text
severity + code + message + file + line + column + suggestion
```

Parser diagnostics use `SLP...` codes. Checker diagnostics use `SLC...` codes. Lexer diagnostics use `SLL...` codes.

## Out Of Scope Before v1.0

- frontend UI,
- package manager,
- macro system,
- advanced generics beyond `Id`, `List`, `Option`, and `Result`,
- custom async runtime,
- Postgres support,
- real LLM or agent runtime.
