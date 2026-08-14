import unittest
import tkinter as tk
import os
from gravlang_ide.welcome_view import WelcomeView
from gravlang_ide.themes import THEMES


class TestIDEWelcomeView(unittest.TestCase):
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

    def test_welcome_view_creation(self):
        theme = THEMES["Catppuccin Mocha"]
        new_triggered = []
        open_triggered = []

        view = WelcomeView(
            self.root,
            theme,
            on_new_file=lambda: new_triggered.append(True),
            on_open_file=lambda: open_triggered.append(True),
        )
        self.assertIsNotNone(view)

    def test_recent_files_rendering(self):
        theme = THEMES["Catppuccin Mocha"]
        clicked_paths = []

        view = WelcomeView(
            self.root,
            theme,
            on_open_recent=lambda path: clicked_paths.append(path),
        )

        test_file = os.path.abspath("main.py")
        view.set_recent_files([test_file])

        self.assertEqual(len(view.recent_files), 1)
        self.assertEqual(view.recent_files[0], test_file)

    def test_demos_list(self):
        theme = THEMES["Catppuccin Mocha"]
        demo_paths = []

        view = WelcomeView(
            self.root,
            theme,
            on_load_demo=lambda path: demo_paths.append(path),
        )

        self.assertTrue(len(view.DEMOS) >= 4)
        first_demo = os.path.abspath(view.DEMOS[0][1])
        self.assertIn("snake_game", first_demo)


if __name__ == "__main__":
    unittest.main()
