# Quickstart

Install for local development:

```bash
pip install -e ".[dev]"
```

Check and build the Todo example:

```bash
slc check examples/todo_app.sl
slc build examples/todo_app.sl --out build/todo_app.py
python build/todo_app.py test
python build/todo_app.py add "Buy milk"
python build/todo_app.py list
```

Generate schema and run doctor:

```bash
slc schema examples/todo_app.sl --out build/todo_schema.json
slc doctor examples/todo_app.sl
slc doctor examples/todo_app.sl --json
```

Run the full local release gate:

```bash
python scripts/release_check.py
```

