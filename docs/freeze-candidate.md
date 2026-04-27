# SL v1.0 Stable Surface

SL v1.0 promotes the v0.13 release-candidate surface to the stable local release baseline. This does not freeze the project forever, but changes to these surfaces require a compatibility note, migration note, and regression fixture.

## Stable Surfaces

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

- v1.0 maintenance must not add new `.sl` syntax without a new minor-version plan.
- Any compatibility-affecting fix must update `docs/compatibility.md`, `CHANGELOG.md`, and at least one regression fixture.
- Public JSON field names must remain stable unless the release notes include a migration path.
- Generated Python may change internally, but user-visible HTTP error shape, CLI exit codes, and source backreference behavior should remain stable.
- Generated Python helper names and private implementation layout are not a public API unless documented in `docs/semantics.md`.

## Deferred Beyond v1.0

- automatic migration execution,
- package registry and version solver,
- production HTTP hosting,
- auth middleware, sessions, cookies, and password hashing,
- native compiler or non-Python backend.
