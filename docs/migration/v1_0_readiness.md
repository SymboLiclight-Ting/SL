# v1.0 Readiness Notes

This document tracks the compatibility work that moved the v0.13 release-candidate surface into the SL v1.0 local stable baseline.

## Must Be Stable Before v1.0

- `.sl` top-level item grammar,
- store helper signatures,
- route declaration syntax,
- `Option<T>`, `Result<T, E>`, and `Response<T>` behavior,
- diagnostics JSON,
- `slc doctor --json`,
- `slc migrate plan --json`,
- generated HTTP error envelope,
- CLI exit codes.

## Must Be Documented Before v1.0

- which v0.x behaviors are experimental,
- which generated Python details are not API,
- how compatibility fixtures are added,
- how breaking changes are approved,
- how TestPyPI or PyPI publication is authorized.

## Explicitly Deferred Beyond v1.0

- automatic destructive migrations,
- package registry,
- production HTTP process management,
- full ORM or query builder,
- macro system,
- native compiler.
