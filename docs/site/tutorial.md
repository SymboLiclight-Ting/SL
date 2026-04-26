# Build a Todo App

This tutorial builds a small Todo application in SL, then checks, tests, and compiles it to readable Python.

By the end, the app has:

- a record type for todo items,
- a SQLite-backed store,
- CLI commands,
- JSON HTTP routes,
- an IntentSpec link,
- a lightweight test.

## 1. Install the Local Compiler

From the repository root:

```bash
pip install -e ".[dev]"
```

Confirm that `slc` is available:

```bash
slc --help
```

## 2. Create the App File

Create a project directory and an empty SL source file:

```bash
mkdir -p build/tutorial-todo
```

Create `build/tutorial-todo/app.sl`:

```sl
app TutorialTodo {
}
```

Check it:

```bash
slc check build/tutorial-todo/app.sl
```

The app does not do anything yet, but this confirms that the compiler can parse and validate the file.

## 3. Add the Data Model

Replace `build/tutorial-todo/app.sl` with:

```sl
app TutorialTodo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }
}
```

`CreateTodo` describes the JSON request body for creating a todo. `Todo` is the stored record. `Id<Todo>` tells SL that the field is an ID for `Todo` records.

Run:

```bash
slc check build/tutorial-todo/app.sl
```

## 4. Add Storage

Add a `store` declaration:

```sl
app TutorialTodo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo
}
```

`store todos: Todo` compiles to a small SQLite-backed record store in the generated Python app.

Check again:

```bash
slc check build/tutorial-todo/app.sl
```

## 5. Add CLI Commands

Add `add` and `list` commands:

```sl
app TutorialTodo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  command list() -> List<Todo> {
    return todos.all()
  }
}
```

Compile the app:

```bash
slc build build/tutorial-todo/app.sl --out build/tutorial-todo/app.py
```

Run the generated CLI:

```bash
python build/tutorial-todo/app.py add "Buy milk"
python build/tutorial-todo/app.py list
```

The generated Python is ordinary Python 3.11. You can open `build/tutorial-todo/app.py` and inspect the code.

## 6. Add HTTP Routes

Add a route that lists todos and a route that creates todos from a typed request body:

```sl
app TutorialTodo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  command list() -> List<Todo> {
    return todos.all()
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }

  route POST "/todos" body CreateTodo -> Todo {
    let title = request.body.title
    return todos.insert({ title: title, done: false })
  }
}
```

Build and serve:

```bash
slc build build/tutorial-todo/app.sl --out build/tutorial-todo/app.py
python build/tutorial-todo/app.py serve
```

In another terminal, call the routes:

```bash
curl http://127.0.0.1:8000/todos
curl -X POST http://127.0.0.1:8000/todos -H "Content-Type: application/json" -d "{\"title\":\"Ship tutorial\"}"
```

## 7. Add a Test

Add a lightweight test block:

```sl
app TutorialTodo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  command list() -> List<Todo> {
    return todos.all()
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }

  route POST "/todos" body CreateTodo -> Todo {
    let title = request.body.title
    return todos.insert({ title: title, done: false })
  }

  test "add creates todo" {
    let item = add("Buy milk")
    assert item.done == false
  }
}
```

Run the test through `slc`:

```bash
slc test build/tutorial-todo/app.sl
```

Or build first and run the generated app test command:

```bash
slc build build/tutorial-todo/app.sl --out build/tutorial-todo/app.py
python build/tutorial-todo/app.py test
```

## 8. Link an IntentSpec File

SL apps can point to an IntentSpec file. This keeps the implementation connected to the app contract.

Create `build/tutorial-todo/tutorial.intent.yaml`:

```yaml
version: "0.1"
kind: "IntentSpec"

# sl: route GET /todos
# sl: route POST /todos
# sl: command add
# sl: command list

metadata:
  name: "tutorial_todo"
  title: "Tutorial Todo"
  owner: "symboliclight"

task:
  goal: "Build a local Todo app with CLI commands and JSON HTTP routes."
  audience:
    - "Application developer"
  priority: "medium"

permissions:
  web: true
  filesystem:
    read: true
    write: true
  network: false
  tools:
    create_file: true
    delete_file: false

output:
  format: "markdown"
  language: "en"
  max_words: 300
  sections:
    - "Build"
    - "Run"
    - "Test"
```

Then add the `intent` and `permissions` declarations near the top of the app:

```sl
app TutorialTodo {
  intent "./tutorial.intent.yaml"

  permissions from intent.permissions

  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  command list() -> List<Todo> {
    return todos.all()
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }

  route POST "/todos" body CreateTodo -> Todo {
    let title = request.body.title
    return todos.insert({ title: title, done: false })
  }

  test "add creates todo" {
    let item = add("Buy milk")
    assert item.done == false
  }
}
```

Run the compiler and doctor:

```bash
slc check build/tutorial-todo/app.sl
slc doctor build/tutorial-todo/app.sl
```

If the optional `intentspec` package is installed, `slc check` validates the referenced IntentSpec file. Without it, SL reports a warning unless `--strict-intent` is used.

## 9. Format and Inspect

Format the app:

```bash
slc fmt build/tutorial-todo/app.sl
```

Generate schema metadata:

```bash
slc schema build/tutorial-todo/app.sl --out build/tutorial-todo/schema.json
```

Build the final Python file:

```bash
slc build build/tutorial-todo/app.sl --out build/tutorial-todo/app.py
```

At this point, the same SL source defines the data model, storage, CLI commands, HTTP routes, tests, and contract link.

## What To Read Next

- [Language Tour](language-tour.md) explains the main declarations.
- [Database](database.md) describes generated stores and database behavior.
- [IntentSpec](intentspec.md) explains the contract layer.
- [Testing](testing.md) covers SL tests and generated app tests.
