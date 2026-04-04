"""
GravLang — CLI entry point.

Usage:
    python main.py                  → launch the GUI IDE
    python main.py program.grav     → run a .grav file headlessly
"""

from __future__ import annotations
import sys
import os

# Allow running as `python main.py` from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from errors import GravLangError
from grav_builtins import register_builtins


def run_file(path: str) -> None:
    """Lex → parse → interpret a .grav source file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found — {path}")
        sys.exit(1)

    try:
        tokens = Lexer(source).tokenize()
        tree   = Parser(tokens).parse()
        interp = Interpreter(source=source)
        interp.interpret(tree)
    except GravLangError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except RecursionError:
        print("❌ Runtime Error: Stack overflow — maximum recursion depth exceeded")
        sys.exit(1)

def main():
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        from gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
