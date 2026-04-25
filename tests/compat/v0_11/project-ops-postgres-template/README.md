# ProjectOpsPostgresTemplate

Run `slc check src/app.sl`.
Run `slc test src/app.sl`.
Run `slc schema src/app.sl --out build/schema.json`.
Run `slc migrate plan src/app.sl --db postgresql://localhost/symboliclight`.
Install `symboliclight[postgres]` before running the generated app against Postgres.
