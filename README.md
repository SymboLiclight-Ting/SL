# SymbolicLight

SymbolicLight Language, or SL, is a spec-native, AI-friendly application language.

It is designed for developers who want application code that is easy for humans and AI tools to generate, review, test, and maintain. SL v0 focuses on small backend and CLI applications, then compiles them to readable Python 3.11.

SymbolicLight is not trying to replace Python, Rust, or TypeScript everywhere. Its first goal is narrower:

> Write application intent, data models, storage, routes, commands, and tests in one compact source file, then compile to ordinary Python.

## Naming

- Formal project and brand name: SymbolicLight.
- Developer-facing language name: SL.
- Compiler command: `slc`.
- Source file extension: `.sl`.

Use SymbolicLight in project, website, release, and positioning text. Use SL in developer docs, examples, tutorials, and day-to-day language references.

## Current MVP

The v0.6 developer preview supports:

- `app` declarations.
- `module` declarations and explicit `import "./file.sl" as name`.
- `intent "./file.intent.yaml"` links to IntentSpec contracts.
- `permissions from intent.permissions` and `test from intent.acceptance` declarations.
- `enum` declarations and `type` record declarations.
- pure `fn` declarations inside modules and apps.
- `Option<T>` and `Result<T, E>` type references.
- `store` declarations backed by SQLite.
- `command` handlers compiled to CLI subcommands.
- `route GET/POST/PUT/PATCH/DELETE` handlers compiled to JSON HTTP routes.
- typed route bodies and `Response<T>` status responses.
- `fixture` declarations and golden tests.
- typed `config` declarations.
- SQLite helpers such as `count`, `exists`, and test-only `clear`.
- JSON schema generation through `slc schema`.
- `test` blocks compiled to lightweight Python assertions.
- official formatting through `slc fmt`.
- source-map sidecars and best-effort `.sl` runtime backreferences.
- incremental `slc check` cache reuse.
- JSON diagnostics for tools through `slc check --json`.
- developer-preview LSP through `slc lsp`.
- local VS Code syntax, snippets, and language-server wiring under `editors/vscode`.
- local playground under `playground/`.
- IntentSpec-aware `slc doctor` route, command, and permission alignment hints.
- repeatable release smoke checks through `scripts/release_check.py`.

## Quick Start

```bash
pip install -e ".[dev]"
slc check examples/todo_app.sl
slc check examples/todo_app.sl --json
slc build examples/todo_app.sl --out build/todo_app.py
slc schema examples/notes_api.sl --out build/notes_schema.json
slc fmt examples/todo_app.sl --check
slc doctor examples/todo_app.sl
slc lsp
python build/todo_app.py test
python build/todo_app.py add "Buy milk"
python build/todo_app.py list
python build/todo_app.py serve
```

The generated app uses only the Python standard library: `argparse`, `sqlite3`, `http.server`, and `json`.

## Example

```sl
app TodoApp {
  intent "./todo.intent.yaml"

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }
}
```

Typed request bodies and status responses:

```sl
route POST "/notes" body CreateNote -> Response<Note> {
  let note = notes.insert({ title: request.body.title, body: request.body.body })
  return response(status: 201, body: note)
}
```

Multi-file apps use explicit imports:

```sl
module models {
  enum Status { open, closed }

  type Issue = {
    id: Id<Issue>,
    title: Text,
    status: Status,
    assignee: Option<Text>,
  }

  fn is_open(status: Status) -> Bool {
    return status == Status.open
  }
}
```

```sl
app IssueTracker {
  import "./models.sl" as models

  store issues: models.Issue

  command create(title: Text) -> models.Issue {
    return issues.insert({ title: title, status: models.Status.open })
  }

  route GET "/open" -> Bool {
    return models.is_open(models.Status.open)
  }
}
```

## Relationship With IntentSpec

IntentSpec describes task intent, permissions, output contracts, and acceptance tests.

SymbolicLight implements the application.

Together:

```text
IntentSpec = what should be built and how it is accepted
SymbolicLight = the application implementation
```

IntentSpec validation is optional in normal `slc check` runs. If the `intentspec` package is installed, SL validates referenced intent files. Missing IntentSpec support is reported as a warning unless `--strict-intent` is used.

## Commands

```bash
slc check <file.sl>
slc check <file.sl> --json
slc check <file.sl> --no-cache
slc build <file.sl> --out build/app.py
slc build <file.sl> --out build/app.py --no-source-map
slc schema <file.sl> --out build/schema.json
slc run <file.sl> -- add "Buy milk"
slc test <file.sl>
slc fmt <file.sl>
slc doctor <file.sl>
slc lsp
slc init <dir>
slc new api <name>
slc add route GET /items <file.sl>
```

## Release Check

```bash
python scripts/release_check.py --skip-package
```

## Project Status

This is a public developer preview. The goal is to prove that a spec-native application language can compile into readable, runnable Python while keeping source code compact and AI-friendly. v0.x remains experimental and may include breaking changes before v1.0.
