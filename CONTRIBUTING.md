# Contributing

Thank you for helping improve SymbolicLight.

Before opening a pull request:

```bash
pip install -e ".[dev]"
pytest -q
python -m compileall -q src playground scripts
python scripts/release_check.py --skip-package
```

Keep changes small and focused. Syntax changes must update `docs/spec.md`, tests, and examples together.

Use `SL`, `slc`, and `.sl` in developer-facing docs. Use `SymbolicLight` as the formal project name.
