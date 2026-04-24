# Notes API

This example demonstrates typed request bodies, `Response<T>`, fixtures, golden tests, and schema generation.

```bash
slc check app.sl
slc schema app.sl --out build/schema.json
slc build app.sl --out build/notes_api.py
python build/notes_api.py test
```
