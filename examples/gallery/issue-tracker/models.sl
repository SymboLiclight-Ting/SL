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
