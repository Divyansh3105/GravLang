"""
GravLang — Custom error classes.

All GravLang errors carry a human-readable message, the source line number
where the error was detected, and optionally the source code of that line.
"""


class GravLangError(Exception):
    """Base exception for every error raised by the GravLang toolchain."""

    def __init__(self, message: str, line: int | None = None, source_line: str = ""):
        self.message = message
        self.line = line
        self.source_line = source_line
        super().__init__(self._format())

    def _format(self) -> str:
        base = f"[Line {self.line}] {self.message}" if self.line else self.message
        if self.source_line:
            base += f"\n    {self.source_line}"
        return base


class LexerError(GravLangError):
    """Raised by the lexer when it encounters an illegal character or token."""

    def __init__(self, message: str, line: int | None = None, source_line: str = ""):
        super().__init__(f"Lexer Error: {message}", line, source_line)


class ParseError(GravLangError):
    """Raised by the parser on a syntax error."""

    def __init__(self, message: str, line: int | None = None, source_line: str = ""):
        super().__init__(f"Parse Error: {message}", line, source_line)


class GravLangRuntimeError(GravLangError):
    """Raised by the interpreter at runtime."""

    def __init__(self, message: str, line: int | None = None, source_line: str = ""):
        super().__init__(f"Runtime Error: {message}", line, source_line)


# ── Flow-control signals (NOT errors — never shown to users) ────────

class BreakSignal(Exception):
    """Raised by 'break' to exit the nearest enclosing loop."""
    pass


class ContinueSignal(Exception):
    """Raised by 'continue' to skip to the next loop iteration."""
    pass
