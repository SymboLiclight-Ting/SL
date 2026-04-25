# Roadmap

## v0.2 Core Freeze Candidate

Implemented in the current mainline:

- explicit `module` and aliased `import`,
- imported pure module functions compile to Python,
- `enum`, `Option<T>`, and `Result<T, E>` type support,
- pure `fn` boundary checks,
- stricter store field checks,
- stricter store id and filter argument checks,
- parser recovery no longer hangs on invalid module items,
- official `slc fmt`,
- `slc doctor`, `slc init`, `slc new api`, and `slc add route`,
- generated Python source comments,
- `docs/compatibility.md`,
- Todo and Issue Tracker examples.

## v0.3 Reliable Compiler

Implemented in the current mainline:

- parser result API with multiple diagnostics per file,
- stricter import alias, namespace, named argument, record field, enum, `Option`, and `Result` checks,
- source-map sidecar files and best-effort generated runtime backreferences,
- incremental check cache reuse with import, intent, and missing dependency invalidation,
- `slc check --json`, `slc check --no-cache`, and `slc build --no-source-map`,
- release diagnostics with stable `severity`, `code`, `message`, `file`, `line`, `column`, and `suggestion` fields.

Deferred to later releases:

- fully typed route body declarations,
- comment-preserving formatter trivia,
- full `Option` and `Result` pattern matching ergonomics.

## v0.4 Standard App Kit

Implemented in the current mainline:

- typed route bodies and `Response<T>`,
- SQLite helpers: `count`, `exists`, and test-only `clear`,
- generated schema metadata and schema drift warnings,
- `slc schema` JSON schema generation,
- fixtures and golden tests,
- typed config with `env` and `env_int`,
- thin `uuid`, `now`, `read_text`, and `write_text` built-ins,
- `slc doctor` route schema status,
- Notes API example.

Deferred to later releases:

- automatic database migrations,
- Postgres support,
- full IntentSpec route, command, and permission diffing,
- auth middleware,
- comment-preserving formatter trivia.

## v0.5 Public Developer Preview

Implemented in the current mainline:

- VS Code syntax package,
- initial LSP diagnostics, hover, definitions, document symbols, and formatting,
- example gallery,
- local playground that shows `.sl` input, generated Python, and diagnostics,
- three complete sample apps.

Deferred to later releases:

- publishing the VS Code extension to the marketplace,
- full semantic token support,
- comment-preserving formatter trivia,
- hosted playground,
- richer refactoring actions.

## v0.6 IntentSpec And Release Hardening

Implemented in the current mainline:

- IntentSpec-aware `slc doctor` route and command diffing through `# sl:` hints,
- permission mismatch reporting for routes, file reads, and local state writes,
- offline IntentSpec acceptance execution through `slc test` for `test from intent.acceptance`,
- repeatable release smoke checks through `scripts/release_check.py`,
- Customer Brief Generator gallery example.

Deferred to later releases:

- full structured IntentSpec route schemas once IntentSpec supports those fields,
- richer IntentSpec assertion execution beyond `required_sections`,
- PyPI publishing automation,
- migration fixtures across many historical releases.

## v0.7 Real App Validation

Implemented in the current mainline:

- Small Admin Backend gallery example,
- route header reads through `request.header(name: Text) -> Option<Text>`,
- read-only `slc doctor --db` schema drift inspection,
- release smoke coverage for five gallery examples.

Deferred to later releases:

- auth middleware,
- password hashing and session management,
- automatic database migrations,
- richer migration planning output.

## v0.8 Ecosystem Hardening

Implemented in the current mainline:

- summary schema diff output in `slc doctor --db`,
- `try_update(id, record) -> Option<T>` for SQLite stores,
- `response_ok` and `response_err` helpers for `Response<Result<...>>`,
- Small Admin Backend refactored around explicit auth helper and `ErrorBody`,
- release-facing schema drift wording and local doctor drift smoke coverage.

Deferred to later releases:

- PyPI release flow,
- documentation site,
- compatibility test suite across prior examples,
- generated migration SQL.

## v0.9 Candidate Direction

Likely next work:

- comment-preserving formatter,
- stronger IDE/LSP polish,
- richer migration planning without automatic data mutation,
- compatibility fixtures across v0.6, v0.7, and v0.8 examples.

## v1.0 Stable

- syntax freeze,
- core standard library stability,
- stable CLI behavior,
- documented compatibility guarantees,
- real project case studies.
