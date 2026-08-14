import unittest
import tkinter as tk
from gravlang.ide.main_window import GravLangIDE, SPINNER_FRAMES


class TestIDEStatusbar(unittest.TestCase):
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

    def test_spinner_frames(self):
        self.assertEqual(len(SPINNER_FRAMES), 10)
        self.assertIn("⠋", SPINNER_FRAMES)

    def test_scope_stats_update(self):
        ide = GravLangIDE(self.root)
        dummy_store = {
            "a": 10,
            "b": "hello",
            "arr": [1, 2, 3],
            "dict_obj": {"x": 1},
        }
        ide._update_scope_stats(dummy_store)
        stats_text = ide._status_stats.cget("text")
        self.assertIn("🌐 Vars: 4", stats_text)
        self.assertIn("📦 Objects: 2", stats_text)

    def test_status_done_metrics(self):
        ide = GravLangIDE(self.root)
        ide._set_status_done(0.042)
        run_text = ide._status_run.cget("text")
        self.assertIn("⚡ Executed in 0.042s", run_text)


if __name__ == "__main__":
    unittest.main()
