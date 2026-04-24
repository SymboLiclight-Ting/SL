# Release Checklist

- Run `pytest`.
- Run `slc check examples/todo_app.sl`.
- Run `slc build examples/todo_app.sl --out build/todo_app.py`.
- Run `python -m py_compile build/todo_app.py`.
- Run `python build/todo_app.py test`.
- Run generated CLI add/list commands with a temporary SQLite database.
- Confirm README quick start matches actual CLI behavior.
