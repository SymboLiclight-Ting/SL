app NotesTemplate {
  intent "../intent/notes-template.intent.yaml"

  type Note = {
    id: Id<Note>,
    title: Text,
    body: Text,
  }

  type CreateNote = {
    title: Text,
    body: Text,
  }

  store notes: Note using sqlite

  command add_note(title: Text, body: Text) -> Note {
    return notes.insert({ title: title, body: body })
  }

  route GET "/notes" -> List<Note> {
    return notes.all()
  }

  route POST "/notes" body CreateNote -> Note {
    return notes.insert({ title: request.body.title, body: request.body.body })
  }

  test "add creates note" {
    let note = add_note("Hello", "World")
    assert note.title == "Hello"
  }
}
