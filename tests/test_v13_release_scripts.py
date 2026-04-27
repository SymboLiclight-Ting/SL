import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_freeze_check_passes() -> None:
    completed = run_script("freeze_check.py")

    assert completed.returncode == 0, completed.stderr
    assert "stable surface check passed" in completed.stdout


def test_example_matrix_passes() -> None:
    completed = run_script("example_matrix.py")

    assert completed.returncode == 0, completed.stderr
    assert "example matrix check passed" in completed.stdout
