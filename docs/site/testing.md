# Testing

SL supports inline tests:

```sl
test "add creates todo" {
  let item = add("Buy milk")
  assert item.done == false
}
```

Fixtures seed stores before each test:

```sl
fixture todos {
  { title: "Buy milk", done: false }
}
```

Golden tests compare returned values against files:

```sl
test "list output" golden "./golden/list.json" {
  return list()
}
```

Run tests:

```bash
slc test examples/todo_app.sl
```

