import tkinter as tk
import os
from .themes import THEMES


class WelcomeView(tk.Frame):
    """Sleek dark-mode Welcome & Quick Start Dashboard."""

    DEMOS = [
        ("🐍 Snake Game", "demos/snake_game.grav"),
        ("📝 Todo App", "demos/todo_app.grav"),
        ("🧠 Brainfuck Interpreter", "demos/brainfuck.grav"),
        ("📊 Grade Analyzer", "demos/grade_analyzer.grav"),
    ]

    SHORTCUTS = [
        ("Ctrl + N", "New File"),
        ("Ctrl + O", "Open File"),
        ("Ctrl + S", "Save File"),
        ("F5 / Ctrl + R", "▶ Run Code"),
        ("F10", "👣 Step Code"),
        ("Ctrl + F", "Find & Replace"),
        ("Ctrl + /", "Toggle Comment"),
        ("Ctrl + Shift + F", "Format Code"),
    ]

    def __init__(
        self,
        parent,
        theme: dict,
        on_new_file=None,
        on_open_file=None,
        on_open_recent=None,
        on_load_demo=None,
    ):
        super().__init__(parent, bg=theme["BG_BASE"])
        self.theme = theme
        self.on_new_file = on_new_file
        self.on_open_file = on_open_file
        self.on_open_recent = on_open_recent
        self.on_load_demo = on_load_demo
        self.recent_files: list[str] = []
        self._build()

    def _build(self):
        t = self.theme
        self.configure(bg=t["BG_BASE"])

        # Scrollable container for smaller screen sizes
        container = tk.Frame(self, bg=t["BG_BASE"])
        container.pack(fill="both", expand=True, padx=24, pady=24)

        # ── Header Banner ────────────────────────────────────────────────────
        hdr = tk.Frame(container, bg=t["BG_BASE"])
        hdr.pack(fill="x", pady=(0, 20))

        title_lbl = tk.Label(
            hdr,
            text="🌌 GravLang IDE",
            bg=t["BG_BASE"],
            fg=t["BLUE"],
            font=("Segoe UI", 24, "bold"),
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            hdr,
            text="A lightweight, elegantly designed multi-paradigm programming language toolchain",
            bg=t["BG_BASE"],
            fg=t["TEXT_SUB"],
            font=("Segoe UI", 11),
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # ── 3-Column Content Grid ────────────────────────────────────────────
        grid = tk.Frame(container, bg=t["BG_BASE"])
        grid.pack(fill="both", expand=True)

        # Column 1: ⚡ Quick Actions
        col1 = self._build_card(grid, "⚡ Quick Actions", t)
        col1.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._build_action_btn(col1, "📄 New File", self.on_new_file, t, primary=True)
        self._build_action_btn(col1, "📂 Open File...", self.on_open_file, t)

        tk.Label(
            col1,
            text="EXPLORE DEMOS",
            bg=t["BG_MANTLE"],
            fg=t["TEXT_OVERLAY"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(16, 6))

        for name, rel_path in self.DEMOS:
            full_path = os.path.abspath(rel_path)
            self._build_action_btn(
                col1,
                name,
                lambda p=full_path: self.on_load_demo(p) if self.on_load_demo else None,
                t,
                subtle=True,
            )

        # Column 2: 🕒 Recent Files
        col2 = self._build_card(grid, "🕒 Recent Files", t)
        col2.pack(side="left", fill="both", expand=True, padx=5)
        self.recent_frame = tk.Frame(col2, bg=t["BG_MANTLE"])
        self.recent_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self._render_recents()

        # Column 3: ⌨️ Keyboard Cheat Sheet
        col3 = self._build_card(grid, "⌨️ Keyboard Shortcuts", t)
        col3.pack(side="left", fill="both", expand=True, padx=(10, 0))

        shortcuts_frame = tk.Frame(col3, bg=t["BG_MANTLE"])
        shortcuts_frame.pack(fill="both", expand=True, padx=12, pady=8)

        for combo, desc in self.SHORTCUTS:
            row = tk.Frame(shortcuts_frame, bg=t["BG_MANTLE"])
            row.pack(fill="x", pady=3)

            k_lbl = tk.Label(
                row,
                text=combo,
                bg=t["BG_SURFACE0"],
                fg=t["BLUE"],
                font=("Consolas", 9, "bold"),
                padx=6,
                pady=2,
            )
            k_lbl.pack(side="left")

            d_lbl = tk.Label(
                row,
                text=desc,
                bg=t["BG_MANTLE"],
                fg=t["TEXT_MAIN"],
                font=("Segoe UI", 9),
            )
            d_lbl.pack(side="left", padx=8)

    def _build_card(self, parent, title: str, t: dict) -> tk.Frame:
        card = tk.Frame(parent, bg=t["BG_MANTLE"], highlightthickness=1, highlightbackground=t["BG_SURFACE0"])
        hdr = tk.Frame(card, bg=t["BG_MANTLE"], height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr,
            text=title,
            bg=t["BG_MANTLE"],
            fg=t["TEXT_MAIN"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=12, pady=8)
        tk.Frame(card, bg=t["BG_SURFACE0"], height=1).pack(fill="x")
        return card

    def _build_action_btn(self, parent, text: str, command, t: dict, primary=False, subtle=False):
        bg = t["BLUE"] if primary else (t["BG_MANTLE"] if subtle else t["BG_SURFACE0"])
        fg = t["BG_CRUST"] if primary else t["TEXT_MAIN"]

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            relief="flat",
            font=("Segoe UI", 10, "bold" if primary else "normal"),
            anchor="w",
            padx=12,
            pady=6,
            cursor="hand2",
            bd=0,
            activebackground=t["TEAL"] if primary else t["BG_SURFACE1"],
            activeforeground=fg,
        )
        btn.pack(fill="x", padx=12, pady=3)

    def set_recent_files(self, paths: list[str]):
        """Update recent files list and re-render."""
        self.recent_files = [p for p in paths if p and os.path.exists(p)]
        self._render_recents()

    def _render_recents(self):
        t = self.theme
        for child in self.recent_frame.winfo_children():
            child.destroy()

        if not self.recent_files:
            tk.Label(
                self.recent_frame,
                text="No recent files yet.\nOpen or save a .grav file to see it here!",
                bg=t["BG_MANTLE"],
                fg=t["TEXT_SUB"],
                font=("Segoe UI", 9),
                justify="left",
            ).pack(anchor="w", padx=4, pady=8)
            return

        for path in self.recent_files[:8]:
            name = os.path.basename(path)
            folder = os.path.dirname(path)

            btn = tk.Frame(self.recent_frame, bg=t["BG_SURFACE0"], cursor="hand2", padx=8, pady=4)
            btn.pack(fill="x", pady=2)

            top = tk.Label(btn, text=name, bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"], font=("Segoe UI", 9, "bold"))
            top.pack(anchor="w")

            sub = tk.Label(btn, text=folder, bg=t["BG_SURFACE0"], fg=t["TEXT_SUB"], font=("Segoe UI", 8))
            sub.pack(anchor="w")

            def _click(e, p=path):
                if self.on_open_recent:
                    self.on_open_recent(p)

            def _enter(e, frame=btn, t_lbl=top, s_lbl=sub):
                frame.configure(bg=t["BG_SURFACE1"])
                t_lbl.configure(bg=t["BG_SURFACE1"])
                s_lbl.configure(bg=t["BG_SURFACE1"])

            def _leave(e, frame=btn, t_lbl=top, s_lbl=sub):
                frame.configure(bg=t["BG_SURFACE0"])
                t_lbl.configure(bg=t["BG_SURFACE0"])
                s_lbl.configure(bg=t["BG_SURFACE0"])

            for w in (btn, top, sub):
                w.bind("<Button-1>", _click)
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)

    def apply_theme(self, theme: dict):
        self.theme = theme
        self._build()
