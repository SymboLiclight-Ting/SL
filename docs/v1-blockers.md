# v1.0 Completion Checklist

This list tracks what must remain true for SL v1.0 to stay release-ready locally.

## Blockers

- Freeze the public `.sl` grammar listed in `docs/freeze-candidate.md`.
- Keep compatibility fixtures for all supported v0.6 and later examples passing.
- Make docs, examples, and generated Python behavior agree for every public command.
- Keep local wheel smoke checks passing from a fresh tag checkout.
- Keep public package upload as an explicit owner decision.

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
