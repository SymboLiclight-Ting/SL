# App Kit

The v0 app kit focuses on CLI and backend applications.

HTTP routes:

```sl
route POST "/todos" body CreateTodo -> Response<Todo> {
  let item = todos.insert({ title: request.body.title, done: false })
  return response(status: 201, body: item)
}
```

SQLite store helpers:

- `insert(record) -> T`
- `all() -> List<T>`
- `get(id) -> Option<T>`
- `update(id, record) -> T`
- `try_update(id, record) -> Option<T>`
- `delete(id) -> Bool`
- `filter(field: value) -> List<T>`
- `count() -> Int`
- `exists(id) -> Bool`
- `clear() -> Int` in tests only

Config values:

```sl
config AppConfig = {
  db_path: Text = env("SL_DB", "symboliclight.sqlite"),
  port: Int = env_int("PORT", 8000),
}
```

