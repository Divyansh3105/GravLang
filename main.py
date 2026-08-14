"""
GravLang — CLI & GUI entry point wrapper.

Usage:
    python main.py                  → launch the GUI IDE
    python main.py program.grav     → run a .grav file headlessly
    python main.py --repl           → launch interactive REPL
"""

import sys
import os

# Ensure the project root directory is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from gravlang.__main__ import main

if __name__ == "__main__":
    main()
