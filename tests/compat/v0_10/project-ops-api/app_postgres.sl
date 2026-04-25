app ProjectOpsApiPostgres {
  enum TaskStatus { open, closed }

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
    owner: Option<Text>,
  }

  config AppConfig = {
    db_url: Text = env("SL_DB_URL", "postgresql://localhost/symboliclight"),
  }

  store projects: Project using postgres
  store tasks: Task using postgres

  command create_project(name: Text) -> Project {
    return projects.insert({ name: name, archived: false })
  }

  command add_task(project_id: Id<Project>, title: Text, owner: Option<Text>) -> Task {
    return tasks.insert({ project_id: project_id, title: title, status: TaskStatus.open, owner: owner })
  }
}
