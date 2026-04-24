from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from symboliclight.diagnostics import Diagnostic

CACHE_VERSION = "check-v2"


@dataclass(slots=True)
class CachedCheck:
    diagnostics: list[Diagnostic]
    dependency_paths: set[Path]
    cache_path: Path


def source_hash(source: str, *, strict_intent: bool = False) -> str:
    digest = hashlib.sha256()
    digest.update(CACHE_VERSION.encode("utf-8"))
    digest.update(f"strict_intent={strict_intent}".encode("utf-8"))
    digest.update(source.encode("utf-8"))
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def cache_path_for(source_path: Path, source: str, *, strict_intent: bool) -> Path:
    cache_dir = source_path.parent / ".slcache" / "check"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{source_hash(source, strict_intent=strict_intent)}.json"


def read_check_cache(source_path: Path, source: str, *, strict_intent: bool) -> CachedCheck | None:
    cache_path = cache_path_for(source_path, source, strict_intent=strict_intent)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("version") != CACHE_VERSION:
        return None
    if payload.get("strict_intent") != strict_intent:
        return None
    dependency_hashes = payload.get("dependency_hashes", {})
    if not isinstance(dependency_hashes, dict):
        return None
    missing_dependency_paths = payload.get("missing_dependency_paths", [])
    if not isinstance(missing_dependency_paths, list):
        return None
    for raw_path in missing_dependency_paths:
        if Path(str(raw_path)).exists():
            return None
    dependency_paths: set[Path] = set()
    for raw_path, expected_hash in dependency_hashes.items():
        path = Path(str(raw_path))
        if not path.exists():
            return None
        try:
            actual_hash = file_hash(path)
        except OSError:
            return None
        if actual_hash != expected_hash:
            return None
        dependency_paths.add(path)
    diagnostics_payload = payload.get("diagnostics", [])
    if not isinstance(diagnostics_payload, list):
        return None
    return CachedCheck(
        [Diagnostic.from_dict(item) for item in diagnostics_payload if isinstance(item, dict)],
        dependency_paths,
        cache_path,
    )


def write_check_cache(
    source_path: Path,
    source: str,
    diagnostics: list[Diagnostic],
    *,
    dependency_paths: set[Path] | None = None,
    missing_dependency_paths: set[Path] | None = None,
    strict_intent: bool = False,
) -> Path:
    cache_path = cache_path_for(source_path, source, strict_intent=strict_intent)
    dependencies = sorted(str(path.resolve()) for path in (dependency_paths or set()))
    missing_dependencies = sorted(str(path.resolve()) for path in (missing_dependency_paths or set()))
    payload = {
        "version": CACHE_VERSION,
        "source": str(source_path.resolve()),
        "strict_intent": strict_intent,
        "dependency_paths": dependencies,
        "missing_dependency_paths": missing_dependencies,
        "dependency_hashes": {path: file_hash(Path(path)) for path in dependencies},
        "diagnostics": [diagnostic.to_dict() for diagnostic in diagnostics],
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cache_path
