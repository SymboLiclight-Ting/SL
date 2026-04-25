app AdminTemplate {
  intent "../intent/admin-template.intent.yaml"

  enum Role { admin, viewer }

  type AdminUser = {
    id: Id<AdminUser>,
    email: Text,
    role: Role,
    disabled: Bool,
  }

  type CreateAdmin = {
    email: Text,
    role: Role,
  }

  config AppConfig = {
    admin_token: Text = env("ADMIN_TOKEN", "dev-token"),
  }

  store users: AdminUser using sqlite

  fn is_authorized(token: Option<Text>) -> Bool {
    return token == some(AppConfig.admin_token)
  }

  command create_admin(email: Text, role: Role) -> AdminUser {
    return users.insert({ email: email, role: role, disabled: false })
  }

  route GET "/users" -> List<AdminUser> {
    return users.all()
  }

  route POST "/users" body CreateAdmin -> AdminUser {
    return users.insert({ email: request.body.email, role: request.body.role, disabled: false })
  }

  test "create admin" {
    let user = create_admin("admin@example.com", Role.admin)
    assert user.disabled == false
  }
}
