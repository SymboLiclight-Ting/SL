# Changelog

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
