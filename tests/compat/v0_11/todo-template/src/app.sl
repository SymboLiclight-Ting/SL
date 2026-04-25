app TodoTemplate {
  intent "../intent/todo-template.intent.yaml"

  type Item = {
    id: Id<Item>,
    title: Text,
    done: Bool,
  }

  store items: Item

  command add(title: Text) -> Item {
    return items.insert({ title: title, done: false })
  }

  route GET "/items" -> List<Item> {
    return items.all()
  }

  test "add creates item" {
    let item = add("Example")
    assert item.done == false
  }
}
