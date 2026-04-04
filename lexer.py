"""
GravLang — Lexer (tokenizer).

Converts raw source code into a flat list of Token objects using regex-based
scanning with named groups.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from errors import LexerError


# ── Token ────────────────────────────────────────────────────────────

@dataclass
class Token:
    type: str
    value: str
    line: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ── Token specification (order matters!) ─────────────────────────────

TOKEN_SPEC: list[tuple[str, str]] = [
    # Whitespace & comments (skipped)
    ("COMMENT",      r"#[^\n]*"),
    ("NEWLINE",      r"\n"),
    ("SKIP",         r"[ \t\r]+"),

    # Literals
    ("FLOAT",        r"\d+\.\d+"),
    ("INT",          r"\d+"),
    ("STRING",       r'"(?:[^"\\]|\\.)*"'),

    # Multi-character operators (must come before single-char variants)
    ("POWER",        r"\*\*"),          # ** (power)
    ("FLOORDIV_ASSIGN", r"//="),       # FIXED: //= (augmented floor-div)
    ("MOD_ASSIGN",   r"%="),           # FIXED: %= (augmented modulo)
    ("FLOORDIV",     r"//"),            # // (integer division)
    ("PLUS_ASSIGN",  r"\+="),           # += (augmented add)
    ("MINUS_ASSIGN", r"-="),            # -= (augmented sub)
    ("STAR_ASSIGN",  r"\*="),           # *= (augmented mul)
    ("SLASH_ASSIGN", r"/="),            # /= (augmented div)
    ("LE",           r"<="),
    ("GE",           r">="),
    ("EQ",           r"=="),
    ("NEQ",          r"!="),

    # Single-character operators & punctuation
    ("PLUS",         r"\+"),
    ("MINUS",        r"-"),
    ("STAR",         r"\*"),
    ("SLASH",        r"/"),
    ("MOD",          r"%"),
    ("LT",           r"<"),
    ("GT",           r">"),
    ("ASSIGN",       r"="),

    ("LPAREN",       r"\("),
    ("RPAREN",       r"\)"),
    ("LBRACE",       r"\{"),
    ("RBRACE",       r"\}"),
    ("LBRACKET",     r"\["),
    ("RBRACKET",     r"\]"),
    ("DOT",          r"\."),
    ("COLON",        r":"),
    ("COMMA",        r","),
    ("SEMI",         r";"),

    # Identifiers & keywords (matched last among visible tokens)
    ("ID",           r"[A-Za-z_][A-Za-z0-9_]*"),
]

# Keywords — if an ID matches one of these it becomes the keyword token.
KEYWORDS: dict[str, str] = {
    "let":      "LET",
    "if":       "IF",
    "elif":     "ELIF",
    "else":     "ELSE",
    "while":    "WHILE",
    "for":      "FOR",
    "func":     "FUNC",
    "return":   "RETURN",
    "true":     "TRUE",
    "false":    "FALSE",
    "and":      "AND",
    "or":       "OR",
    "not":      "NOT",
    "print":    "PRINT",
    "class":    "CLASS",
    "extends":  "EXTENDS",
    "self":     "SELF",
    # New keywords
    "break":    "BREAK",
    "continue": "CONTINUE",
    "null":     "NULL",
    "in":       "IN",
}

# Build master regex
_master_pattern = "|".join(
    f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC
)
_master_re = re.compile(_master_pattern)


# ── Lexer class ──────────────────────────────────────────────────────

class Lexer:
    """Tokenize GravLang source code."""

    def __init__(self, source: str):
        self.source = source
        self.source_lines = source.splitlines()  # stored for error messages

    def get_line(self, line_no: int) -> str:
        """Return the source text for a given 1-based line number."""
        if 1 <= line_no <= len(self.source_lines):
            return self.source_lines[line_no - 1]
        return ""

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        line = 1
        last_end = 0  # FIXED: track last match end for single-pass illegal char detection

        for mo in _master_re.finditer(self.source):
            # FIXED: check gap between last match end and current match start
            if mo.start() > last_end:
                gap = self.source[last_end:mo.start()]
                for i, ch in enumerate(gap):
                    if ch not in " \t\r\n":
                        pos = last_end + i
                        bad_line = self.source[:pos].count("\n") + 1
                        raise LexerError(
                            f"Unexpected character: {ch!r}", bad_line,
                            self.get_line(bad_line),
                        )
            last_end = mo.end()  # FIXED: advance last_end past this match

            kind = mo.lastgroup
            value = mo.group()

            if kind == "NEWLINE":
                line += 1
                continue
            if kind in ("SKIP", "COMMENT"):
                continue

            # Keyword / boolean promotion
            if kind == "ID" and value in KEYWORDS:
                kind = KEYWORDS[value]

            tokens.append(Token(kind, value, line))

        # FIXED: check trailing characters after last match (single-pass, no O(n²))
        if last_end < len(self.source):
            tail = self.source[last_end:]
            for i, ch in enumerate(tail):
                if ch not in " \t\r\n":
                    pos = last_end + i
                    bad_line = self.source[:pos].count("\n") + 1
                    raise LexerError(
                        f"Unexpected character: {ch!r}", bad_line,
                        self.get_line(bad_line),
                    )

        tokens.append(Token("EOF", "", line))
        return tokens
