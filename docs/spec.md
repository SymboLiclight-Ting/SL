# SymbolicLight Language Specification v0.3

This document defines SymbolicLight v0.3 as a spec-native, AI-friendly application language that compiles to readable Python 3.11.

## Source Units

Each `.sl` file contains exactly one top-level unit:

```sl
app Name { ... }
module name { ... }
```

An `app` is executable and can be built, run, tested, and served. A `module` is imported by an app or another module and may define shared records, enums, and pure `fn` logic.

## Keywords

```text
app module import as intent permissions from enum type fn store route command test let return assert if else true false
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

Stores are backed by SQLite in v0.3. Supported methods:

```text
todos.insert(record) -> Todo
todos.all() -> List<Todo>
todos.get(id) -> Option<Todo>
todos.update(id, record) -> Todo
todos.delete(id) -> Bool
todos.filter(field: value) -> List<Todo>
```

`insert` and `update` require record literals in v0.3. The checker validates unknown fields, duplicate fields, missing required fields, and obvious field type mismatches.

`get`, `update`, and `delete` require an `Int` or `Id<T>` id argument.

`filter` requires named arguments and validates each filter value against the matching record field type. Other store methods use positional arguments in v0.3.

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

v0.3 supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`. Request body fields are read through `request.body.field`. Route return types must be JSON encodable: primitives, enums, records, `Id<T>`, `List<T>`, `Option<T>`, `Result<T, E>`, or `Response<T>`.

### `test`

Inline tests compile to generated Python assertions:

```sl
test "add creates todo" {
  let item = add("Buy milk")
  assert item.done == false
}
```

External IntentSpec tests are declared with:

```sl
test from intent.acceptance
```

## Statements

```text
let name = expr
return expr
assert expr
if expr { ... } else { ... }
expr
```

## Expressions

v0.2 supports:

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

## CLI

```bash
slc check <path>
slc check <path> --json
slc check <path> --no-cache
slc build <path> --out build/app.py
slc build <path> --out build/app.py --no-source-map
slc run <path> -- <generated-app-args>
slc test <path>
slc fmt <path>
slc doctor <path>
slc init <dir>
slc new api <name>
slc add route GET /items <path>
```

`slc fmt` is intentionally conservative in v0.3. It refuses to rewrite files containing `//` comments because the formatter does not yet have comment-preserving trivia support.

`slc check --json` emits a machine-readable diagnostics array with `severity`, `code`, `message`, `file`, `line`, `column`, and `suggestion`.

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

## Out Of Scope Before v0.5

- frontend UI,
- package manager,
- macro system,
- advanced generics beyond `Id`, `List`, `Option`, and `Result`,
- custom async runtime,
- Postgres support,
- real LLM or agent runtime.
