import importlib.util
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("playground_server", ROOT / "playground" / "server.py")
assert SPEC is not None and SPEC.loader is not None
playground_server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(playground_server)
compile_source = playground_server.compile_source
PlaygroundHandler = playground_server.PlaygroundHandler


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


def test_playground_compile_source_rejects_modules() -> None:
    result = compile_source(
        """
module helpers {
  fn ok() -> Bool {
    return true
  }
}
"""
    )

    assert result["ok"] is False
    assert any("only compile app files" in item["message"] for item in result["diagnostics"])


def test_playground_post_malformed_json_returns_400() -> None:
    class HandlerForTest(PlaygroundHandler):
        def __init__(self) -> None:
            self.path = "/compile"
            self.headers = {"Content-Length": "1"}
            self.rfile = io.BytesIO(b"{")
            self.wfile = io.BytesIO()
            self.status = None
            self.response_headers = []

        def send_response(self, code, message=None):  # noqa: ANN001
            self.status = code

        def send_header(self, keyword, value):  # noqa: ANN001
            self.response_headers.append((keyword, value))

        def end_headers(self):
            pass

    handler = HandlerForTest()

    handler.do_POST()

    assert handler.status == 400
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["ok"] is False
    assert "Malformed JSON" in payload["diagnostics"][0]["message"]
