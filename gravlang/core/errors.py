"""
GravLang — Custom error classes.

All GravLang errors carry a human-readable message, the source line number
where the error was detected, and optionally the source code of that line.
"""


class GravLangError(Exception):
    """Base exception for every error raised by the GravLang toolchain."""

    kind = ""  # display prefix, e.g. "Runtime Error"; kept out of .message

    def __init__(self, message: str, line: int | None = None, source_line: str = ""):
        self.message = message
        self.line = line
        self.source_line = source_line
        super().__init__(self._format())

    def _format(self) -> str:
        msg = f"{self.kind}: {self.message}" if self.kind else self.message
        base = f"[Line {self.line}] {msg}" if self.line else msg
        if self.source_line:
            base += f"\n    {self.source_line}"
        return base


class LexerError(GravLangError):
    """Raised by the lexer when it encounters an illegal character or token."""

    kind = "Lexer Error"


class ParseError(GravLangError):
    """Raised by the parser on a syntax error."""

    kind = "Parse Error"


class GravLangRuntimeError(GravLangError):
    """Raised by the interpreter at runtime."""

    kind = "Runtime Error"


# ── Flow-control signals (NOT errors — never shown to users) ────────

class BreakSignal(Exception):
    """Raised by 'break' to exit the nearest enclosing loop."""
    pass


class ContinueSignal(Exception):
    """Raised by 'continue' to skip to the next loop iteration."""
    pass


class ExecutionStopped(Exception):
    """Raised by the IDE to abort a run; not a GravLangError, so user catch blocks can't swallow it."""
    pass
