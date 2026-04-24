# Contributing

SymbolicLight is currently an MVP application language compiler.

Before changing language behavior:

1. Update `docs/spec.md`.
2. Update `examples/todo_app.sl` if the golden syntax changes.
3. Add or update tests.
4. Run `pytest`.
5. Build and run the generated Todo app.

Keep changes small and focused. Generated Python should remain readable and standard-library based unless there is a documented reason to add a dependency.
