from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SourceLocation:
    path: str
    line: int
    column: int


@dataclass(slots=True)
class Diagnostic:
    message: str
    location: SourceLocation
    suggestion: str = ""
    severity: str = "error"
    code: str = "SL000"

    def format(self) -> str:
        prefix = f"{self.location.path}:{self.location.line}:{self.location.column}"
        rendered = f"{prefix}: {self.severity} {self.code}: {self.message}"
        if self.suggestion:
            rendered += f"\n  suggestion: {self.suggestion}"
        return rendered

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "file": self.location.path,
            "line": self.location.line,
            "column": self.location.column,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Diagnostic":
        return cls(
            str(payload.get("message", "")),
            SourceLocation(
                str(payload.get("file", payload.get("path", "<cache>"))),
                int(payload.get("line", 1)),
                int(payload.get("column", 1)),
            ),
            str(payload.get("suggestion", "")),
            str(payload.get("severity", "error")),
            str(payload.get("code", "SL000")),
        )


class SymbolicLightError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("\n".join(diagnostic.format() for diagnostic in diagnostics))
        self.diagnostics = diagnostics


def raise_if_errors(diagnostics: list[Diagnostic]) -> None:
    errors = [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    if errors:
        raise SymbolicLightError(errors)
