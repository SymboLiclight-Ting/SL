app ProjectOpsTemplate {
  intent "../intent/project-ops-template.intent.yaml"

  enum TaskStatus { open, done }

  type Project = {
    id: Id<Project>,
    name: Text,
    archived: Bool,
  }

  type Task = {
    id: Id<Task>,
    project_id: Id<Project>,
    title: Text,
    status: TaskStatus,
  }

  type CreateProject = {
    name: Text,
  }

  type CreateTask = {
    project_id: Id<Project>,
    title: Text,
  }

  config AppConfig = {
    db_path: Text = env("SL_DB", "symboliclight.sqlite"),
  }

  store projects: Project using sqlite
  store tasks: Task using sqlite

  command create_project(name: Text) -> Project {
    return projects.insert({ name: name, archived: false })
  }

  command create_task(project_id: Id<Project>, title: Text) -> Task {
    return tasks.insert({ project_id: project_id, title: title, status: TaskStatus.open })
  }

  route GET "/projects" -> List<Project> {
    return projects.all()
  }

  route POST "/projects" body CreateProject -> Project {
    return projects.insert({ name: request.body.name, archived: false })
  }

  route GET "/tasks" -> List<Task> {
    return tasks.all()
  }

  route POST "/tasks" body CreateTask -> Task {
    return tasks.insert({ project_id: request.body.project_id, title: request.body.title, status: TaskStatus.open })
  }

  test "create project" {
    let project = create_project("Launch")
    assert project.archived == false
  }
}
