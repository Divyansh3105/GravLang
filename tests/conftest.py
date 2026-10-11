"""
conftest.py — pytest configuration for the GravLang test suite.

Adds the project root to sys.path so all GravLang modules
(lexer, parser, interpreter, …) can be imported from any test.
"""

from __future__ import annotations
import sys
import os

# Project root is one level above this file (tests/../)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# IDE tests change the theme / recent files: keep that out of the developer's real settings.
import tempfile

os.environ.setdefault("GRAVLANG_CONFIG", os.path.join(tempfile.mkdtemp(prefix="gravlang-test-"), "config.json"))
