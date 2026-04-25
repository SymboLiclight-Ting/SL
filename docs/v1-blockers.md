# v1.0 Blocker List

This list is the v0.13 release-candidate gate for deciding what must happen before SymbolicLight can become v1.0.

## Blockers

- Freeze the public `.sl` grammar listed in `docs/freeze-candidate.md`.
- Keep compatibility fixtures for all supported v0.6 and later examples passing.
- Make docs, examples, and generated Python behavior agree for every public command.
- Keep local wheel smoke checks passing from a fresh tag checkout.
- Decide the official PyPI/TestPyPI publication policy.

## Nice To Have Before v1.0

- More LSP hover coverage for complex expressions.
- Additional real-world sample apps.
- More detailed migration-plan suggestions.
- Better docs navigation if a static site generator is later selected.

## Explicitly Deferred

- automatic migration execution,
- production-grade HTTP hosting,
- auth middleware and session management,
- native compiler,
- package registry,
- macro system.
