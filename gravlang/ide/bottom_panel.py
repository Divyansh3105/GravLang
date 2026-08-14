import tkinter as tk
from tkinter import ttk
import re
import threading
from typing import Sequence
from .themes import THEMES

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    HAS_GRAVLANG: bool = True
    from ..core.lexer import Lexer
    from ..core.parser import Parser
    from ..core.interpreter import Interpreter
    from ..core.environment import Environment
    from ..core.grav_builtins import register_builtins
    from ..core.errors import GravLangError
else:
    try:
        from ..core.lexer import Lexer
        from ..core.parser import Parser
        from ..core.interpreter import Interpreter
        from ..core.environment import Environment
        from ..core.grav_builtins import register_builtins
        from ..core.errors import GravLangError
        HAS_GRAVLANG = True
    except ImportError:
        HAS_GRAVLANG = False

        class GravLangError(Exception):
            pass

        class Environment:
            _store = {}

        class Interpreter:
            def __init__(self, print_fn=None, input_fn=None, source="", **kwargs):
                self.global_env = Environment()

            def interpret(self, tree):
                pass


class ProblemsView(tk.Frame):
    """Real-time error diagnostic list with clickable line jumps."""

    def __init__(self, parent, theme, on_jump_cb=None):
        super().__init__(parent, bg=theme["BG_CRUST"])
        self.theme = theme
        self.on_jump = on_jump_cb
        self._build()

    def _build(self):
        t = self.theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Problems.Treeview",
            background=t["BG_CRUST"],
            foreground=t["TEXT_MAIN"],
            fieldbackground=t["BG_CRUST"],
            rowheight=24,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        style.configure(
            "Problems.Treeview.Heading",
            background=t["BG_MANTLE"],
            foreground=t["TEXT_SUB"],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map("Problems.Treeview", background=[("selected", t["BG_SURFACE1"])])

        self.tree = ttk.Treeview(
            self,
            columns=("severity", "line", "message"),
            show="headings",
            style="Problems.Treeview",
            selectmode="browse",
        )
        self.tree.heading("severity", text="", anchor="center")
        self.tree.heading("line", text="Line", anchor="center")
        self.tree.heading("message", text="Diagnostic Message", anchor="w")

        self.tree.column("severity", width=36, minwidth=36, stretch=False, anchor="center")
        self.tree.column("line", width=60, minwidth=60, stretch=False, anchor="center")
        self.tree.column("message", width=400, stretch=True, anchor="w")

        vsb = tk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self._on_select)
        self.tree.bind("<Return>", self._on_select)

    def set_problems(self, problems: Sequence[tuple[str, int | str, str]]):
        """Populate list of problems: [(severity, line, message), ...]"""
        self.tree.delete(*self.tree.get_children())
        for sev, line, msg in problems:
            icon = "❌" if sev == "error" else "⚠️"
            self.tree.insert("", "end", values=(icon, str(line), msg))

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item.get("values", [])
        if len(values) >= 2 and self.on_jump:
            try:
                line = int(values[1])
                self.on_jump(line)
            except ValueError:
                pass

    def apply_theme(self, theme):
        self.theme = theme
        t = theme
        self.configure(bg=t["BG_CRUST"])
        style = ttk.Style()
        style.configure(
            "Problems.Treeview",
            background=t["BG_CRUST"],
            foreground=t["TEXT_MAIN"],
            fieldbackground=t["BG_CRUST"],
        )
        style.configure("Problems.Treeview.Heading", background=t["BG_MANTLE"], foreground=t["TEXT_SUB"])
        style.map("Problems.Treeview", background=[("selected", t["BG_SURFACE1"])])


