# Todo API + CLI

This example demonstrates the smallest useful SL application shape: records, SQLite store, CLI commands, HTTP routes, and an inline test.

```bash
slc check app.sl
slc build app.sl --out build/todo_app.py
python build/todo_app.py test
python build/todo_app.py add "Buy milk"
python build/todo_app.py list
```
