from __future__ import annotations

import contextlib
import io
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symboliclight.cli import main
from symboliclight.codegen import generate_schema_hash
from symboliclight.parser import parse_source


APP_SOURCE = """
app DriftSmoke {
  type Item = {
    id: Id<Item>,
    title: Text,
    done: Bool,
  }

  store items: Item
}
"""


def main_smoke() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "app.sl"
        database_path = root / "app.sqlite"
        source.write_text(APP_SOURCE, encoding="utf-8")
        app = parse_source(APP_SOURCE, path=str(source))
        database = sqlite3.connect(database_path)
        try:
            database.execute("CREATE TABLE sl_migrations (version INTEGER PRIMARY KEY, schema_hash TEXT NOT NULL)")
            database.execute(
                "INSERT INTO sl_migrations (version, schema_hash) VALUES (1, ?)",
                [generate_schema_hash(app)],
            )
            database.execute('CREATE TABLE "items" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "title" TEXT)')
            database.commit()
        finally:
            database.close()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["doctor", str(source), "--db", str(database_path)])
        report = output.getvalue()
        if status != 0:
            print(report)
            return status
        required = [
            "schema drift: structural drift detected",
            "schema diff: missing column items.done",
        ]
        missing = [line for line in required if line not in report]
        if missing:
            print(report)
            print("doctor drift smoke failed; missing expected output:")
            for line in missing:
                print(f"- {line}")
            return 1
    print("ok - doctor drift smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())
