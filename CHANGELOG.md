# Changelog

## v0.8.0

- Added read-only summary schema diff output to `slc doctor --db`.
- Added `try_update(id, record) -> Option<T>` for stores.
- Added `response_ok` and `response_err` helpers for `Response<Result<...>>`.
- Updated Small Admin Backend to use an explicit auth helper and unified `ErrorBody` responses.

## v0.7.0

- Added the Small Admin Backend gallery example for real-app validation.
- Added route-only `request.header(name: Text) -> Option<Text>` for explicit header token checks.
- Added read-only `slc doctor --db` schema drift inspection.
- Added release smoke coverage for the fifth gallery app.
- Documented v0.7 auth and migration boundaries.
- Tightened target-aware record validation through `Response<T>`, `Result<T, E>`, and `Option<T>` wrappers.
- Improved `Id<T>` ergonomics for CLI parameters and store id diagnostics.
- Made generated `store.update` fail explicitly when the target id does not exist.

## v0.6.0

- Prepared `0.6.0rc1` packaging for the `v0.6.0-rc1` release candidate.
- Added IntentSpec-aware `slc doctor` diffing for SL route and command hints.
- Added offline IntentSpec acceptance checks through `slc test` for `test from intent.acceptance`.
- Added permission mismatch reporting for routes, local state writes, and file reads/writes.
- Hardened route handler names, SQLite identifier quoting, and formatter string escaping.
- Added `scripts/release_check.py` for repeatable release smoke checks.
- Added wheel install smoke checks for release candidates, including installed-`slc` gallery runs from an empty workspace.
- Added the Customer Brief Generator gallery example.
- Documented v0.6 release hardening behavior.

## v0.5.0

- Added `slc lsp` with developer-preview diagnostics, hover, definition, document symbols, and formatting support.
- Added a local VS Code preview extension for `.sl` syntax highlighting, snippets, and LSP startup.
- Strengthened `slc init`, `slc new api`, and `slc add route` project-generation behavior.
- Added the SL example gallery for Todo, Notes, and Issue Tracker samples.
- Added a local playground that compiles `.sl` source to Python or diagnostics JSON.
- Documented the public developer preview status and SL naming convention.

## v0.4.0

- Added typed route request bodies with `body TypeName`.
- Added `Response<T>` support through `response(status: ..., body: ...)`.
- Added SQLite helpers: `count`, `exists`, and test-only `clear`.
- Added generated schema metadata and startup schema drift warnings.
- Added `fixture` declarations and isolated in-memory fixture loading for tests.
- Added golden tests for generated output comparison.
- Added typed `config` declarations backed by `env` and `env_int`.
- Added thin standard-library builtins: `uuid`, `now`, `read_text`, and `write_text`.
- Added `slc schema` JSON schema generation.
- Added the Notes API example as the v0.4 regression app.

## v0.3.0

- Added parser result APIs for multi-diagnostic recovery.
- Added stricter checker validation for imports, named arguments, record literals, route returns, `Option<T>`, and `Result<T, E>`.
- Added source-map sidecar output from `slc build`.
- Added generated runtime backreferences that print best-effort `.sl` source locations for exceptions.
- Added reusable check cache with imported module hash invalidation.
- Added `slc check --json`, `slc check --no-cache`, and `slc build --no-source-map`.
- Standardized diagnostics around `severity`, `code`, `message`, `file`, `line`, `column`, and `suggestion`.

## v0.2.0

- Added explicit modules and aliased imports.
- Added enums, `Option<T>`, and `Result<T, E>` type references.
- Added pure `fn` boundary checks and stricter store checks.
- Added `slc fmt`, `slc doctor`, `slc init`, `slc new api`, and `slc add route`.
- Added Todo and Issue Tracker examples.
