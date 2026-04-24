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

Next focus:

- better parser recovery with multiple diagnostics per file,
- source-map helpers that turn Python exceptions into `.sl` locations,
- richer route body typing,
- more complete `Option` and `Result` control-flow ergonomics,
- incremental check cache reuse instead of write-only cache metadata.

## v0.4 Standard App Kit

Target standard capabilities:

- typed `Request<T>` and `Response<T>`,
- richer SQLite helpers and migration metadata,
- JSON schema generation,
- fixtures and golden tests,
- typed config and `.env`,
- thin `time`, `uuid`, `path`, and `file` standard wrappers,
- `slc doctor` checks for IntentSpec routes, commands, permissions, and acceptance coverage.

## v0.5 Public Developer Preview

Developer experience:

- VS Code syntax package,
- initial LSP diagnostics, hover, definitions, document symbols, and formatting,
- example gallery,
- local playground that shows `.sl` input, generated Python, and diagnostics,
- three complete sample apps.

## v0.8 Ecosystem Hardening

- five sample applications,
- PyPI release flow,
- changelog and migration fixtures,
- documentation site,
- compatibility test suite across prior examples.

## v1.0 Stable

- syntax freeze,
- core standard library stability,
- stable CLI behavior,
- documented compatibility guarantees,
- real project case studies.
