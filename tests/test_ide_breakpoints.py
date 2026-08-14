import unittest
import tkinter as tk
from gravlang_ide.editor import EditorTab
from gravlang_ide.themes import THEMES
from interpreter import Interpreter
from environment import Environment
from parser import Parser
from lexer import Lexer


class TestIDEBreakpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            cls.tk_available = True
        except Exception:
            cls.tk_available = False

    @classmethod
    def tearDownClass(cls):
        if cls.tk_available:
            cls.root.destroy()

    def setUp(self):
        if not self.tk_available:
            self.skipTest("Tkinter display not available")

    def test_breakpoint_toggle(self):
        frame = tk.Frame(self.root)
        theme = THEMES["Catppuccin Mocha"]
        tab = EditorTab(frame, theme, on_change_cb=lambda: None, on_cursor_cb=lambda r, c: None)
        
        self.assertEqual(len(tab.breakpoints), 0)
        
        # Toggle line 3 ON
        added = tab.toggle_breakpoint(3)
        self.assertTrue(added)
        self.assertIn(3, tab.breakpoints)

        # Toggle line 3 OFF
        removed = tab.toggle_breakpoint(3)
        self.assertFalse(removed)
        self.assertNotIn(3, tab.breakpoints)

        # Toggle lines 5 & 8
        tab.toggle_breakpoint(5)
        tab.toggle_breakpoint(8)
        self.assertEqual(tab.breakpoints, {5, 8})

        # Clear breakpoints
        tab.clear_breakpoints()
        self.assertEqual(len(tab.breakpoints), 0)

    def test_breakpoint_hook_detection(self):
        code = """
let x = 10;
let y = 20;
let z = x + y;
"""
        tokens = Lexer(code).tokenize()
        tree = Parser(tokens).parse()

        paused_lines = []
        breakpoints = {3}  # Line 3: let y = 20;

        def step_hook(line, env):
            if line in breakpoints:
                paused_lines.append(line)

        interp = Interpreter(source=code, on_step=step_hook)
        interp.interpret(tree)

        self.assertIn(3, paused_lines)


if __name__ == "__main__":
    unittest.main()
