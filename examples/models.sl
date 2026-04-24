module models {
  enum Status { open, closed }

  type Issue = {
    id: Id<Issue>,
    title: Text,
    status: Status,
    assignee: Option<Text>,
  }
}
