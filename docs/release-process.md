# Release Process

This project uses local release candidates before any public package upload.

Recommended process:

```bash
pytest -q
python -m compileall -q src playground scripts
python scripts/release_check.py
git tag v0.11.0-rc1
python scripts/release_check.py
```

For a fresh tag rehearsal, create a detached worktree from the tag and run `python scripts/release_check.py` there.

Uploading to TestPyPI or PyPI is optional and must be an explicit project-owner decision.
