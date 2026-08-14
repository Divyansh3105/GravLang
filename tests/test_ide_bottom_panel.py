import unittest
import tkinter as tk
from gravlang_ide.bottom_panel import BottomPanel, ProblemsView
from gravlang_ide.themes import THEMES


class TestIDEBottomPanel(unittest.TestCase):
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

    def test_bottom_panel_tab_switching(self):
        theme = THEMES["Catppuccin Mocha"]
        panel = BottomPanel(self.root, theme)

        self.assertEqual(panel.active_tab_idx, 0)

        # Switch to Problems (tab 1)
        panel.switch_tab(1)
        self.assertEqual(panel.active_tab_idx, 1)

        # Switch back to Output (tab 0)
        panel.switch_tab(0)
        self.assertEqual(panel.active_tab_idx, 0)

    def test_problems_view_jump_callback(self):
        theme = THEMES["Catppuccin Mocha"]
        jumped_lines = []

        def jump_cb(line):
            jumped_lines.append(line)

        view = ProblemsView(self.root, theme, on_jump_cb=jump_cb)
        view.set_problems([("error", 12, "SyntaxError: Unexpected token")])

        items = view.tree.get_children()
        self.assertEqual(len(items), 1)

        # Select first item and trigger jump
        view.tree.selection_set(items[0])
        view._on_select()
        self.assertIn(12, jumped_lines)


if __name__ == "__main__":
    unittest.main()
