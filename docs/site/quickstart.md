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

Try the 10-minute path:

1. Run `slc check examples/todo_app.sl`.
2. Build with `slc build examples/todo_app.sl --out build/todo_app.py`.
3. Open `examples/todo_app.sl`, add or edit a route, then run `slc test examples/todo_app.sl`.
4. Inspect `build/todo_app.py` to see the generated Python.

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

Create a new API project:

```bash
slc new api my-api --template todo --backend sqlite
slc check my-api/src/app.sl
```
