from pathlib import Path
import py_compile

from symboliclight.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_cli_check_build_and_test(tmp_path: Path) -> None:
    source = ROOT / "examples" / "todo_app.sl"
    output = tmp_path / "todo_app.py"

    assert main(["check", str(source)]) == 0
    assert main(["build", str(source), "--out", str(output)]) == 0
    py_compile.compile(str(output), doraise=True)
    assert main(["test", str(source)]) == 0


def test_cli_fmt_doctor_init_new_and_add_route(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "tiny.sl"
    source.write_text(
        'app Tiny { type Item = { id: Id<Item>, title: Text, } store items: Item route GET "/items" -> List<Item> { return items.all() } }',
        encoding="utf-8",
    )

    assert main(["fmt", str(source)]) == 0
    assert main(["fmt", str(source), "--check"]) == 0
    assert main(["doctor", str(source)]) == 0
    assert main(["add", "route", "GET", "/health", str(source)]) == 0

    project = tmp_path / "demo"
    assert main(["init", str(project)]) == 0
    assert (project / "app.sl").exists()

    monkeypatch.chdir(tmp_path)
    assert main(["new", "api", "sample"]) == 0
    assert (tmp_path / "sample.sl").exists()
