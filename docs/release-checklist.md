# Release Checklist

- Run `pytest`.
- Run `python -m compileall -q src playground`.
- Run `slc check examples/todo_app.sl`.
- Run `slc check --json examples/todo_app.sl`.
- Run `slc build examples/todo_app.sl --out build/todo_app.py`.
- Run `python -m py_compile build/todo_app.py`.
- Run `python build/todo_app.py test`.
- Run gallery `slc check/build/test/schema/doctor` smoke checks.
- Run generated CLI add/list commands with a temporary SQLite database.
- Confirm README quick start matches actual CLI behavior.
- Confirm `slc lsp --help` is available.
