app ProjectOpsApi {
  intent "./project_ops.intent.yaml"

  permissions from intent.permissions

  enum TaskStatus { open, closed }

  type ErrorBody = {
    code: Text,
    message: Text,
  }

  type Project = {
    id: Id<Project>,
    name: Text,
    archived: Bool,
  }

  type Member = {
    id: Id<Member>,
    name: Text,
    role: Text,
    disabled_reason: Option<Text>,
  }

  type Task = {
    id: Id<Task>,
    project_id: Id<Project>,
    title: Text,
    status: TaskStatus,
    owner: Option<Text>,
  }

  type AuditEvent = {
    id: Id<AuditEvent>,
    message: Text,
    created_at: Text,
  }

  type CreateProject = {
    name: Text,
  }

  type CreateTask = {
    project_id: Id<Project>,
    title: Text,
    owner: Option<Text>,
  }

  config AppConfig = {
    admin_token: Text = env("ADMIN_TOKEN", "dev-token"),
    db_path: Text = env("SL_DB", "project_ops.sqlite"),
  }

  store projects: Project using sqlite
  store members: Member using sqlite
  store tasks: Task using sqlite
  store audit_events: AuditEvent using sqlite

  fn is_authorized(token: Option<Text>) -> Bool {
    return token == some(AppConfig.admin_token)
  }

  command create_project(name: Text) -> Project {
    let project = projects.insert({ name: name, archived: false })
    let audit = audit_events.insert({ message: "created project", created_at: now() })
    return project
  }

  command add_task(project_id: Id<Project>, title: Text, owner: Option<Text>) -> Task {
    return tasks.insert({ project_id: project_id, title: title, status: TaskStatus.open, owner: owner })
  }

  command list_projects() -> List<Project> {
    return projects.all()
  }

  route GET "/projects" -> Response<Result<List<Project>, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      return response_ok(status: 200, body: projects.all())
    }
    return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
  }

  route POST "/projects" body CreateProject -> Response<Result<Project, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      let project = projects.insert({ name: request.body.name, archived: false })
      let audit = audit_events.insert({ message: "created project", created_at: now() })
      return response_ok(status: 201, body: project)
    }
    return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
  }

  route GET "/tasks" -> Response<Result<List<Task>, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      return response_ok(status: 200, body: tasks.all())
    }
    return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
  }

  route POST "/tasks" body CreateTask -> Response<Result<Task, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      let task = tasks.insert({
        project_id: request.body.project_id,
        title: request.body.title,
        status: TaskStatus.open,
        owner: request.body.owner
      })
      return response_ok(status: 201, body: task)
    }
    return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
  }

  test "create project and task" {
    let project = create_project("Launch")
    let task = add_task(project.id, "Write release plan", some("Ada"))
    assert project.archived == false
    assert task.status == TaskStatus.open
  }

  test from intent.acceptance
}
