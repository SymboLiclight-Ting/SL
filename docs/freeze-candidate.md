# SL v0.13 Freeze Candidate

v0.13 is the release-candidate hardening phase for the v1.0 public surface. It does not freeze the project forever, but it identifies the surfaces that should not change without a compatibility note, migration note, and regression fixture.

## Freeze Candidate Surfaces

- top-level items: `app`, `module`, `import`, `intent`, `permissions`, `test from intent.acceptance`, `enum`, `type`, `store`, `config`, `fixture`, `fn`, `command`, `route`, and `test`.
- type syntax: primitive types, record types, enum references, `Id<T>`, `List<T>`, `Option<T>`, `Result<T, E>`, `Response<T>`, and imported qualified type names.
- store helpers: `insert`, `all`, `get`, `update`, `try_update`, `delete`, `filter`, `count`, `exists`, and test-only `clear`.
- route syntax: `route METHOD "/path"`, typed route bodies with `body TypeName`, and return type declarations.
- Response/Result helpers: `response`, `response_ok`, and `response_err`.
- CLI commands: `slc check`, `slc build`, `slc schema`, `slc run`, `slc test`, `slc fmt`, `slc doctor`, `slc migrate`, `slc lsp`, `slc init`, `slc new`, and `slc add`.
- diagnostics JSON: `"severity"`, `"code"`, `"message"`, `"file"`, `"line"`, `"column"`, and `"suggestion"`.
- doctor JSON: `"source"`, `"unit"`, `"diagnostics"`, `"summary"`, `"intent"`, `"schema"`, `"drift"`, `"diff"`, `"cache"`, and `"source_map"`.
- migrate plan JSON: `"kind"`, `"table"`, `"column"`, `"expected"`, `"actual"`, and `"suggestion"`.
- generated HTTP error envelope: `{"error": {"code": "...", "message": "..."}}`.

## Change Policy

- v0.13 must not add new `.sl` syntax.
- Any compatibility-affecting fix must update `docs/compatibility.md`, `CHANGELOG.md`, and at least one regression fixture.
- Public JSON field names must remain stable unless the release notes include a migration path.
- Generated Python may change internally, but user-visible HTTP error shape, CLI exit codes, and source backreference behavior should remain stable.

## Deferred From Freeze

- automatic migration execution,
- package registry and version solver,
- production HTTP hosting,
- auth middleware, sessions, cookies, and password hashing,
- native compiler or non-Python backend.
