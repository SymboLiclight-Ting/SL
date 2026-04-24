# SymbolicLight Language Specification v0.2

This document defines SymbolicLight v0.2 as a spec-native, AI-friendly application language that compiles to readable Python 3.11.

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

Imported declarations are referenced through the alias, for example `models.Issue` or `models.Status.open`. SymbolicLight has no implicit global sharing.

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

Stores are backed by SQLite in v0.2. Supported methods:

```text
todos.insert(record) -> Todo
todos.all() -> List<Todo>
todos.get(id) -> Option<Todo>
todos.update(id, record) -> Todo
todos.delete(id) -> Bool
todos.filter(field: value) -> List<Todo>
```

`insert` and `update` validate record fields at compile time when the argument is a record literal.

### `fn`

`fn` is pure application logic. It must not call store methods, commands, routes, or runtime side effects.

### `command`

`command` compiles to a CLI subcommand. Commands may use stores and pure functions. Tests may call commands. Routes and pure functions may not call commands directly.

### `route`

`route` compiles to a JSON HTTP handler:

```sl
route GET "/todos" -> List<Todo> {
  return todos.all()
}
```

v0.2 supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`. Request body fields are read through `request.body.field`.

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
slc build <path> --out build/app.py
slc run <path> -- <generated-app-args>
slc test <path>
slc fmt <path>
slc doctor <path>
slc init <dir>
slc new api <name>
slc add route GET /items <path>
```

## Generated Python Contract

The compiler emits one Python 3.11 file using standard library modules first:

- `argparse`
- `sqlite3`
- `http.server`
- `json`

Generated code includes `# source: file.sl:line` comments for major functions, routes, and tests.

## Out Of Scope Before v0.5

- frontend UI,
- package manager,
- macro system,
- advanced generics beyond `Id`, `List`, `Option`, and `Result`,
- custom async runtime,
- Postgres support,
- real LLM or agent runtime.
