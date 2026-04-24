app NotesApi {
  intent "./notes.intent.yaml"

  type CreateNote = {
    title: Text,
    body: Text,
  }

  type Note = {
    id: Id<Note>,
    title: Text,
    body: Text,
  }

  store notes: Note

  config NotesConfig = {
    port: Int = env_int("PORT", 8000),
  }

  fixture notes {
    { title: "Welcome", body: "First note" },
  }

  command add(title: Text, body: Text) -> Note {
    return notes.insert({ title: title, body: body })
  }

  command list() -> List<Note> {
    return notes.all()
  }

  command count() -> Int {
    return notes.count()
  }

  route GET "/notes" -> List<Note> {
    return notes.all()
  }

  route POST "/notes" body CreateNote -> Response<Note> {
    let note = notes.insert({ title: request.body.title, body: request.body.body })
    return response(status: 201, body: note)
  }

  test "fixture count" {
    assert notes.count() == 1
  }

  test "golden notes" golden "./golden/notes.json" {
    return notes.all()
  }
}
