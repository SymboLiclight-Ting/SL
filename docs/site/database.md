# Database

SL stores compile to SQLite tables.

Generated apps record a schema hash in `sl_migrations`, but v0.x does not automatically migrate data.

Inspect a database:

```bash
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite --json
```

Doctor separates metadata drift from structural diff:

- `schema drift: up to date` means the stored hash matches.
- `schema drift: structural drift detected` means the stored hash matches but the actual table structure differs.
- `schema drift: drift detected` means the stored hash differs.
- `schema diff: no structural difference detected` means the inspected table structure matches.

