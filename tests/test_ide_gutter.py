import unittest
import tkinter as tk
from gravlang.ide.editor import EditorTab
from gravlang.ide.themes import THEMES


class TestIDEGutter(unittest.TestCase):
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

    def test_find_fold_ranges(self):
        frame = tk.Frame(self.root)
        theme = THEMES["Catppuccin Mocha"]
        tab = EditorTab(frame, theme, on_change_cb=lambda: None, on_cursor_cb=lambda r, c: None)

        code = """func calculate(x, y) {
    let sum = x + y;
    if (sum > 10) {
        print("large");
    }
    return sum;
}
"""
        tab.set_content(code)
        ranges = tab._find_fold_ranges()

        # Line 1 opens { and closes on line 7
        self.assertIn(1, ranges)
        self.assertEqual(ranges[1], 7)

        # Line 3 opens { and closes on line 5
        self.assertIn(3, ranges)
        self.assertEqual(ranges[3], 5)

    def test_toggle_fold(self):
        frame = tk.Frame(self.root)
        theme = THEMES["Catppuccin Mocha"]
        tab = EditorTab(frame, theme, on_change_cb=lambda: None, on_cursor_cb=lambda r, c: None)

        code = """func test() {
    print(1);
    print(2);
}"""
        tab.set_content(code)

        # Initially block is not folded
        self.assertNotIn(1, tab.folded_blocks)

        # Toggle fold ON for line 1
        folded = tab.toggle_fold(1)
        self.assertTrue(folded)
        self.assertIn(1, tab.folded_blocks)

        # Toggle fold OFF for line 1
        unfolded = tab.toggle_fold(1)
        self.assertFalse(unfolded)
        self.assertNotIn(1, tab.folded_blocks)

    def test_set_paused_line(self):
        frame = tk.Frame(self.root)
        theme = THEMES["Catppuccin Mocha"]
        tab = EditorTab(frame, theme, on_change_cb=lambda: None, on_cursor_cb=lambda r, c: None)

        self.assertIsNone(tab.paused_line)

        tab.set_paused_line(4)
        self.assertEqual(tab.paused_line, 4)

        tab.set_paused_line(None)
        self.assertIsNone(tab.paused_line)


if __name__ == "__main__":
    unittest.main()
