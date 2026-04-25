# Compatibility Policy

SymbolicLight is currently in the `v0.x` experimental period.

## v0.x

Breaking changes are allowed when they improve the core language shape, but every breaking change must update:

- `docs/spec.md`
- `docs/semantics.md`
- examples
- tests
- changelog or migration notes when a release is cut

The compiler should reject old syntax with actionable diagnostics whenever practical.

## v1.0

After `v1.0`, the following surfaces are considered stable:

- core syntax,
- type names and generic arity,
- store method names and signatures,
- CLI command behavior,
- generated Python runtime contract,
- formatter output.

Breaking changes after `v1.0` require a documented migration path.

## Current Stability

Stable enough to build examples:

- `app`
- `module`
- `import "./file.sl" as alias`
- `type`
- `enum`
- `store`
- `fn`
- `command`
- `route`
- `test`

Still experimental:

- `Result<T, E>` expression ergonomics,
- IntentSpec acceptance execution beyond the v0.6 offline bridge,
- permissions enforcement,
- source-map behavior beyond v0.3 sidecar maps and best-effort runtime backreferences,
- standard library APIs beyond SQLite, CLI, JSON HTTP, and tests.

## v0.3 Notes

v0.3 keeps v0.2 syntax intact and tightens behavior:

- duplicate import aliases are rejected,
- import aliases may not collide with local declarations,
- function and command named arguments are checked,
- record literal duplicate fields are rejected,
- route return types must be JSON encodable,
- `slc check` may reuse `.slcache/` diagnostics unless `--no-cache` is used,
- `slc build` emits `.slmap.json` by default unless `--no-source-map` is used.

These checks may reject programs that previously compiled accidentally.

## v0.4 Notes

v0.4 adds the Standard App Kit while keeping v0.3 programs valid:

- routes may declare typed request bodies with `body TypeName`,
- `GET body TypeName` is rejected,
- `Response<T>` is supported through the `response` built-in,
- store helpers now include `count`, `exists`, and test-only `clear`,
- `fixture`, golden tests, and typed `config` are new app-level syntax,
- `slc schema` is a new CLI command,
- generated Python records schema drift metadata but does not migrate data.

These additions are experimental until `v1.0`.

## v0.5 Notes

v0.5 is a public developer preview focused on tooling:

- `slc lsp` is additive and experimental,
- `slc init` and `slc new api` now generate project directories with `src/app.sl` and `intent/*.intent.yaml`,
- `slc add route` is stricter and refuses to edit files with `//` comments or parser errors,
- VS Code, playground, and gallery files are developer-preview assets and are not v1.0 compatibility commitments.

## v0.6 Notes

v0.6 hardens release and IntentSpec alignment without changing `.sl` syntax:

- `slc doctor` reads optional `# sl:` hints in IntentSpec files,
- doctor reports route, command, and permission alignment gaps as report lines, not compiler errors,
- `slc test` runs the v0.6 offline IntentSpec acceptance bridge when `test from intent.acceptance` is declared,
- `scripts/release_check.py` centralizes release smoke commands,
- the Customer Brief Generator gallery example is additive.

## v0.7 Notes

v0.7 validates SL against a more realistic backend while keeping syntax changes minimal:

- `request.header(name: Text) -> Option<Text>` is additive and route-only,
- `slc doctor --db path/to/app.sqlite` is additive and read-only,
- schema drift inspection reports status but does not migrate data,
- the Small Admin Backend gallery example is additive.

## v0.8 Notes

v0.8 continues real-app hardening without broad syntax expansion:

- `try_update(id, record) -> Option<T>` is additive and does not change `update(id, record) -> T`,
- `response_ok` and `response_err` are additive built-ins; `response(...)` behavior is unchanged,
- `slc doctor --db` adds read-only summary schema diff lines and still never mutates application databases,
- the Small Admin Backend gallery now demonstrates an explicit auth helper and `ErrorBody` response pattern.

## v0.9 Notes

v0.9 stabilizes developer experience without changing `.sl` core syntax:

- `slc fmt` now preserves common `//` comment trivia instead of refusing commented files,
- `slc doctor --json` adds a machine-readable doctor report while preserving text output,
- LSP hover, definition, document symbols, and formatting are broader but remain developer-preview surfaces,
- compatibility fixtures under `tests/compat/` preserve representative v0.6, v0.7, and v0.8 example behavior,
- docs site Markdown files under `docs/site/` are documentation source material and do not introduce a site generator commitment.

## v0.10 Notes

v0.10 adds production app kit surfaces while preserving existing SQLite apps:

- `store name: Type using sqlite` and `using postgres` are additive; omitted backend remains `sqlite`,
- one app may use only one store backend in v0.10,
- Postgres runtime support is optional through `symboliclight[postgres]`; default installs do not gain a mandatory database driver,
- `slc migrate plan` is additive and read-only,
- migration planning and `doctor --db` do not execute SQL changes and do not mutate user databases,
- `project-ops-api` is an additive gallery example for production-app-kit validation.

## v0.11 Notes

v0.11 is an ecosystem preview and does not add core `.sl` syntax:

- `slc new api <name>` keeps its existing default behavior,
- `slc new api --template ... --backend ...` is additive,
- `postgres` template generation is limited to the Project Ops starter,
- docs, VS Code, release notes, and GitHub metadata are project assets, not v1.0 compatibility commitments,
- v0.10 Project Ops is frozen as a compatibility fixture.
