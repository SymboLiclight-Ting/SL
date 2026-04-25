app IssueTracker {
  import "./models.sl" as models

  intent "./issue.intent.yaml"

  permissions from intent.permissions

  store issues: models.Issue

  command create(title: Text) -> models.Issue {
    return issues.insert({ title: title, status: models.Status.open })
  }

  command list_open() -> List<models.Issue> {
    return issues.filter(status: models.Status.open)
  }

  route GET "/issues" -> List<models.Issue> {
    return issues.all()
  }

  test from intent.acceptance

  test "create issue" {
    let issue = create("Bug")
    assert issue.status == models.Status.open
    assert models.is_open(issue.status) == true
  }
}
