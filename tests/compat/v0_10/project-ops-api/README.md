# Project Ops API

This v0.10 gallery app validates production-app-kit behavior:

- SQLite fallback app in `app.sl`
- Postgres backend codegen in `app_postgres.sl`
- typed config through `env`
- explicit auth helper through `request.header`
- multiple stores, commands, and routes
- `Response<Result<T, ErrorBody>>` through `response_ok` and `response_err`
- migration planning through `slc migrate plan`

Useful commands:

```bash
slc check app.sl
slc test app.sl
slc schema app.sl --out build/project_ops_schema.json
slc doctor app.sl
slc migrate plan app.sl --db build/project_ops.sqlite
slc check app_postgres.sl
slc build app_postgres.sl --out build/project_ops_postgres.py
slc migrate plan app_postgres.sl --db postgresql://localhost/symboliclight
```
