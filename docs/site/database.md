# Database

SL stores compile to SQLite tables by default. v0.10 also supports Postgres-backed stores with `using postgres` when the optional `symboliclight[postgres]` dependency is installed.

Generated apps record a schema hash in `sl_migrations`, but v0.x does not automatically migrate data.

Inspect a database:

```bash
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite --json
slc migrate plan examples/gallery/project-ops-api/app.sl --db build/project_ops.sqlite
slc migrate plan examples/gallery/project-ops-api/app_postgres.sl --db postgresql://localhost/symboliclight
```

Doctor separates metadata drift from structural diff:

- `schema drift: up to date` means the stored hash matches.
- `schema drift: structural drift detected` means the stored hash matches but the actual table structure differs.
- `schema drift: drift detected` means the stored hash differs.
- `schema diff: no structural difference detected` means the inspected table structure matches.

Migration plans are read-only in v0.12. SL reports missing tables, extra tables, missing columns, extra columns, and type mismatches, but it does not execute SQL changes or generate destructive migration commands.

Generated SQLite and Postgres store helpers wrap driver failures with operation names such as `database items.insert failed`. HTTP routes map uncaught database failures to a stable `500` JSON error response while keeping detailed tracebacks on stderr for local debugging.
