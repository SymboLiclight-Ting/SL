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
- IntentSpec acceptance execution,
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
