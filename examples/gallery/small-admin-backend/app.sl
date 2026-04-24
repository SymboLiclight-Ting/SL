app SmallAdminBackend {
  intent "./admin.intent.yaml"

  permissions from intent.permissions

  enum Role { owner, admin, auditor }

  type CreateAdmin = {
    name: Text,
    email: Text,
  }

  type DisableAdmin = {
    id: Id<AdminUser>,
    name: Text,
    email: Text,
    reason: Text,
  }

  type ErrorBody = {
    code: Text,
    message: Text,
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

  fn is_authorized(token: Option<Text>) -> Bool {
    return token == some(AdminConfig.admin_token)
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

  command disable_admin(id: Id<AdminUser>, name: Text, email: Text, reason: Text) -> AdminUser {
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

  route GET "/admins" -> Response<Result<List<AdminUser>, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      return response_ok(status: 200, body: users.all())
    } else {
      return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
    }
  }

  route POST "/admins" body CreateAdmin -> Response<Result<AdminUser, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      let user = users.insert({
        name: request.body.name,
        email: request.body.email,
        role: Role.admin,
        active: true,
        disabled_reason: none()
      })
      audit_events.insert({ action: "route_create_admin", actor: request.body.name, created_at: now() })
      return response_ok(status: 201, body: user)
    } else {
      return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
    }
  }

  route PATCH "/admins/disable" body DisableAdmin -> Response<Result<AdminUser, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      let user = users.update(request.body.id, {
        name: request.body.name,
        email: request.body.email,
        role: Role.admin,
        active: false,
        disabled_reason: some(request.body.reason)
      })
      audit_events.insert({ action: "route_disable_admin", actor: request.body.name, created_at: now() })
      return response_ok(status: 200, body: user)
    } else {
      return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
    }
  }

  route GET "/audit" -> Response<Result<List<AuditEvent>, ErrorBody>> {
    if is_authorized(request.header("Authorization")) {
      return response_ok(status: 200, body: audit_events.all())
    } else {
      return response_err(status: 401, code: "unauthorized", message: "Admin token is required.")
    }
  }

  test from intent.acceptance

  test "admin lifecycle" {
    let user = create_admin("Ada", "ada@example.com")
    assert users.count() == 1
    let disabled = disable_admin(user.id, user.name, user.email, "left team")
    assert disabled.active == false
    assert users.try_update(999, {
      name: "Missing",
      email: "missing@example.com",
      role: Role.admin,
      active: false,
      disabled_reason: some("missing")
    }) == none()
    assert audit_events.count() == 2
  }

  test "session token" {
    let session = create_session(uuid(), "Ada", now())
    assert session.owner == "Ada"
  }
}
