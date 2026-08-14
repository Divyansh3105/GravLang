"""
GravLang CLI and GUI launcher.

Usage:
    python -m gravlang                   → Launch GUI IDE
    python -m gravlang --repl            → Launch interactive REPL
    python -m gravlang program.grav      → Run program headlessly
"""

import sys
import os

from .core.lexer import Lexer
from .core.parser import Parser
from .core.interpreter import Interpreter
from .core.errors import GravLangError, ParseError
from .core.grav_builtins import _builtin_toString


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
            for stmt in tree.body:
                val = interp._exec(stmt, interp.global_env)
                if type(stmt).__name__ not in ("VarDecl", "Assign", "AugAssign", "IfStmt", "WhileStmt", "ForStmt", "ForInStmt", "FuncDecl", "ClassDecl", "ReturnStmt", "BreakStmt", "ContinueStmt", "ImportStmt", "TryCatchStmt", "ThrowStmt", "Block"):
                    if val is not None:
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
        from .ide.main_window import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
