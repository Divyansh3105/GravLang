import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, json, time, threading, re
from datetime import datetime
from .themes import THEMES, CONFIG_FILE
from .constants import *
from .components import VariableInspector, FileExplorer, _simple_dialog, FindReplaceBar
from .editor import EditorTab
from .compiler_view import CompilerStagesWindow
from .bottom_panel import BottomPanel
from .welcome_view import WelcomeView
try:
    from lexer import Lexer
    from parser import Parser
    from interpreter import Interpreter
    from errors import GravLangError
    HAS_GRAVLANG = True
except ImportError:
    HAS_GRAVLANG = False

    class GravLangError(Exception):
        pass

    class _FakeEnv:
        _store = {}

    class Interpreter:
        def __init__(self, print_fn=None, input_fn=None, source="", **kwargs):
            self.global_env = _FakeEnv()
            self._print_fn = print_fn or print


        def interpret(self, tree):
            self._print_fn("GravLang runtime not found.\nRunning in demo mode.")

    class Lexer:
        def __init__(self, src): pass
        def tokenize(self): return []

    class Parser:
        def __init__(self, tokens): pass
        def parse(self): return None

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

class GravLangIDE:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("GravLang IDE")
        self.root.geometry("1280x800")
        self.root.minsize(900, 600)

        # load config
        self._config = self._load_config()
        theme_name   = self._config.get("theme", "Catppuccin Mocha")
        self.theme   = THEMES.get(theme_name, THEMES["Catppuccin Mocha"])
        self.theme_name = theme_name
        self._recent_files: list[str] = [
            p for p in self._config.get("recent_files", []) if os.path.exists(p)
        ]

        # state
        self._tabs:       list[EditorTab] = []
        self._tab_frames: list[tk.Frame]  = []
        self._active_idx: int = -1
        self._sidebar_visible = True
        self._inspector_visible = True
        self._last_run_time: float = 0.0
        self._run_status   = ""
        self._cancel_flag  = False        # FIXED: cancel flag for Stop button
        self._run_thread   = None         # FIXED: track background run thread
        self._stages_win: CompilerStagesWindow | None = None
        self._is_stepping  = False
        self._step_event   = threading.Event()
        self._last_paused_line = -1

        self.root.configure(bg=self.theme["BG_BASE"])
        self._build_ui()
        self._bind_global()

    # ── UI BUILD ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_titlebar()
        self._build_tabbar()
        self._build_toolbar()
        self._build_findbar()
        self._build_body()
        self._build_statusbar()

    def _build_titlebar(self):
        t  = self.theme
        tb = tk.Frame(self.root, bg=t["BG_MANTLE"], height=30)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)
        self._titlebar = tb

        # ── Window drag (click anywhere on bar except buttons) ───────────────
        self._drag_x = 0
        self._drag_y = 0
        self._is_maximized = False

        def start_drag(e):
            self._drag_x = e.x_root - self.root.winfo_x()
            self._drag_y = e.y_root - self.root.winfo_y()

        def do_drag(e):
            if self._is_maximized:
                return
            x = e.x_root - self._drag_x
            y = e.y_root - self._drag_y
            self.root.geometry(f"+{x}+{y}")

        def on_double_click(e):
            self._toggle_fullscreen()

        tb.bind("<Button-1>",    start_drag)
        tb.bind("<B1-Motion>",   do_drag)
        tb.bind("<Double-1>",    on_double_click)

        # ── LEFT: app icon ───────────────────────────────────────────────────
        icon_cv = tk.Canvas(tb, width=20, height=20,
                            bg=t["BG_MANTLE"], highlightthickness=0)
        icon_cv.pack(side="left", padx=(10, 4), pady=5)
        # Draw a simple "G" chevron logo like VS Code's icon
        icon_cv.create_polygon(10,3, 17,7, 17,13, 10,17, 10,13, 14,10, 14,10, 10,7,
                               fill=t["BLUE"], outline="")
        icon_cv.bind("<Button-1>", start_drag)
        icon_cv.bind("<B1-Motion>", do_drag)

        # ── CENTER: title text (draggable) ───────────────────────────────────
        self.title_lbl = tk.Label(tb, text="GravLang IDE — untitled.grav",
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"],
            font=("Segoe UI", 11))
        self.title_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.title_lbl.bind("<Button-1>",  start_drag)
        self.title_lbl.bind("<B1-Motion>", do_drag)
        self.title_lbl.bind("<Double-1>",  on_double_click)

        # ── RIGHT: Windows-style window controls ─────────────────────────────
        btn_frame = tk.Frame(tb, bg=t["BG_MANTLE"])
        btn_frame.pack(side="right")

        # Each control: (symbol, hover_bg, command)
        controls = [
            ("─",  t["BG_SURFACE0"], self._minimize_window),
            ("□",  t["BG_SURFACE0"], self._toggle_fullscreen),
            ("✕",  "#c42b1c",        self.root.destroy),
        ]
        self._win_btns = []
        for symbol, hover_bg, cmd in controls:
            normal_bg = t["BG_MANTLE"]
            btn = tk.Label(
                btn_frame, text=symbol,
                bg=normal_bg, fg=t["TEXT_OVERLAY"],
                font=("Segoe UI", 11),
                width=4, pady=4, cursor="hand2",
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            btn.bind("<Enter>",    lambda e, w=btn, h=hover_bg: w.configure(bg=h, fg="#ffffff"))
            btn.bind("<Leave>",    lambda e, w=btn, nb=normal_bg, t=t: w.configure(bg=nb, fg=t["TEXT_OVERLAY"]))
            self._win_btns.append((btn, normal_bg, hover_bg))

    def _build_tabbar(self):
        t   = self.theme
        bar = tk.Frame(self.root, bg=t["BG_MANTLE"], height=42,
                       bd=0, relief="flat")
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # inner scrollable tab area
        self._tab_scroll_frame = tk.Frame(bar, bg=t["BG_MANTLE"])
        self._tab_scroll_frame.pack(side="left", fill="y")

        plus = tk.Label(bar, text=" + ", bg=t["BG_MANTLE"], fg=t["TEXT_OVERLAY"],
                        font=("Segoe UI", 14, "bold"), cursor="hand2")
        plus.pack(side="left", padx=4)
        plus.bind("<Button-1>", lambda e: self.new_tab())

        self._tabbar = bar
        self._tab_labels: list[tk.Frame] = []

    def _build_toolbar(self):
        t   = self.theme
        bar = tk.Frame(self.root, bg=t["BG_MANTLE"], height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        self._toolbar = bar

        def btn(text, cmd, accent=False, padx=10):
            bg = t["BLUE"] if accent else t["BG_MANTLE"]
            fg = t["BG_CRUST"] if accent else t["TEXT_MAIN"]
            b  = tk.Button(bar, text=text, command=cmd,
                bg=bg, fg=fg, relief="flat", font=("Segoe UI", 10, "bold"),
                padx=padx, pady=4, cursor="hand2",
                activebackground=t["BG_SURFACE0"] if not accent else t["TEAL"],
                activeforeground=fg, bd=0, highlightthickness=0)
            b.pack(side="left", padx=1, pady=3)
            b.bind("<Enter>", lambda e, w=b: w.configure(
                bg=t["BG_SURFACE0"] if not accent else t["TEAL"]))
            b.bind("<Leave>", lambda e, w=b: w.configure(
                bg=bg))
            return b

        def sep():
            tk.Frame(bar, bg=t["BG_SURFACE0"], width=1, height=18).pack(
                side="left", padx=4, pady=8)

        self._run_button = btn("▶  Run", self.run_code, accent=True)
        self._step_button = btn("👣 Step", self.step_code)
        sep()
        btn("📂 Open",  self.open_file)
        btn("💾 Save",  self.save_file)
        btn("🪄 Format", self.format_code)
        sep()
        # Compiler Stages button
        stg_btn = tk.Button(bar, text="⚙ Stages", command=self._open_stages,
            bg=t["BG_MANTLE"], fg=t["MAUVE"], relief="flat",
            font=("Segoe UI", 10, "bold"), padx=10, pady=4, cursor="hand2",
            activebackground=t["BG_SURFACE0"], bd=0, highlightthickness=0)
        stg_btn.pack(side="left", padx=1, pady=3)
        stg_btn.bind("<Enter>", lambda e: stg_btn.configure(bg=t["BG_SURFACE0"]))
        stg_btn.bind("<Leave>", lambda e: stg_btn.configure(bg=t["BG_MANTLE"]))
        sep()
        # Examples dropdown
        ex_btn = tk.Button(bar, text="📚 Examples ▾", command=self._show_examples,
            bg=t["BG_MANTLE"], fg=t["TEXT_MAIN"], relief="flat",
            font=("Segoe UI", 10, "bold"), padx=10, pady=4, cursor="hand2",
            activebackground=t["BG_SURFACE0"], bd=0, highlightthickness=0)
        ex_btn.pack(side="left", padx=1, pady=3)
        ex_btn.bind("<Enter>", lambda e: ex_btn.configure(bg=t["BG_SURFACE0"]))
        ex_btn.bind("<Leave>", lambda e: ex_btn.configure(bg=t["BG_MANTLE"]))

        btn("🔍 Find", self._toggle_find)
        sep()
        # Theme dropdown (right)
        th_btn = tk.Button(bar, text="🎨 Theme ▾", command=self._show_themes,
            bg=t["BG_MANTLE"], fg=t["TEXT_MAIN"], relief="flat",
            font=("Segoe UI", 10, "bold"), padx=10, pady=4, cursor="hand2",
            activebackground=t["BG_SURFACE0"], bd=0, highlightthickness=0)
        th_btn.pack(side="right", padx=1, pady=3)
        th_btn.bind("<Enter>", lambda e: th_btn.configure(bg=t["BG_SURFACE0"]))
        th_btn.bind("<Leave>", lambda e: th_btn.configure(bg=t["BG_MANTLE"]))

        hlp_btn = tk.Button(bar, text="? Shortcuts", command=self._show_shortcuts,
            bg=t["BG_MANTLE"], fg=t["TEXT_MAIN"], relief="flat",
            font=("Segoe UI", 10, "bold"), padx=10, pady=4, cursor="hand2",
            activebackground=t["BG_SURFACE0"], bd=0, highlightthickness=0)
        hlp_btn.pack(side="right", padx=1, pady=3)
        hlp_btn.bind("<Enter>", lambda e: hlp_btn.configure(bg=t["BG_SURFACE0"]))
        hlp_btn.bind("<Leave>", lambda e: hlp_btn.configure(bg=t["BG_MANTLE"]))

        # self._run_button is the primary reference; _run_btn kept for compat
        self._run_btn = self._run_button

    def _build_findbar(self):
        # Parented to _editor_pane which is built in _build_body.
        # We defer actual packing until _build_body has run (called after it).
        pass

    def _attach_findbar(self):
        """Called after _editor_pane exists.  Creates the bar inside the pane."""
        t = self.theme
        self._findbar = FindReplaceBar(
            self._editor_pane,
            editor_getter=self._active_editor,
            theme=t, bg=t["BG_MANTLE"])
        # not packed yet — shown on demand via _toggle_find()

    def _build_body(self):
        t = self.theme
        # Outer frame fills all remaining space between toolbars and statusbar
        self._outer = tk.Frame(self.root, bg=t["BG_BASE"])
        self._outer.pack(fill="both", expand=True)

        # ── ACTIVITY BAR (leftmost vertical strip) ───────────────────────────
        self._activity_bar = tk.Frame(self._outer, bg=t["BG_MANTLE"], width=44)
        self._activity_bar.pack(side="left", fill="y")
        self._activity_bar.pack_propagate(False)
        self._build_activity_bar()

        # ── RIGHT SIDE: vertical split (editor on top, output on bottom) ─────
        # All side="left" children must be added BEFORE any side="top/bottom"
        # children, or pack ignores them.  So we put the vertical frame here.
        self._right = tk.Frame(self._outer, bg=t["BG_BASE"])
        self._right.pack(side="left", fill="both", expand=True)

        # ── BOTTOM PANE (inside _right, packed first so it reserves space) ───
        self._build_bottom_pane()

        # ── HORIZONTAL ROW: sidebar + editor (above the bottom pane) ─────────
        self._body = tk.Frame(self._right, bg=t["BG_BASE"])
        self._body.pack(side="top", fill="both", expand=True)

        # ── SIDEBAR (file explorer) ──────────────────────────────────────────
        self._sidebar = tk.Frame(self._body, bg=t["BG_MANTLE"], width=180)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._file_explorer = FileExplorer(
            self._sidebar, t, self.open_file_path)
        self._file_explorer.pack(fill="both", expand=True)

        # ── EDITOR AREA ──────────────────────────────────────────────────────
        self._editor_pane = tk.Frame(self._body, bg=t["BG_BASE"])
        self._editor_pane.pack(side="left", fill="both", expand=True)

        # container for stacked tab frames
        self._editor_stack = tk.Frame(self._editor_pane, bg=t["BG_BASE"])
        self._editor_stack.pack(fill="both", expand=True, side="top")

        # Attach the findbar now that _editor_pane exists
        self._attach_findbar()

        # Welcome & Quick Start Dashboard View
        self._welcome_view = WelcomeView(
            self._editor_stack,
            t,
            on_new_file=lambda: self.new_tab(),
            on_open_file=self.open_file,
            on_open_recent=self.open_file_path,
            on_load_demo=self.open_file_path,
        )
        self._welcome_view.set_recent_files(self._recent_files)
        self._welcome_view.pack(fill="both", expand=True)

    def _build_activity_bar(self):
        t   = self.theme
        bar = self._activity_bar
        icons = [("🗂", self._toggle_sidebar, True),
                 ("⌕", self._toggle_find, False)]
        self._act_btns = []
        for text, cmd, active in icons:
            btn = tk.Button(bar, text=text, command=cmd,
                bg=t["BG_MANTLE"], fg=t["BLUE"] if active else t["TEXT_SUB"],
                relief="flat", font=("Segoe UI", 16), padx=0, pady=8,
                cursor="hand2", width=3, bd=0, highlightthickness=0,
                activebackground=t["BG_SURFACE0"])
            btn.pack(fill="x", pady=4)
            self._act_btns.append(btn)

        # info at bottom
        info = tk.Button(bar, text="ⓘ", command=self._show_shortcuts,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 14), cursor="hand2", width=3, bd=0,
            highlightthickness=0, activebackground=t["BG_SURFACE0"])
        info.place(relx=0.5, rely=1.0, anchor="s", y=-10)

    def _jump_to_editor_line(self, line: int):
        tab = self._active_tab()
        if tab:
            tab.editor.mark_set("insert", f"{line}.0")
            tab.editor.see(f"{line}.0")
            tab.editor.focus_set()

    def _build_bottom_pane(self):
        t = self.theme

        # ── Drag-sash resize handle ──────────────────────────────────────────
        self._sash = tk.Frame(self._right, bg=t["BG_SURFACE1"], height=4, cursor="sb_v_double_arrow")
        self._sash.pack(side="bottom", fill="x")
        self._sash_dragging = False
        self._sash_start_y  = 0
        self._sash_start_h  = 220

        def _sash_press(e):
            self._sash_dragging = True
            self._sash_start_y  = e.y_root
            self._sash_start_h  = self._bottom.winfo_height()

        def _sash_drag(e):
            if not self._sash_dragging:
                return
            delta = self._sash_start_y - e.y_root   # dragging up = bigger panel
            new_h = max(80, min(self._sash_start_h + delta, 600))
            self._bottom.configure(height=new_h)

        def _sash_release(e):
            self._sash_dragging = False

        self._sash.bind("<ButtonPress-1>",   _sash_press)
        self._sash.bind("<B1-Motion>",        _sash_drag)
        self._sash.bind("<ButtonRelease-1>",  _sash_release)
        # Highlight sash on hover
        self._sash.bind("<Enter>", lambda e: self._sash.configure(bg=t["BLUE"]))
        self._sash.bind("<Leave>", lambda e: self._sash.configure(bg=t["BG_SURFACE1"]))

        # ── Main bottom container ────────────────────────────────────────────
        self._bottom = tk.Frame(self._right, bg=t["BG_CRUST"], height=220)
        self._bottom.pack(side="bottom", fill="x")
        self._bottom.pack_propagate(False)

        # ── Multi-Tab Bottom Panel (left) ───────────────────────────────────
        self._bottom_panel = BottomPanel(self._bottom, t, on_jump_cb=self._jump_to_editor_line)
        self._bottom_panel.pack(side="left", fill="both", expand=True)

        self._output = self._bottom_panel.output_txt
        self._out_frame = self._bottom_panel.out_frame

        hdr = self._bottom_panel.hdr

        self._clear_on_run = tk.BooleanVar(value=False)

        def _toggle_clear_on_run():
            state = self._clear_on_run.get()
            clr_lbl.configure(
                fg=t["BLUE"] if state else t["TEXT_SUB"],
                text="⟳ Clear on Run ✓" if state else "⟳ Clear on Run",
            )

        clr_lbl = tk.Label(
            hdr, text="⟳ Clear on Run",
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"],
            font=("Segoe UI", 9), cursor="hand2", padx=6,
        )
        clr_lbl.pack(side="right", pady=4, padx=4)
        clr_lbl.bind("<Button-1>", lambda e: (
            self._clear_on_run.set(not self._clear_on_run.get()),
            _toggle_clear_on_run(),
        ))
        clr_lbl.bind("<Enter>", lambda e: clr_lbl.configure(fg=t["BLUE"]))
        clr_lbl.bind("<Leave>", lambda e: clr_lbl.configure(
            fg=t["BLUE"] if self._clear_on_run.get() else t["TEXT_SUB"]))
        self._clr_lbl = clr_lbl

        tk.Button(hdr, text="📋 Copy", command=self._copy_output,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 9), cursor="hand2", bd=0,
            highlightthickness=0).pack(side="right", padx=4, pady=2)
        tk.Button(hdr, text="✕ Clear", command=self._clear_output,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 9), cursor="hand2", bd=0,
            highlightthickness=0).pack(side="right", pady=2)

        # ── Inline Input Bar (hidden by default inside output tab) ───────────
        self._input_bar = tk.Frame(self._out_frame, bg=t["BG_MANTLE"])
        self._input_prompt_lbl = tk.Label(
            self._input_bar, text="Input:", bg=t["BG_MANTLE"], fg=t["PEACH"],
            font=("Consolas", 10, "bold")
        )
        self._input_prompt_lbl.pack(side="left", padx=(8, 4), pady=4)
        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            self._input_bar, textvariable=self._input_var,
            bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"],
            insertbackground=t["FG_CURSOR"], font=("Consolas", 10),
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=t["BG_SURFACE1"], highlightcolor=t["BLUE"]
        )
        self._input_entry.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        self._input_btn = tk.Button(
            self._input_bar, text="Enter ↵",
            bg=t["BLUE"], fg=t["STATUS_FG"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
            cursor="hand2", activebackground=t["LAVENDER"], activeforeground=t["STATUS_FG"]
        )
        self._input_btn.pack(side="right", padx=(4, 8), pady=4)

        # ── Inspector (right) ────────────────────────────────────────────────
        self._insp_frame = tk.Frame(self._bottom, bg=t["BG_MANTLE"], width=260)
        self._insp_frame.pack(side="right", fill="y")
        self._insp_frame.pack_propagate(False)
        self._inspector = VariableInspector(self._insp_frame, t)
        self._inspector.pack(fill="both", expand=True)

    def _build_statusbar(self):
        t  = self.theme
        sb = tk.Frame(self.root, bg=t["STATUS_BG"], height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self._status_lang = tk.Label(sb, text="⬤ GravLang",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"],
            font=("Segoe UI", 9, "bold"), pady=3)
        self._status_lang.pack(side="left", padx=8)

        self._status_file = tk.Label(sb, text="untitled.grav",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 9), pady=3)
        self._status_file.pack(side="left", padx=4)

        self._status_stats = tk.Label(sb, text="🌐 Vars: 0 · 📦 Objects: 0",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 9), pady=3)
        self._status_stats.pack(side="left", padx=16)

        self._status_cursor = tk.Label(sb, text="Ln 1, Col 1",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 9), pady=3)
        self._status_cursor.pack(side="right", padx=8)

        self._status_lines = tk.Label(sb, text="1 line",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 9), pady=3)
        self._status_lines.pack(side="right", padx=8)

        self._status_run = tk.Label(sb, text="Ready",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 9), pady=3)
        self._status_run.pack(side="right", padx=8)

        self._statusbar = sb

    # ── TAB MANAGEMENT ────────────────────────────────────────────────────────

    def new_tab(self, filepath="", content=""):
        if hasattr(self, "_welcome_view"):
            self._welcome_view.pack_forget()
        t   = self.theme
        tab = EditorTab(self._editor_stack, t,
                        on_change_cb=self._on_editor_change,
                        on_cursor_cb=self._on_cursor_move)
        if filepath:
            tab.filepath = filepath
            tab.set_content(content)
        else:
            tab.set_content("# New GravLang file\n\n")
        self._tabs.append(tab)
        idx = len(self._tabs) - 1
        self._build_tab_label(idx)
        self.switch_tab(idx)
        return tab

    def _build_tab_label(self, idx: int):
        t    = self.theme
        tab  = self._tabs[idx]
        name = tab.name()
        frame = tk.Frame(self._tab_scroll_frame, bg=t["BG_MANTLE"],
                         cursor="hand2", padx=4)
        frame.pack(side="left", fill="y")

        # top accent line (shown when active)
        accent = tk.Frame(frame, bg=t["BLUE"], height=2)
        accent.pack(fill="x")

        inner = tk.Frame(frame, bg=t["BG_MANTLE"])
        inner.pack(fill="both", expand=True, padx=2)

        # file icon
        ext = os.path.splitext(name)[1]
        ic  = tk.Canvas(inner, width=10, height=12,
                        bg=t["BG_MANTLE"], highlightthickness=0)
        ic.create_rectangle(1, 1, 9, 11,
            fill=t["BLUE"] if ext == ".grav" else t["TEXT_SUB"], outline="")
        ic.pack(side="left", padx=2, pady=8)

        lbl = tk.Label(inner, text=name, bg=t["BG_MANTLE"],
            fg=t["TEXT_OVERLAY"], font=("Segoe UI", 10), pady=6)
        lbl.pack(side="left")

        dot = tk.Label(inner, text="●", bg=t["BG_MANTLE"],
            fg=t["PEACH"], font=("Segoe UI", 8))
        # not packed until modified

        close = tk.Label(inner, text="×", bg=t["BG_MANTLE"],
            fg=t["TEXT_OVERLAY"], font=("Segoe UI", 12), padx=4, cursor="hand2")
        close.pack(side="left")

        _frame_data = {"accent": accent, "lbl": lbl, "dot": dot, "close": close,
                       "ic": ic, "inner": inner, "frame": frame}  # FIXED: store frame ref for close_tab

        def on_click(e, t=tab):    self.switch_tab(t)
        def on_close(e, t=tab):    self.close_tab(t)
        def on_enter(e, w=frame, d=_frame_data):
            d["close"].pack(side="left")
        def on_leave(e, w=frame, d=_frame_data):
            pass  # keep close visible always for simplicity

        for w in [frame, inner, lbl, ic]:
            w.bind("<Button-1>", on_click)
        close.bind("<Button-1>", on_close)

        self._tab_labels.append(_frame_data)

    def switch_tab(self, target: int | EditorTab):
        if isinstance(target, EditorTab):
            if target not in self._tabs:
                return
            idx = self._tabs.index(target)
        else:
            idx = target

        if not (0 <= idx < len(self._tabs)):
            return

        if hasattr(self, "_welcome_view"):
            self._welcome_view.pack_forget()

        t = self.theme
        for i, tab in enumerate(self._tabs):
            tab.frame.pack_forget()
        self._active_idx = idx
        self._tabs[idx].frame.pack(fill="both", expand=True)
        self._refresh_tab_labels()
        self._update_title()
        self._update_status_file()

    def _refresh_tab_labels(self):
        t = self.theme
        for i, data in enumerate(self._tab_labels):
            active = (i == self._active_idx)
            bg  = t["BG_BASE"] if active else t["BG_MANTLE"]
            fg  = t["TEXT_MAIN"] if active else t["TEXT_OVERLAY"]
            data["lbl"].configure(bg=bg, fg=fg)
            data["inner"].configure(bg=bg)
            data["close"].configure(bg=bg)
            data["ic"].configure(bg=bg)
            data["accent"].configure(bg=t["BLUE"] if active else t["BG_MANTLE"],
                                     height=2 if active else 1)
            tab = self._tabs[i]
            if tab.modified:
                data["dot"].pack(side="left")
            else:
                data["dot"].pack_forget()

    def close_tab(self, target: int | EditorTab):
        if isinstance(target, EditorTab):
            if target not in self._tabs:
                return
            idx = self._tabs.index(target)
        else:
            idx = target

        if not (0 <= idx < len(self._tabs)):
            return

        tab = self._tabs[idx]
        if tab.modified:
            ans = messagebox.askyesnocancel("Unsaved", f"Save {tab.name()} before closing?")
            if ans is None: return
            if ans: self.save_file()

        tab.frame.destroy()
        self._tabs.pop(idx)
        lbl_data = self._tab_labels.pop(idx)
        lbl_data["frame"].destroy()  # store frame reference instead of fragile .master.master

        if len(self._tabs) == 0:
            self._active_idx = -1
            self._update_title()
            if hasattr(self, "_welcome_view"):
                self._welcome_view.set_recent_files(self._recent_files)
                self._welcome_view.pack(fill="both", expand=True)
            return

        new_idx = min(idx, len(self._tabs) - 1)
        self._active_idx = -1
        self.switch_tab(new_idx)

    def _active_tab(self) -> EditorTab | None:
        if 0 <= self._active_idx < len(self._tabs):
            return self._tabs[self._active_idx]
        return None

    def _active_editor(self) -> tk.Text | None:
        tab = self._active_tab()
        return tab.editor if tab else None

    # ── FILE OPERATIONS ───────────────────────────────────────────────────────

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("GravLang", "*.grav"), ("All", "*.*")])
        if path:
            self.open_file_path(path)

    def open_file_path(self, path: str):
        norm_path = os.path.abspath(path)
        if norm_path in self._recent_files:
            self._recent_files.remove(norm_path)
        self._recent_files.insert(0, norm_path)
        self._recent_files = self._recent_files[:10]
        self._config["recent_files"] = self._recent_files
        self._save_config()

        if hasattr(self, "_welcome_view"):
            self._welcome_view.set_recent_files(self._recent_files)
            self._welcome_view.pack_forget()

        # check if already open
        for i, tab in enumerate(self._tabs):
            if tab.filepath == path or tab.filepath == norm_path:
                self.switch_tab(i)
                return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        tab = self._active_tab()
        if tab and not tab.modified and not tab.get_content().strip():
            tab.filepath = path
            tab.set_content(content)
            self._refresh_tab_labels()
            self._update_title()
            self._update_status_file()
        else:
            self.new_tab(filepath=path, content=content)
        for i, tab in enumerate(self._tabs):
            if tab.filepath == path:
                self.switch_tab(i)
                return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        tab = self._active_tab()
        if tab and not tab.modified and not tab.get_content().strip():
            tab.filepath = path
            tab.set_content(content)
            self._refresh_tab_labels()
            self._update_title()
            self._update_status_file()
        else:
            self.new_tab(filepath=path, content=content)

    def save_file(self):
        tab = self._active_tab()
        if not tab: return
        if not tab.filepath:
            path = filedialog.asksaveasfilename(
                defaultextension=".grav",
                filetypes=[("GravLang", "*.grav"), ("All", "*.*")])
            if not path: return
            tab.filepath = path
        try:
            with open(tab.filepath, "w", encoding="utf-8") as f:
                f.write(tab.get_content())
            tab.modified = False
            self._refresh_tab_labels()
            self._update_title()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def format_code(self):
        tab = self._active_tab()
        if not tab: return
        code = tab.get_content()
        try:
            from formatter import format_source
            formatted = format_source(code)
            if formatted != code:
                tab.set_content(formatted)
                tab.modified = True
                self._update_title()
        except Exception as e:
            self._append_output(f"❌ Formatter Error: {e}\n", "error")

    # ── RUN ───────────────────────────────────────────────────────────────────

    def step_code(self):
        if getattr(self, "_is_running", False):
            self._is_stepping = True
            self._step_event.set()
        else:
            self.run_code(is_stepping=True)

    def run_code(self, is_stepping=False):
        tab = self._active_tab()
        if not tab: return
        code = tab.get_content()

        if getattr(self, "_is_running", False):
            self._is_stepping = False
            self._step_event.set()
            return
            
        self._is_stepping = is_stepping
        self._last_paused_line = -1

        # Clear output before run if the toggle is enabled
        if getattr(self, "_clear_on_run", None) and self._clear_on_run.get():
            self._clear_output()

        ts = datetime.now().strftime("%H:%M:%S")
        self._append_output(f"── Run at {ts} {'─'*30}\n", "sep")
        self._set_status_running()
        self._is_running = True
        self._cancel_flag = False
        self.root.update_idletasks()   # flush the UI so "Running…" shows up
        t_start = time.time()
        lines: list[str] = []

        def capture(*args):  # accept multiple args like print(a, b)
            text = " ".join(str(a) for a in args)
            lines.append(text)
            # Stream output live to the panel (crucial for interactive input() programs)
            self.root.after(0, lambda t=text: self._append_output(t + "\n"))

        # ── GUI input hook ─────────────────────────────────────────────────
        # Called from the background run-thread when GravLang code calls input().
        # Displays the inline input bar at the bottom of the output panel and
        # blocks until the user submits via Enter key or button click.
        def gui_input_fn(prompt=""):
            result_holder = [""]
            event = threading.Event()
            self._active_input_event = event

            def _show_inline_input():
                p_text = str(prompt) if prompt else "Input:"
                if p_text and not p_text.endswith(" ") and not p_text.endswith(":"):
                    p_text += ":"
                if prompt:
                    self._append_output(str(prompt))

                self._input_prompt_lbl.configure(text=p_text)
                self._input_var.set("")

                # Crucial: Unpack _output, pack _input_bar at bottom first, then repack _output top expand
                # This guarantees _input_bar receives height at the bottom of out_frame.
                self._output.pack_forget()
                self._input_bar.pack(side="bottom", fill="x", padx=4, pady=(0, 4))
                self._output.pack(side="top", fill="both", expand=True, padx=4, pady=4)

                self._input_entry.focus_set()
                self._input_entry.focus_force()

                def _on_output_click(evt):
                    if self._input_bar.winfo_ismapped():
                        self._input_entry.focus_set()

                self._output.bind("<Button-1>", _on_output_click)

                def _submit(evt=None):
                    answered = self._input_var.get()
                    try:
                        self._output.unbind("<Button-1>")
                    except Exception:
                        pass
                    self._input_bar.pack_forget()
                    self._input_entry.unbind("<Return>")
                    self._input_btn.configure(command=lambda: None)
                    self._active_input_event = None
                    self._append_output(answered + "\n", "")
                    result_holder[0] = answered
                    event.set()

                self._input_entry.bind("<Return>", _submit)
                self._input_btn.configure(command=_submit)

            self.root.after(0, _show_inline_input)
            event.wait()          # block run-thread until input submitted
            return result_holder[0]

        # Whether the stages window is open — captured for thread closure
        stages_open = (self._stages_win is not None and self._stages_win.is_open())
        stages_ref  = self._stages_win if stages_open else None

        if stages_ref:
            self.root.after(0, lambda: stages_ref.clear_all())
            self.root.after(0, lambda: stages_ref.set_status("⏳  Compiling…"))

        def _run_in_thread():
            lex_tokens = []
            ast_tree   = None
            trace_lines: list[tuple[str, str]] = []
            errors_out: list[str] = []
            store_out: dict = {}

            try:
                # ── Stage 1: Lexer ────────────────────────────────────────
                lex_tokens = Lexer(code).tokenize()
                if stages_ref:
                    toks_snap = list(lex_tokens)
                    self.root.after(0, lambda: stages_ref.show_tokens(toks_snap))

                # ── Stage 2: Parser ───────────────────────────────────────
                ast_tree = Parser(lex_tokens).parse()
                if stages_ref:
                    tree_snap = ast_tree
                    self.root.after(10, lambda: stages_ref.show_ast(tree_snap))

                # ── Stage 3: Interpreter (with trace) ─────────────────────
                import ast_nodes as _an
                import dataclasses

                def _on_step_hook(line, env):
                    active_tab = self._active_tab()
                    is_bp = active_tab and (line in active_tab.breakpoints)

                    if is_bp and line != self._last_paused_line:
                        self._is_stepping = True

                    if not getattr(self, "_is_stepping", False):
                        return
                    if line == self._last_paused_line:
                        return
                    if self._cancel_flag:
                        from errors import GravLangError
                        raise GravLangError("Execution stopped")
                    
                    self._last_paused_line = line
                    store = dict(env._store)
                    
                    def _update_ui():
                        self._inspector.populate(store)
                        tab = self._active_tab()
                        if tab:
                            tab.editor.tag_remove("step_highlight", "1.0", "end")
                            tab.editor.tag_add("step_highlight", f"{line}.0", f"{line}.end")
                            tab.editor.see(f"{line}.0")
                            tab.set_paused_line(line)
                        status_msg = f"⏸ Paused at line {line} (Breakpoint)" if is_bp else f"⏸ Paused at line {line}"
                        if hasattr(self, "_status_run"):
                            self._status_run.configure(text=status_msg)
                    
                    self.root.after(0, _update_ui)
                    self._step_event.clear()
                    self._step_event.wait()
                    if self._cancel_flag:
                        from errors import GravLangError
                        raise GravLangError("Execution stopped")

                if stages_ref:
                    # Wrap Interpreter to intercept variable declarations/assignments
                    orig_visit_VarDecl   = None
                    orig_visit_Assign    = None
                    orig_visit_AugAssign = None
                    orig_call            = None

                    interp = Interpreter(print_fn=capture, input_fn=gui_input_fn, source=code, on_step=_on_step_hook)

                    _orig_vd  = interp._visit_VarDecl
                    _orig_as  = interp._visit_Assign
                    _orig_aug = interp._visit_AugAssign
                    _orig_fc  = interp._visit_FuncCall
                    _orig_mc  = interp._visit_MethodCall
                    _orig_fd  = interp._visit_FuncDecl
                    _orig_cd  = interp._visit_ClassDecl

                    def _traced_vd(node, env):
                        result = _orig_vd(node, env)
                        val = env._store.get(node.name, "?")
                        trace_lines.append((f"L{node.line}  let {node.name} = {val!r}", "trace"))
                        return result

                    def _traced_as(node, env):
                        result = _orig_as(node, env)
                        try:
                            val = env.get(node.name)
                        except Exception:
                            val = "?"
                        trace_lines.append((f"L{node.line}  {node.name} = {val!r}", "kw"))
                        return result

                    def _traced_aug(node, env):
                        result = _orig_aug(node, env)
                        try:
                            val = env.get(node.name)
                        except Exception:
                            val = "?"
                        trace_lines.append((f"L{node.line}  {node.name} {node.op}= → {val!r}", "num"))
                        return result

                    def _traced_fc(node, env):
                        args = [interp._exec(a, env) for a in node.args]
                        trace_lines.append((f"L{node.line}  call {node.name}({', '.join(repr(a) for a in args)})", "type"))
                        try:
                            callee = env.get(node.name)
                        except Exception:
                            callee = None
                        from grav_builtins import register_builtins
                        from gravlang_class import GravLangClass
                        # Re-use original logic but skip double-eval of args by short-circuit
                        return _orig_fc(node, env)

                    def _traced_fd(node, env):
                        trace_lines.append((f"L{node.line}  define func {node.name}({', '.join(node.params)})", "muted"))
                        return _orig_fd(node, env)

                    def _traced_cd(node, env):
                        trace_lines.append((f"L{node.line}  define class {node.name}", "muted"))
                        return _orig_cd(node, env)

                    interp._visit_VarDecl   = _traced_vd
                    interp._visit_Assign    = _traced_as
                    interp._visit_AugAssign = _traced_aug
                    interp._visit_FuncDecl  = _traced_fd
                    interp._visit_ClassDecl = _traced_cd
                    # Note: we skip wrapping FuncCall as it would double-eval args

                else:
                    interp = Interpreter(print_fn=capture, input_fn=gui_input_fn, source=code, on_step=_on_step_hook)

                interp.interpret(ast_tree)
                elapsed = time.time() - t_start
                output_lines = list(lines)
                store_out = dict(interp.global_env._store)

                if stages_ref:
                    tl_snap = list(trace_lines)
                    self.root.after(20, lambda: stages_ref.show_trace(tl_snap))
                    self.root.after(30, lambda: stages_ref.set_status(
                        f"✓  Pipeline complete in {elapsed:.3f}s  ·  "
                        f"{len(lex_tokens)-1} tokens  ·  {len(tl_snap)} traced events"))

                self.root.after(0, lambda: self._finish_run(output_lines, [], elapsed, store_out))

            except GravLangError as e:
                elapsed = time.time() - t_start
                output_lines = list(lines)
                if stages_ref:
                    err_msg = str(e)
                    # Still show partial results
                    if lex_tokens:
                        toks_snap = list(lex_tokens)
                        self.root.after(0, lambda: stages_ref.show_tokens(toks_snap))
                    if ast_tree is not None:
                        tree_snap = ast_tree
                        self.root.after(10, lambda: stages_ref.show_ast(tree_snap))
                    tl_snap = list(trace_lines)
                    if tl_snap:
                        self.root.after(20, lambda: stages_ref.show_trace(tl_snap))
                    self.root.after(30, lambda: stages_ref.set_status(f"❌  {err_msg}"))
                self.root.after(0, lambda e=e: self._finish_run(output_lines, [str(e)], elapsed, {}))

            except Exception as e:
                elapsed = time.time() - t_start
                output_lines = list(lines)
                if stages_ref:
                    self.root.after(0, lambda e=e: stages_ref.set_status(f"❌  Internal error: {e}"))
                self.root.after(0, lambda e=e: self._finish_run(output_lines, [f"Internal error: {e}"], elapsed, {}))


        self._run_thread = threading.Thread(target=_run_in_thread, daemon=True)
        self._run_thread.start()

    def _stop_code(self):
        """Signal the running thread to stop; show cancellation message."""
        self._cancel_flag = True
        self._step_event.set()
        tab = self._active_tab()
        if tab:
            tab.set_paused_line(None)
        if hasattr(self, "_input_bar"):
            self.root.after(0, lambda: self._input_bar.pack_forget())
        if getattr(self, "_active_input_event", None):
            self._active_input_event.set()
        self._append_output("⚠ Stop requested — waiting for current operation...\n", "error")

    def _finish_run(self, lines, errors, elapsed, store):
        self._is_running = False  # clear running guard
        tab = self._active_tab()
        if tab:
            tab.editor.tag_remove("step_highlight", "1.0", "end")
            tab.set_paused_line(None)
        # NOTE: lines already streamed live by capture(); no need to replay them.
        for err in errors:
            self._append_output(f"❌ {err}\n", "error")
        if errors:
            self._append_output(f"✗ Error in {elapsed:.3f}s\n", "timing")
            self._set_status_error(elapsed)
        else:
            self._append_output(f"✓ Done in {elapsed:.3f}s\n", "timing")
            self._set_status_done(elapsed)
        if store is not None:
            self._inspector.populate(store)
            self._update_scope_stats(store)

    def _append_output(self, text: str, tag: str = ""):
        if hasattr(self, "_bottom_panel"):
            self._bottom_panel.append_output(text, tag)
        else:
            self._output.configure(state="normal")
            if tag:
                self._output.insert("end", text, tag)
            else:
                self._output.insert("end", text)
            self._output.configure(state="disabled")
            self._output.see("end")

    def _clear_output(self):
        if hasattr(self, "_bottom_panel"):
            self._bottom_panel.clear_output()
        else:
            self._output.configure(state="normal")
            self._output.delete("1.0", "end")
            self._output.configure(state="disabled")

    def _copy_output(self):
        txt = self._bottom_panel.output_txt if hasattr(self, "_bottom_panel") else self._output
        content = txt.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    # ── STATUS ────────────────────────────────────────────────────────────────

    def _set_status_running(self):
        self._is_running = True
        self._spinner_idx = 0
        self._animate_spinner()

    def _animate_spinner(self):
        if not getattr(self, "_is_running", False):
            return
        frame = SPINNER_FRAMES[self._spinner_idx % len(SPINNER_FRAMES)]
        self._spinner_idx += 1
        t = self.theme
        self._status_run.configure(
            text=f"{frame} Running...",
            bg=t["STATUS_BG"],
            fg=t["BLUE"]
        )
        self.root.after(80, self._animate_spinner)

    def _set_status_done(self, elapsed: float):
        t = self.theme
        self._is_running = False
        tab = self._active_tab()
        byte_count = len(tab.get_content().encode("utf-8")) if tab else 0
        self._status_run.configure(
            text=f"⚡ Executed in {elapsed:.3f}s · {byte_count} B",
            bg=t["STATUS_BG"],
            fg=t["GREEN"]
        )

    def _set_status_error(self, elapsed: float):
        t = self.theme
        self._is_running = False
        tab = self._active_tab()
        byte_count = len(tab.get_content().encode("utf-8")) if tab else 0
        self._status_run.configure(
            text=f"❌ Error in {elapsed:.3f}s · {byte_count} B",
            bg=t["RED"],
            fg="#1e1e2e"
        )

    def _update_scope_stats(self, store: dict | None):
        if not store:
            vars_count = 0
            obj_count = 0
        else:
            vars_count = len(store)
            obj_count = sum(
                1 for v in store.values()
                if isinstance(v, (list, dict, tuple, set)) or hasattr(v, "fields") or hasattr(v, "methods")
            )
        t = self.theme
        if hasattr(self, "_status_stats"):
            self._status_stats.configure(
                text=f"🌐 Vars: {vars_count} · 📦 Objects: {obj_count}",
                bg=t["STATUS_BG"],
                fg=t["STATUS_FG"]
            )

    def _on_cursor_move(self, row: int, col: int):
        t = self.theme
        self._status_cursor.configure(text=f"Ln {row}, Col {col}")
        ed = self._active_editor()
        if ed:
            total = int(ed.index("end-1c").split(".")[0])
            self._status_lines.configure(text=f"{total} lines")

    def _on_editor_change(self):
        self._refresh_tab_labels()
        self._update_title()
        tab = self._active_tab()
        if tab and hasattr(self, "_bottom_panel"):
            problems = [("error", line, msg) for line, msg in tab._lint_errors.items()]
            self._bottom_panel.set_problems(problems)

    def _update_title(self):
        tab  = self._active_tab()
        name = tab.name() if tab else "untitled.grav"
        mod  = " ●" if (tab and tab.modified) else ""
        self.title_lbl.configure(text=f"GravLang IDE — {name}{mod}")
        self.root.title(f"GravLang IDE — {name}{mod}")

    def _update_status_file(self):
        tab  = self._active_tab()
        name = tab.name() if tab else "untitled.grav"
        self._status_file.configure(text=name)

    # ── UI HELPERS ────────────────────────────────────────────────────────────

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self._sidebar.pack_forget()
        else:
            self._sidebar.pack(side="left", fill="y",
                               before=self._editor_pane)
        self._sidebar_visible = not self._sidebar_visible

    def _toggle_find(self):
        if self._findbar.winfo_ismapped():
            self._findbar.hide()
        else:
            self._findbar.show()

    def _minimize_window(self):
        """Minimize the window to taskbar."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
        except Exception:
            self.root.iconify()

    def _toggle_fullscreen(self):
        """Toggle maximize / restore natively."""
        self._is_maximized = not getattr(self, "_is_maximized", False)

        if self._is_maximized:
            self.root.state('zoomed')
        else:
            self.root.state('normal')

        # Update button symbol  □ ↔ ❐
        if hasattr(self, "_win_btns") and len(self._win_btns) > 1:
            sym = "❐" if self._is_maximized else "□"
            self._win_btns[1][0].configure(text=sym)

    def _show_examples(self):
        t    = self.theme
        menu = tk.Menu(self.root, tearoff=0,
            bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"],
            activebackground=t["BG_SURFACE1"],
            activeforeground=t["TEXT_MAIN"],
            font=("Segoe UI", 10), bd=0, relief="flat")
        groups = [
            ["Hello World"],
            ["Fibonacci", "FizzBuzz", "Bubble Sort"],
            ["Stack Class", "Calculator Class", "For-In Loop Demo", "Animals (Final Test)"],
        ]
        first = True
        for group in groups:
            if not first:
                menu.add_separator()
            first = False
            for name in group:
                if name in SAMPLES:
                    menu.add_command(label=name,
                        command=lambda n=name: self._load_sample(n))
        try:
            x = self._toolbar.winfo_rootx() + 200
            y = self._toolbar.winfo_rooty() + 36
            menu.post(x, y)
        except Exception:
            pass

    def _load_sample(self, name: str):
        code = SAMPLES[name]
        tab  = self._active_tab()
        if tab and not tab.get_content().strip().replace("# New GravLang file", "").strip():
            tab.set_content(code)
            tab.filepath = f"{name.lower().replace(' ','_')}.grav"
            tab.modified = False
            self._refresh_tab_labels()
            self._update_title()
        else:
            fname = f"{name.lower().replace(' ','_')}.grav"
            new_tab = self.new_tab(filepath=fname, content=code)
            new_tab.modified = False
            self._refresh_tab_labels()

    def _show_themes(self):
        t    = self.theme
        menu = tk.Menu(self.root, tearoff=0,
            bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"],
            activebackground=t["BG_SURFACE1"],
            activeforeground=t["TEXT_MAIN"],
            font=("Segoe UI", 10), bd=0, relief="flat")
        for name in THEMES:
            menu.add_command(label=("✓ " if name == self.theme_name else "  ") + name,
                command=lambda n=name: self.apply_theme(n))
        try:
            x = self.root.winfo_rootx() + self.root.winfo_width() - 160
            y = self._toolbar.winfo_rooty() + 36
            menu.post(x, y)
        except Exception:
            pass

    def apply_theme(self, name: str):
        if name not in THEMES: return
        self.theme_name = name
        self.theme = THEMES[name]
        t = self.theme
        self._save_config()
        # Update all major widgets
        self._titlebar.configure(bg=t["BG_MANTLE"])
        self.title_lbl.configure(bg=t["BG_MANTLE"], fg=t["TEXT_SUB"])
        # Re-color window control buttons
        if hasattr(self, "_win_btns"):
            for i, (btn, _, hover_bg) in enumerate(self._win_btns):
                new_normal = t["BG_MANTLE"]
                new_hover  = "#c42b1c" if i == 2 else t["BG_SURFACE0"]
                btn.configure(bg=new_normal, fg=t["TEXT_OVERLAY"])
                self._win_btns[i] = (btn, new_normal, new_hover)
                btn.bind("<Enter>", lambda e, w=btn, h=new_hover: w.configure(bg=h, fg="#ffffff"))
                btn.bind("<Leave>", lambda e, w=btn, nb=new_normal: w.configure(bg=nb, fg=t["TEXT_OVERLAY"]))
        self._tabbar.configure(bg=t["BG_MANTLE"])
        self._tab_scroll_frame.configure(bg=t["BG_MANTLE"])
        self._toolbar.configure(bg=t["BG_MANTLE"])
        self._body.configure(bg=t["BG_BASE"])
        self._outer.configure(bg=t["BG_BASE"])
        self._right.configure(bg=t["BG_BASE"])
        self._activity_bar.configure(bg=t["BG_MANTLE"])
        self._sidebar.configure(bg=t["BG_MANTLE"])
        self._editor_pane.configure(bg=t["BG_BASE"])
        self._editor_stack.configure(bg=t["BG_BASE"])
        self._statusbar.configure(bg=t["STATUS_BG"])
        for lbl in [self._status_lang, self._status_file,
                    self._status_cursor, self._status_lines, self._status_run]:
            lbl.configure(bg=t["STATUS_BG"], fg=t["STATUS_FG"])
        self._output.configure(bg=t["BG_CRUST"], fg=t["GREEN"])
        self._out_frame.configure(bg=t["BG_CRUST"])
        self._sash.configure(bg=t["BG_SURFACE1"])
        if hasattr(self, "_clr_lbl"):
            active = self._clear_on_run.get()
            self._clr_lbl.configure(
                bg=t["BG_MANTLE"],
                fg=t["BLUE"] if active else t["TEXT_SUB"],
            )
        if hasattr(self, "_input_bar"):
            self._input_bar.configure(bg=t["BG_MANTLE"])
            self._input_prompt_lbl.configure(bg=t["BG_MANTLE"], fg=t["PEACH"])
            self._input_entry.configure(
                bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"],
                insertbackground=t["FG_CURSOR"],
                highlightbackground=t["BG_SURFACE1"], highlightcolor=t["BLUE"]
            )
            self._input_btn.configure(
                bg=t["BLUE"], fg=t["STATUS_FG"],
                activebackground=t["LAVENDER"], activeforeground=t["STATUS_FG"]
            )
        for tab in self._tabs:
            tab.apply_theme(t)
        self._inspector._apply_theme(t)
        self._file_explorer._apply_theme(t)
        self._findbar._apply_theme(t)
        self._refresh_tab_labels()

    def _show_shortcuts(self):
        t   = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("Keyboard Shortcuts")
        dlg.geometry("420x500")
        dlg.configure(bg=t["BG_MANTLE"])
        dlg.transient(self.root)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Keyboard Shortcuts", bg=t["BG_MANTLE"],
            fg=t["TEXT_MAIN"], font=("Segoe UI", 14, "bold")).pack(pady=(16,8))

        frame = tk.Frame(dlg, bg=t["BG_MANTLE"])
        frame.pack(fill="both", expand=True, padx=16)

        shortcuts = [
            ("F5 / Ctrl+Enter", "Run code"),
            ("Ctrl+O",          "Open file"),
            ("Ctrl+S",          "Save file"),
            ("Ctrl+T",          "New tab"),
            ("Ctrl+W",          "Close tab"),
            ("Ctrl+Tab",        "Next tab"),
            ("Ctrl+F",          "Find"),
            ("Ctrl+H",          "Find & Replace"),
            ("Ctrl+/",          "Toggle comment"),
            ("Ctrl+D",          "Duplicate line"),
            ("Ctrl+Z",          "Undo"),
            ("Ctrl+Y",          "Redo"),
            ("Ctrl+L",          "Clear output"),
            ("Ctrl+I",          "Toggle inspector"),
            ("Tab",             "Indent / autocomplete"),
            ("Escape",          "Close find / autocomplete"),
        ]
        for key, desc in shortcuts:
            row = tk.Frame(frame, bg=t["BG_MANTLE"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, bg=t["BG_SURFACE0"], fg=t["BLUE"],
                font=("Consolas", 10), width=18, anchor="w", padx=6, pady=2
                ).pack(side="left")
            tk.Label(row, text=desc, bg=t["BG_MANTLE"], fg=t["TEXT_MAIN"],
                font=("Segoe UI", 10), padx=8
                ).pack(side="left")

        tk.Button(dlg, text="Close", command=dlg.destroy,
            bg=t["BLUE"], fg=t["BG_CRUST"], relief="flat",
            font=("Segoe UI", 10, "bold"), padx=20, pady=4, cursor="hand2"
            ).pack(pady=12)
        dlg.bind("<Escape>", lambda e: dlg.destroy())

    def _open_stages(self):
        """Open (or bring to front) the Compiler Stages window."""
        if self._stages_win and self._stages_win.is_open():
            self._stages_win.lift()
        else:
            self._stages_win = CompilerStagesWindow(self.root, self.theme)

    # ── GLOBAL BINDINGS ───────────────────────────────────────────────────────

    def _bind_global(self):
        r = self.root
        r.bind("<F5>",           lambda e: self.run_code())
        r.bind("<Control-Return>", lambda e: self.run_code())
        r.bind("<Control-o>",    lambda e: self.open_file())
        r.bind("<Control-s>",    lambda e: self.save_file())
        r.bind("<Control-t>",    lambda e: self.new_tab())
        r.bind("<Control-w>",    lambda e: self.close_tab(self._active_idx))
        r.bind("<Control-Tab>",  lambda e: self.switch_tab(
            (self._active_idx + 1) % max(1, len(self._tabs))))
        r.bind("<Control-f>",    lambda e: self._toggle_find(replace=False))
        r.bind("<Control-h>",    lambda e: self._toggle_find(replace=True))
        r.bind("<Control-l>",    lambda e: self._clear_output())
        r.bind("<Control-i>",    lambda e: self._toggle_inspector())

    def _toggle_find(self, replace: bool = False):
        """Show/hide the Find & Replace bar.

        Ctrl+F  → open (or re-focus) the Find row.
        Ctrl+H  → open the bar with focus on the Replace row.
        Pressing the shortcut again while the bar is visible hides it.
        """
        fb = self._findbar
        is_visible = fb.winfo_ismapped()

        if is_visible and not replace:
            # Already visible in find mode — toggle off
            fb.hide()
            # Return focus to the active editor
            ed = self._active_editor()
            if ed:
                ed.focus_set()
            return

        # Pre-populate the search box with any current selection
        ed = self._active_editor()
        if ed:
            try:
                sel = ed.get("sel.first", "sel.last")
                if sel and not sel.count("\n"):
                    fb.find_var.set(sel)
            except tk.TclError:
                pass

        fb.show(replace=replace)

    def _toggle_inspector(self):
        if self._inspector_visible:
            self._insp_frame.pack_forget()
        else:
            self._insp_frame.pack(side="right", fill="y")
        self._inspector_visible = not self._inspector_visible

    # ── CONFIG ────────────────────────────────────────────────────────────────

    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "theme": self.theme_name,
                    "recent_files": getattr(self, "_recent_files", []),
                }, f, indent=2)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def _hide_titlebar_windows(root: tk.Tk):
    """
    Hide the native Windows title bar using DWM/SetWindowLong WITHOUT using
    overrideredirect — so the window stays registered with the Shell and
    appears in the taskbar and Alt+Tab normally.

    Steps:
      1. Remove the WS_CAPTION and WS_THICKFRAME style bits  →  no title bar, no resize border
      2. Tell DWM the non-client area is 0 on all sides       →  no leftover chrome pixels
      3. Trigger a frame change so Windows redraws immediately
    """
    try:
        import ctypes, ctypes.wintypes

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())

        # ── Window style constants ────────────────────────────────────────────
        GWL_STYLE       = -16
        WS_CAPTION      = 0x00C00000   # title bar + border
        WS_THICKFRAME   = 0x00040000   # resizable border
        WS_MAXIMIZEBOX  = 0x00010000
        WS_MINIMIZEBOX  = 0x00020000
        WS_SYSMENU      = 0x00080000

        # Remove title bar / resize chrome
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU)
        style |= WS_MINIMIZEBOX | WS_MAXIMIZEBOX
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)

        # ── DWM: collapse non-client area to zero ─────────────────────────────
        class MARGINS(ctypes.Structure):
            _fields_ = [("left", ctypes.c_int), ("right",  ctypes.c_int),
                        ("top",  ctypes.c_int), ("bottom", ctypes.c_int)]

        margins = MARGINS(0, 0, 0, 0)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # ── Force Windows to redraw the frame ────────────────────────────────
        SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0020   # nosize|nomove|nozorder|framechanged
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)

    except Exception:
        # Fallback: overrideredirect (taskbar won't show, but window still works)
        root.overrideredirect(True)


def launch_gui():
    root = tk.Tk()
    root.title("GravLang IDE")

    # Center window on screen at startup
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 1280, 800
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    # Build UI first, THEN hide the native title bar via DWM (not overrideredirect)
    # so the window stays in the taskbar and Alt+Tab.
    app = GravLangIDE(root)
    root.update()   # ensure HWND is fully created before calling DWM
    _hide_titlebar_windows(root)

    root.mainloop()
