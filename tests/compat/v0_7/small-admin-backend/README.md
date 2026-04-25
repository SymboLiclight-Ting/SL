# Small Admin Backend

This v0.7 gallery example validates SL against a more realistic backend shape.

It covers:

- typed config through `env` and `env_int`
- multiple SQLite stores
- multiple CLI commands
- authenticated HTTP routes through `request.header`
- typed request bodies
- IntentSpec route, command, permission, and acceptance alignment
- schema drift inspection through `slc doctor --db`

Run:

```bash
slc check app.sl
slc test app.sl
slc schema app.sl --out build/schema.json
slc build app.sl --out build/admin.py
python build/admin.py create_admin Ada ada@example.com
ADMIN_TOKEN=dev-token python build/admin.py serve
slc doctor app.sl --db admin.sqlite
```
