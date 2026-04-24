from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from symboliclight.checker import check_program_result
from symboliclight.codegen import generate_python
from symboliclight.diagnostics import Diagnostic
from symboliclight.parser import parse_source_result


ROOT = Path(__file__).resolve().parent


def compile_source(source: str) -> dict[str, object]:
    result = parse_source_result(source, path="<playground>")
    diagnostics: list[Diagnostic] = list(result.diagnostics)
    if result.unit is not None and not any(item.severity == "error" for item in diagnostics):
        diagnostics.extend(check_program_result(result.unit, source_path=Path("<playground>")).diagnostics)
    if result.unit is None or any(item.severity == "error" for item in diagnostics):
        return {"ok": False, "diagnostics": [item.to_dict() for item in diagnostics]}
    return {"ok": True, "python": generate_python(result.unit), "diagnostics": [item.to_dict() for item in diagnostics]}


class PlaygroundHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        content = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path != "/compile":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        response = json.dumps(compile_source(str(payload.get("source", "")))).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), PlaygroundHandler)
    print("SL playground running at http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
