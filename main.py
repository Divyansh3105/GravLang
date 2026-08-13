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
from errors import GravLangError, ParseError
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
        interp = Interpreter(source=source, current_file=os.path.abspath(path))
        interp.interpret(tree)
    except GravLangError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except RecursionError:
        print("❌ Runtime Error: Stack overflow — maximum recursion depth exceeded")
        sys.exit(1)

def repl() -> None:
    """Interactive read-eval-print loop."""
    print("GravLang REPL. Type 'exit' to quit.")
    interp = Interpreter(source="<stdin>", current_file=os.getcwd())
    
    buffer = ""
    while True:
        try:
            prompt = "... " if buffer else "> "
            line = input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            break
            
        if not buffer and line.strip() == "exit":
            break
            
        buffer += line + "\n"
        
        try:
            tokens = Lexer(buffer).tokenize()
        except GravLangError as e:
            print(f"❌ {e}")
            buffer = ""
            continue
            
        try:
            tree = Parser(tokens).parse()
        except ParseError as e:
            if "EOF" in str(e):
                continue
            else:
                print(f"❌ {e}")
                buffer = ""
                continue
                
        try:
            # Evaluate all statements in the parsed tree
            for stmt in tree.body:
                # If it's a bare expression statement, we can print its value
                # But since our interpreter returns None for statements, we just exec
                val = interp._exec(stmt, interp.global_env)
                # Hack to print bare expressions in REPL
                if type(stmt).__name__ not in ("VarDecl", "Assign", "AugAssign", "IfStmt", "WhileStmt", "ForStmt", "ForInStmt", "FuncDecl", "ClassDecl", "ReturnStmt", "BreakStmt", "ContinueStmt", "ImportStmt", "TryCatchStmt", "ThrowStmt", "Block"):
                    if val is not None:
                        from grav_builtins import _builtin_toString
                        print(_builtin_toString(val))
        except GravLangError as e:
            print(f"❌ {e}")
        except RecursionError:
            print("❌ Runtime Error: Stack overflow")
            
        buffer = ""

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--repl":
            repl()
        else:
            run_file(sys.argv[1])
    else:
        from gravlang_ide import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