class BottomPanel(tk.Frame):
    """Multi-tabbed bottom developer control center."""

    def __init__(self, parent, theme, on_jump_cb=None):
        super().__init__(parent, bg=theme["BG_CRUST"])
        self.theme = theme
        self.on_jump = on_jump_cb
        self.active_tab_idx = 0
        self._build()

    def _build(self):
        t = self.theme

        # ── Header bar with tabs & action buttons ─────────────────────────────
        self.hdr = tk.Frame(self, bg=t["BG_MANTLE"], height=28)
        self.hdr.pack(fill="x", side="top")
        self.hdr.pack_propagate(False)

        # Tab buttons container (left)
        self.tab_bar = tk.Frame(self.hdr, bg=t["BG_MANTLE"])
        self.tab_bar.pack(side="left", fill="y")

        self.tab_defs = [
            ("🖥️ Output", "output"),
            ("⚠️ Problems", "problems"),
        ]
        self.tab_btns: list[tk.Label] = []
        for idx, (label, name) in enumerate(self.tab_defs):
            btn = tk.Label(
                self.tab_bar,
                text=label,
                bg=t["BG_MANTLE"],
                fg=t["TEXT_SUB"],
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                padx=10,
                pady=4,
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, i=idx: self.switch_tab(i))
            self.tab_btns.append(btn)

        # ── Body views container ─────────────────────────────────────────────
        self.body = tk.Frame(self, bg=t["BG_CRUST"])
        self.body.pack(fill="both", expand=True, side="top")

        # 1. Output View
        self.out_frame = tk.Frame(self.body, bg=t["BG_CRUST"])
        self.output_txt = tk.Text(
            self.out_frame,
            bg=t["BG_CRUST"],
            fg=t["GREEN"],
            font=("Consolas", 11),
            relief="flat",
            state="disabled",
            wrap="word",
            bd=0,
        )
        self.output_vsb = tk.Scrollbar(self.out_frame, orient="vertical", command=self.output_txt.yview)
        self.output_txt.configure(yscrollcommand=self.output_vsb.set)
        self.output_vsb.pack(side="right", fill="y")
        self.output_txt.pack(fill="both", expand=True, padx=4, pady=4)
        self._setup_output_tags()

        # 2. Problems View
        self.problems_view = ProblemsView(self.body, t, on_jump_cb=self.on_jump)

        self.views = [self.out_frame, self.problems_view]
        self.switch_tab(0)

    def _setup_output_tags(self):
        t = self.theme
        txt = self.output_txt
        txt.tag_configure("str", foreground=t["GREEN"])
        txt.tag_configure("num", foreground=t["MAUVE"])
        txt.tag_configure("bool", foreground=t["BLUE"])
        txt.tag_configure("null", foreground=t["LAVENDER"])
        txt.tag_configure("coll", foreground=t["TEAL"])
        txt.tag_configure("error", foreground=t["RED"], font=("Consolas", 11, "bold"))
        txt.tag_configure("timing", foreground=t["BLUE"])
        txt.tag_configure("sep", foreground=t["TEXT_SUB"])

    def switch_tab(self, target_idx: int):
        if not (0 <= target_idx < len(self.views)):
            return
        t = self.theme
        self.active_tab_idx = target_idx

        for idx, btn in enumerate(self.tab_btns):
            active = idx == target_idx
            bg = t["BG_BASE"] if active else t["BG_MANTLE"]
            fg = t["BLUE"] if active else t["TEXT_SUB"]
            btn.configure(bg=bg, fg=fg)

        for idx, view in enumerate(self.views):
            if idx == target_idx:
                view.pack(fill="both", expand=True)
            else:
                view.pack_forget()

    def append_output(self, text: str, tag: str = ""):
        """Append text to Output tab with automatic type-based color tags."""
        txt = self.output_txt
        txt.configure(state="normal")

        if tag:
            txt.insert("end", text, tag)
        else:
            # Auto-colorize typed literals if plain text
            lines = text.splitlines(keepends=True)
            for line in lines:
                if line.startswith("❌") or "Error" in line:
                    txt.insert("end", line, "error")
                elif line.startswith("✓") or line.startswith("──"):
                    txt.insert("end", line, "timing" if line.startswith("✓") else "sep")
                else:
                    self._insert_typed_line(txt, line)
        txt.configure(state="disabled")
        txt.see("end")

    def _insert_typed_line(self, txt: tk.Text, line: str):
        """Tokenize a line of printed output and insert with typed syntax colors."""
        tokens = re.split(r'(".*?"|\b\d+\.?\d*\b|\btrue\b|\bfalse\b|\bnull\b)', line)
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith('"') and tok.endswith('"'):
                txt.insert("end", tok, "str")
            elif re.match(r'^\d+\.?\d*$', tok):
                txt.insert("end", tok, "num")
            elif tok in ("true", "false"):
                txt.insert("end", tok, "bool")
            elif tok == "null":
                txt.insert("end", tok, "null")
            elif tok in ("{", "}", "[", "]", ":", ","):
                txt.insert("end", tok, "coll")
            else:
                txt.insert("end", tok)

    def clear_output(self):
        txt = self.output_txt
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.configure(state="disabled")

    def set_problems(self, problems: Sequence[tuple[str, int | str, str]]):
        self.problems_view.set_problems(problems)
        count = len(problems)
        self.tab_btns[1].configure(text=f"⚠️ Problems ({count})")

    def apply_theme(self, theme):
        self.theme = theme
        t = theme
        self.configure(bg=t["BG_CRUST"])
        self.hdr.configure(bg=t["BG_MANTLE"])
        self.tab_bar.configure(bg=t["BG_MANTLE"])
        self.out_frame.configure(bg=t["BG_CRUST"])
        self.output_txt.configure(bg=t["BG_CRUST"], fg=t["TEXT_MAIN"])

        self._setup_output_tags()
        self.problems_view.apply_theme(theme)
        self.switch_tab(self.active_tab_idx)
