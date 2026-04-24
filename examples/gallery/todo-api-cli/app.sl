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

  command list() -> List<Todo> {
    return todos.all()
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }

  route POST "/todos" -> Todo {
    let title = request.body.title
    return todos.insert({ title: title, done: false })
  }

  test "add creates todo" {
    let item = add("Buy milk")
    assert item.done == false
  }
}
