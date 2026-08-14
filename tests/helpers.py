"""
helpers.py — shared utilities for the GravLang pytest test suite.

Provides ``run_grav(source_or_path)`` which lexes, parses, and interprets
a GravLang program and returns its stdout as a list of strings (one per
print() call), making assertions straightforward.
"""

from __future__ import annotations
import os
from typing import Union

from gravlang.core.lexer import Lexer
from gravlang.core.parser import Parser
from gravlang.core.interpreter import Interpreter
from gravlang.core.errors import GravLangError


def run_grav(
    source: str,
    *,
    path: str = "",
) -> list[str]:
    """
    Run a GravLang source string through the full pipeline and capture output.

    Parameters
    ----------
    source:
        GravLang source code as a string.
    path:
        Optional absolute path; used only so the interpreter can resolve
        relative ``import`` statements.  Leave empty for self-contained tests.

    Returns
    -------
    list[str]
        Lines printed by the program (one entry per ``print()`` call,
        *without* a trailing newline).

    Raises
    ------
    GravLangError
        Re-raised for any lexer / parser / runtime error so individual
        tests can assert on error scenarios.
    """
    captured: list[str] = []

    def _capture(*args, sep: str = " ", end: str = "\n") -> None:
        captured.append(sep.join(str(a) for a in args))

    tokens = Lexer(source).tokenize()
    tree = Parser(tokens).parse()
    interp = Interpreter(
        source=source,
        current_file=os.path.abspath(path) if path else "",
        print_fn=_capture,
    )
    interp.interpret(tree)
    return captured


def run_grav_file(path: str) -> list[str]:
    """
    Run a ``.grav`` file and capture its output.

    Parameters
    ----------
    path:
        Absolute (or CWD-relative) path to the ``.grav`` file.

    Returns
    -------
    list[str]
        Lines printed by the program.
    """
    abs_path = os.path.abspath(path)
    with open(abs_path, encoding="utf-8") as fh:
        source = fh.read()
    return run_grav(source, path=abs_path)
