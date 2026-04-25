# Changelog

## v0.12.0rc1

- Added beta hardening for generated HTTP errors, including stable JSON envelopes and a fixed request body limit.
- Added runtime guards for `read_text` and `write_text` empty paths and directory paths.
- Wrapped generated store helper database exceptions with stable operation names.
- Added CLI exit code coverage for compiler, runtime, doctor, migrate, project generation, formatter, and argparse failures.
- Added Windows, macOS, Linux and Python 3.11/3.12 CI matrix coverage.
- Added v0.11 compatibility fixtures and beta release smoke script improvements.
- Added v0.12 security review documentation.

## v0.11.0rc1

- Added ecosystem preview docs, contribution guidance, security policy, and GitHub issue/CI templates.
- Added `slc new api --template ... --backend ...` for Todo, Notes, Admin, and Project Ops starter apps.
- Added docs, VS Code extension, and release notes maintenance checks.
- Added v0.10 Project Ops compatibility fixtures.
- Updated package and VS Code preview versions for the v0.11 release candidate.

## v0.10.0rc1

- Added explicit store backend clauses with `using sqlite` and `using postgres`.
- Added optional Postgres runtime support through `symboliclight[postgres]`.
- Added read-only `slc migrate plan` text and JSON output.
- Extended generated CRUD helpers and schema inspection for Postgres-backed apps.
- Added the Project Ops API gallery example with SQLite fallback and Postgres codegen coverage.
- Updated release smoke checks to include migration-plan and Project Ops API coverage.

## v0.9.0rc2

- Aligned the release candidate package version with the `v0.9.0-rc2` tag.
- Polished v0.9 review diagnostics so release-facing messages no longer mention older v0.8 wording.
- Updated the full development plan to mark v0.9 DX Stabilization as complete and v0.10 as the next stage.

## v0.9.0rc1

- Added comment-preserving formatting for common `//` comment positions.
- Added `slc doctor --json` for machine-readable doctor output.
- Extended LSP hover, definition, document symbols, and formatting coverage.
- Added compatibility fixtures for representative v0.6, v0.7, and v0.8 applications.
- Added a Markdown documentation site skeleton under `docs/site/`.
- Updated release smoke checks to include compatibility fixtures.

## v0.8.0

- Added read-only summary schema diff output to `slc doctor --db`.
- Added `try_update(id, record) -> Option<T>` for stores.
- Added `response_ok` and `response_err` helpers for `Response<Result<...>>`.
- Updated Small Admin Backend to use an explicit auth helper and unified `ErrorBody` responses.
- Stabilized release-facing schema drift and schema diff wording.
- Added a release smoke fixture for hash-matched databases with structural drift.
- Clarified that `ErrorBody` is a recommended pattern; custom error record names with `code: Text` and `message: Text` are supported.

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
