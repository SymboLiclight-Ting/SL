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
- source-map behavior beyond generated comments,
- standard library APIs beyond SQLite, CLI, JSON HTTP, and tests.
