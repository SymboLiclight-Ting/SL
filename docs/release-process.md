# Release Process

This project prepares local release artifacts before any public package upload. Uploading to GitHub, TestPyPI, or PyPI is optional and must be an explicit project-owner decision.

Recommended process:

```bash
pytest -q
python -m compileall -q src playground scripts
python scripts/docs_check.py
python scripts/vscode_check.py
python scripts/freeze_check.py
python scripts/example_matrix.py
python scripts/release_check.py
python scripts/release_notes.py --from v0.13.0-rc2 --to HEAD --out build/release-notes-v1.0.0.md
git tag v1.0.0
python scripts/release_check.py
```

For a fresh tag rehearsal, create a detached worktree from the tag and run `python scripts/release_check.py` there.

The local v1.0 process produces `dist/symboliclight-1.0.0.tar.gz`, `dist/symboliclight-1.0.0-py3-none-any.whl`, release notes, and an announcement draft. Do not push tags or upload packages unless the owner explicitly asks for that step.
