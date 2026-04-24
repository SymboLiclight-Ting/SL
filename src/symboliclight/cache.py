from __future__ import annotations

import hashlib
import json
from pathlib import Path

from symboliclight.diagnostics import Diagnostic

CACHE_VERSION = "check-v1"


def source_hash(source: str) -> str:
    digest = hashlib.sha256()
    digest.update(CACHE_VERSION.encode("utf-8"))
    digest.update(source.encode("utf-8"))
    return digest.hexdigest()


def write_check_cache(source_path: Path, source: str, diagnostics: list[Diagnostic]) -> Path:
    cache_dir = source_path.parent / ".slcache" / "check"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{source_hash(source)}.json"
    payload = {
        "version": CACHE_VERSION,
        "source": str(source_path),
        "diagnostics": [
            {
                "message": diagnostic.message,
                "severity": diagnostic.severity,
                "line": diagnostic.location.line,
                "column": diagnostic.location.column,
                "suggestion": diagnostic.suggestion,
            }
            for diagnostic in diagnostics
        ],
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cache_path
