# Language Tour

An SL app starts with an `app` block:

```sl
app TodoApp {
  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo
}
```

Core declarations:

- `type` defines records.
- `enum` defines stable text variants.
- `store` creates a SQLite-backed record store.
- `fn` defines pure application logic.
- `command` defines CLI behavior.
- `route` defines JSON HTTP behavior.
- `test` defines lightweight application tests.

Modules are explicit:

```sl
import "./models.sl" as models
```

Imported names stay qualified, such as `models.Issue` or `models.Status.open`.

