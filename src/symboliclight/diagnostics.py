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

    def format(self) -> str:
        prefix = f"{self.location.path}:{self.location.line}:{self.location.column}"
        rendered = f"{prefix}: {self.severity}: {self.message}"
        if self.suggestion:
            rendered += f"\n  suggestion: {self.suggestion}"
        return rendered


class SymbolicLightError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("\n".join(diagnostic.format() for diagnostic in diagnostics))
        self.diagnostics = diagnostics


def raise_if_errors(diagnostics: list[Diagnostic]) -> None:
    errors = [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    if errors:
        raise SymbolicLightError(errors)
