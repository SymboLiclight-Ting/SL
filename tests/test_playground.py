import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("playground_server", ROOT / "playground" / "server.py")
assert SPEC is not None and SPEC.loader is not None
playground_server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(playground_server)
compile_source = playground_server.compile_source


def test_playground_compile_source_success() -> None:
    result = compile_source(
        """
app Demo {
  route GET "/hello" -> Text {
    return "hello"
  }
}
"""
    )

    assert result["ok"] is True
    assert "def route_get_hello" in result["python"]


def test_playground_compile_source_diagnostics() -> None:
    result = compile_source(
        """
app Demo {
  store items: Missing
}
"""
    )

    assert result["ok"] is False
    assert any("Missing" in item["message"] for item in result["diagnostics"])
