from __future__ import annotations

from dataclasses import dataclass

from symboliclight.diagnostics import Diagnostic, SourceLocation, SymbolicLightError

KEYWORDS = {
    "app",
    "module",
    "import",
    "as",
    "intent",
    "permissions",
    "from",
    "enum",
    "type",
    "config",
    "fn",
    "store",
    "fixture",
    "route",
    "body",
    "command",
    "test",
    "golden",
    "let",
    "return",
    "assert",
    "if",
    "else",
    "true",
    "false",
}


@dataclass(slots=True)
class Token:
    kind: str
    value: str
    location: SourceLocation


def lex(source: str, *, path: str = "<memory>") -> list[Token]:
    lexer = Lexer(source, path)
    return lexer.run()


class Lexer:
    def __init__(self, source: str, path: str) -> None:
        self.source = source
        self.path = path
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.diagnostics: list[Diagnostic] = []

    def run(self) -> list[Token]:
        while self.peek() is not None:
            char = self.peek()
            if char is not None and char.isspace():
                self.advance()
                continue
            if char == "/" and self.peek_next() == "/":
                self.skip_comment()
                continue
            if char is not None and (char.isalpha() or char == "_"):
                self.lex_identifier()
                continue
            if char is not None and char.isdigit():
                self.lex_number()
                continue
            if char == '"':
                self.lex_string()
                continue
            self.lex_symbol()

        self.tokens.append(Token("eof", "", self.location()))
        if self.diagnostics:
            raise SymbolicLightError(self.diagnostics)
        return self.tokens

    def lex_identifier(self) -> None:
        start = self.location()
        value = ""
        while (char := self.peek()) is not None and (char.isalnum() or char == "_"):
            value += char
            self.advance()
        self.tokens.append(Token("keyword" if value in KEYWORDS else "ident", value, start))

    def lex_number(self) -> None:
        start = self.location()
        value = ""
        seen_dot = False
        while (char := self.peek()) is not None:
            if char.isdigit():
                value += char
                self.advance()
            elif char == "." and not seen_dot and (self.peek_next() or "").isdigit():
                seen_dot = True
                value += char
                self.advance()
            else:
                break
        self.tokens.append(Token("number", value, start))

    def lex_string(self) -> None:
        start = self.location()
        self.advance()
        value = ""
        while (char := self.peek()) is not None:
            if char == '"':
                self.advance()
                self.tokens.append(Token("string", value, start))
                return
            if char == "\\":
                self.advance()
                escaped = self.peek()
                if escaped == "n":
                    value += "\n"
                elif escaped == '"':
                    value += '"'
                elif escaped is not None:
                    value += escaped
                if escaped is not None:
                    self.advance()
                continue
            value += char
            self.advance()
        self.diagnostics.append(
            Diagnostic("Unterminated string literal.", start, "Close the string with a double quote.")
        )

    def lex_symbol(self) -> None:
        start = self.location()
        char = self.advance()
        assert char is not None
        pair = char + (self.peek() or "")
        if pair in {"->", "==", "!=", "<=", ">=", "&&", "||"}:
            self.advance()
            self.tokens.append(Token("symbol", pair, start))
            return
        if char in "{}()[],:.<>+-*/=":
            self.tokens.append(Token("symbol", char, start))
            return
        self.diagnostics.append(
            Diagnostic(f"Unexpected character `{char}`.", start, "Remove it or add it to the lexer.")
        )

    def skip_comment(self) -> None:
        while (char := self.peek()) is not None:
            self.advance()
            if char == "\n":
                break

    def peek(self) -> str | None:
        if self.index >= len(self.source):
            return None
        return self.source[self.index]

    def peek_next(self) -> str | None:
        if self.index + 1 >= len(self.source):
            return None
        return self.source[self.index + 1]

    def advance(self) -> str | None:
        char = self.peek()
        if char is None:
            return None
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def location(self) -> SourceLocation:
        return SourceLocation(self.path, self.line, self.column)
