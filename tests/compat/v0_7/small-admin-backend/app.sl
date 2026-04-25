app SmallAdminBackend {
  intent "./admin.intent.yaml"

  permissions from intent.permissions

  enum Role { owner, admin, auditor }

  type CreateAdmin = {
    name: Text,
    email: Text,
  }

  type DisableAdmin = {
    id: Int,
    name: Text,
    email: Text,
    reason: Text,
  }

  type AdminUser = {
    id: Id<AdminUser>,
    name: Text,
    email: Text,
    role: Role,
    active: Bool,
    disabled_reason: Option<Text>,
  }

  type AuditEvent = {
    id: Id<AuditEvent>,
    action: Text,
    actor: Text,
    created_at: Text,
  }

  type SessionToken = {
    id: Id<SessionToken>,
    token: Text,
    owner: Text,
    expires_at: Text,
  }

  store users: AdminUser
  store audit_events: AuditEvent
  store sessions: SessionToken

  config AdminConfig = {
    admin_token: Text = env("ADMIN_TOKEN", "dev-token"),
    db_path: Text = env("SL_DB", "admin.sqlite"),
    port: Int = env_int("PORT", 8000),
  }

  command create_admin(name: Text, email: Text) -> AdminUser {
    let user = users.insert({
      name: name,
      email: email,
      role: Role.admin,
      active: true,
      disabled_reason: none()
    })
    audit_events.insert({ action: "create_admin", actor: name, created_at: now() })
    return user
  }

  command list_admins() -> List<AdminUser> {
    return users.all()
  }

  command disable_admin(id: Int, name: Text, email: Text, reason: Text) -> AdminUser {
    let user = users.update(id, {
      name: name,
      email: email,
      role: Role.admin,
      active: false,
      disabled_reason: some(reason)
    })
    audit_events.insert({ action: "disable_admin", actor: name, created_at: now() })
    return user
  }

  command create_session(token: Text, owner: Text, expires_at: Text) -> SessionToken {
    return sessions.insert({ token: token, owner: owner, expires_at: expires_at })
  }

  route GET "/health" -> Text {
    return "ok"
  }

  route GET "/admins" -> Response<List<AdminUser>> {
    if request.header("Authorization") == some(AdminConfig.admin_token) {
      return response(status: 200, body: users.all())
    } else {
      return response(status: 401, body: [])
    }
  }

  route POST "/admins" body CreateAdmin -> Response<AdminUser> {
    if request.header("Authorization") == some(AdminConfig.admin_token) {
      let user = users.insert({
        name: request.body.name,
        email: request.body.email,
        role: Role.admin,
        active: true,
        disabled_reason: none()
      })
      audit_events.insert({ action: "route_create_admin", actor: request.body.name, created_at: now() })
      return response(status: 201, body: user)
    } else {
      return response(status: 401, body: users.insert({
        name: "unauthorized",
        email: "unauthorized",
        role: Role.auditor,
        active: false,
        disabled_reason: some("unauthorized")
      }))
    }
  }

  route PATCH "/admins/disable" body DisableAdmin -> Response<AdminUser> {
    if request.header("Authorization") == some(AdminConfig.admin_token) {
      let user = users.update(request.body.id, {
        name: request.body.name,
        email: request.body.email,
        role: Role.admin,
        active: false,
        disabled_reason: some(request.body.reason)
      })
      audit_events.insert({ action: "route_disable_admin", actor: request.body.name, created_at: now() })
      return response(status: 200, body: user)
    } else {
      return response(status: 401, body: users.insert({
        name: "unauthorized",
        email: "unauthorized",
        role: Role.auditor,
        active: false,
        disabled_reason: some("unauthorized")
      }))
    }
  }

  route GET "/audit" -> Response<List<AuditEvent>> {
    if request.header("Authorization") == some(AdminConfig.admin_token) {
      return response(status: 200, body: audit_events.all())
    } else {
      return response(status: 401, body: [])
    }
  }

  test from intent.acceptance

  test "admin lifecycle" {
    let user = create_admin("Ada", "ada@example.com")
    assert users.count() == 1
    let disabled = disable_admin(1, user.name, user.email, "left team")
    assert disabled.active == false
    assert audit_events.count() == 2
  }

  test "session token" {
    let session = create_session(uuid(), "Ada", now())
    assert session.owner == "Ada"
  }
}
