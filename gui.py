"""
GravLang — Tkinter GUI IDE.

Split-pane layout:
  LEFT   → code editor with line numbers and syntax highlighting
  RIGHT  → read-only output panel
  TOP    → toolbar with Run, Clear, Load, Save buttons
  BOTTOM → status bar (line:col, total lines, state)
"""

from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, font as tkfont
import re

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from errors import GravLangError


# ── Keyword sets for highlighting ────────────────────────────────────

KEYWORDS = {
    "let", "if", "elif", "else", "while", "for",
    "func", "return", "and", "or", "not", "true", "false", "print",
    "class", "extends", "self",
    "break", "continue", "null", "in",
}

BUILTINS = {
    "input", "len", "type", "toInt", "toFloat", "toString",
    "push", "pop", "remove", "contains", "reverse", "sort", "hasAttr",
}


# ── GUI Application ─────────────────────────────────────────────────

class GravLangIDE:
    """Tkinter-based IDE for GravLang."""

    # ── colour palette ──────────────────────────────────────────────
    BG_DARK   = "#1e1e2e"
    BG_PANEL  = "#181825"
    BG_EDITOR = "#1e1e2e"
    BG_OUTPUT = "#11111b"
    FG_TEXT   = "#cdd6f4"
    FG_LINENO = "#585b70"
    FG_CURSOR = "#f5e0dc"
    ACCENT    = "#89b4fa"        # blue   (keywords)
    ACCENT2   = "#a6e3a1"       # green  (output)
    ACCENT3   = "#f38ba8"       # red    (errors / booleans)
    ACCENT4   = "#fab387"       # peach  (strings)
    ACCENT5   = "#cba6f7"       # mauve  (numbers / augmented ops)
    ACCENT6   = "#94e2d5"       # teal   (builtins)
    BORDER    = "#313244"
    BTN_BG    = "#313244"
    BTN_FG    = "#cdd6f4"
    BTN_HOVER = "#45475a"

    def __init__(self, root: tk.Tk):
        self.root = root
        self._configure_root()
        self._build_toolbar()
        self._build_panes()
        self._build_status_bar()
        self._setup_tags()
        self._bind_events()
        # Initial placeholder
        self.editor.insert("1.0", "# Welcome to GravLang!\n# Write your code here and press Run.\n\n")
        self._update_line_numbers()
        self._highlight()
        self._update_status()

    # ── root window ──────────────────────────────────────────────────

    def _configure_root(self):
        self.root.title("GravLang IDE")
        self.root.configure(bg=self.BG_DARK)
        self.root.geometry("1100x650")
        self.root.minsize(800, 500)

        self.mono = tkfont.Font(family="Consolas", size=12)
        self.mono_small = tkfont.Font(family="Consolas", size=11)
        self.ui_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

    # ── toolbar ──────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=self.BG_PANEL, pady=6, padx=10)
        bar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(
            bar, text="⚛  GravLang IDE", bg=self.BG_PANEL,
            fg=self.ACCENT, font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 20))

        buttons = [
            ("▶  Run  (F5)",       self._on_run),
            ("✕  Clear  (Ctrl+L)", self._on_clear),
            ("📂  Load",           self._on_load),
            ("💾  Save",           self._on_save),
        ]
        for text, cmd in buttons:
            btn = tk.Button(
                bar, text=text, command=cmd,
                bg=self.BTN_BG, fg=self.BTN_FG,
                activebackground=self.BTN_HOVER,
                activeforeground=self.BTN_FG,
                font=self.ui_font, bd=0, padx=14, pady=4,
                cursor="hand2", relief=tk.FLAT,
            )
            btn.pack(side=tk.LEFT, padx=4)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.BTN_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.BTN_BG))

    # ── editor + output panes ────────────────────────────────────────

    def _build_panes(self):
        pane = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL,
            bg=self.BORDER, sashwidth=4, bd=0,
        )
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 0))

        # ── left: editor with line numbers ──
        left_frame = tk.Frame(pane, bg=self.BG_EDITOR)

        self.line_numbers = tk.Text(
            left_frame, width=4, bg=self.BG_PANEL, fg=self.FG_LINENO,
            font=self.mono_small, bd=0, padx=6, pady=8,
            state=tk.DISABLED, takefocus=False,
            selectbackground=self.BG_PANEL, highlightthickness=0,
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        editor_scroll = tk.Scrollbar(left_frame, bg=self.BG_DARK, troughcolor=self.BG_DARK)
        editor_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.editor = tk.Text(
            left_frame, bg=self.BG_EDITOR, fg=self.FG_TEXT,
            insertbackground=self.FG_CURSOR, font=self.mono,
            bd=0, padx=8, pady=8, wrap=tk.NONE, undo=True,
            yscrollcommand=self._sync_scroll, highlightthickness=0,
            selectbackground="#45475a",
        )
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        editor_scroll.config(command=self._on_editor_scroll)

        pane.add(left_frame, stretch="always")

        # ── right: output panel ──
        right_frame = tk.Frame(pane, bg=self.BG_OUTPUT)

        tk.Label(
            right_frame, text="OUTPUT", bg=self.BG_OUTPUT,
            fg=self.FG_LINENO, font=("Segoe UI", 9, "bold"),
            anchor="w", padx=10, pady=4,
        ).pack(fill=tk.X)

        output_scroll = tk.Scrollbar(right_frame, bg=self.BG_DARK, troughcolor=self.BG_DARK)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.output = tk.Text(
            right_frame, bg=self.BG_OUTPUT, fg=self.ACCENT2,
            font=self.mono, bd=0, padx=10, pady=6, wrap=tk.WORD,
            state=tk.DISABLED, highlightthickness=0,
            selectbackground="#45475a",
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        output_scroll.config(command=self.output.yview)
        self.output.config(yscrollcommand=output_scroll.set)

        pane.add(right_frame, stretch="always")

    # ── status bar ───────────────────────────────────────────────────

    def _build_status_bar(self):
        self.status_bar = tk.Label(
            self.root,
            text="✓ Ready",
            bg=self.BG_PANEL,
            fg=self.FG_LINENO,
            font=("Segoe UI", 9),
            anchor="w",
            padx=10,
            pady=3,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, state: str = "✓ Ready"):
        """Refresh the status bar with cursor position and line count."""
        try:
            pos = self.editor.index(tk.INSERT)
            line, col = pos.split(".")
            total = int(self.editor.index("end-1c").split(".")[0])
            self.status_bar.config(
                text=f"Line {line}, Col {int(col) + 1}  |  {total} lines  |  {state}"
            )
        except Exception:
            self.status_bar.config(text=state)

    # ── syntax highlighting tags ─────────────────────────────────────

    def _setup_tags(self):
        self.editor.tag_configure("keyword",  foreground=self.ACCENT)
        self.editor.tag_configure("builtin",  foreground=self.ACCENT6)
        self.editor.tag_configure("string",   foreground=self.ACCENT4)
        self.editor.tag_configure("number",   foreground=self.ACCENT5)
        self.editor.tag_configure("comment",  foreground=self.FG_LINENO)
        self.editor.tag_configure("boolean",  foreground=self.ACCENT3)
        self.editor.tag_configure("augop",    foreground=self.ACCENT5)

        self.output.tag_configure("error", foreground=self.ACCENT3)
        self.output.tag_configure("info",  foreground=self.FG_LINENO)

    # ── events ───────────────────────────────────────────────────────

    def _bind_events(self):
        self.editor.bind("<KeyRelease>",    lambda _e: self._on_change())
        self.editor.bind("<ButtonRelease>", lambda _e: self._update_status())
        self.editor.bind("<Return>",        lambda _e: self.root.after(1, self._on_change))
        self.editor.bind("<BackSpace>",     lambda _e: self.root.after(1, self._on_change))
        self.root.bind("<Control-Return>",  lambda _e: self._on_run())
        self.root.bind("<F5>",              lambda _e: self._on_run())
        self.root.bind("<Control-l>",       lambda _e: self._on_clear())

    def _on_change(self):
        self._update_line_numbers()
        self._highlight()
        self._update_status()

    # ── scrolling sync ───────────────────────────────────────────────

    def _sync_scroll(self, *args):
        self.line_numbers.yview_moveto(args[0])

    def _on_editor_scroll(self, *args):
        self.editor.yview(*args)
        self.line_numbers.yview(*args)

    # ── line numbers ─────────────────────────────────────────────────

    def _update_line_numbers(self):
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        line_count = int(self.editor.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.config(state=tk.DISABLED)

    # ── syntax highlighting ──────────────────────────────────────────

    def _highlight(self):
        code = self.editor.get("1.0", tk.END)
        for tag in ("keyword", "builtin", "string", "number", "comment", "boolean", "augop"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        # Comments
        for m in re.finditer(r"#[^\n]*", code):
            self._tag_match(m, "comment")
        # Strings
        for m in re.finditer(r'"(?:[^"\\]|\\.)*"', code):
            self._tag_match(m, "string")
        # Numbers
        for m in re.finditer(r"\b\d+(\.\d+)?\b", code):
            self._tag_match(m, "number")
        # Keywords
        for word in KEYWORDS:
            for m in re.finditer(rf"\b{word}\b", code):
                self._tag_match(m, "keyword")
        # Booleans (overrides keyword)
        for m in re.finditer(r"\b(true|false)\b", code):
            self._tag_match(m, "boolean")
        # Builtins
        for word in BUILTINS:
            for m in re.finditer(rf"\b{word}\b", code):
                self._tag_match(m, "builtin")
        # Augmented assignment operators
        for m in re.finditer(r"(\+=|-=|\*=|/=)", code):
            self._tag_match(m, "augop")

    def _tag_match(self, match: re.Match, tag: str):
        start = f"1.0+{match.start()}c"
        end   = f"1.0+{match.end()}c"
        self.editor.tag_add(tag, start, end)

    # ── button handlers ──────────────────────────────────────────────

    def _on_run(self):
        code = self.editor.get("1.0", tk.END).strip()
        if not code:
            return

        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self._update_status("⏳ Running...")
        self.root.update_idletasks()

        lines: list[str] = []

        def capture_print(*args):
            text = " ".join(str(a) for a in args)
            lines.append(text)

        try:
            tokens = Lexer(code).tokenize()
            tree   = Parser(tokens).parse()
            interp = Interpreter(print_fn=capture_print, source=code)
            interp.interpret(tree)

            if lines:
                self.output.insert(tk.END, "\n".join(lines) + "\n")
            else:
                self.output.insert(tk.END, "(no output)\n", "info")
            self._update_status("✓ Done")

        except GravLangError as e:
            if lines:
                self.output.insert(tk.END, "\n".join(lines) + "\n")
            self.output.insert(tk.END, f"\n❌ {e}\n", "error")
            self._update_status("✗ Error")

        except RecursionError:
            if lines:
                self.output.insert(tk.END, "\n".join(lines) + "\n")
            self.output.insert(tk.END, "\n❌ Runtime Error: Stack overflow — maximum recursion depth exceeded\n", "error")
            self._update_status("✗ Error")

        except Exception as e:
            self.output.insert(tk.END, f"\n❌ Internal error: {e}\n", "error")
            self._update_status("✗ Error")

        self.output.config(state=tk.DISABLED)

    def _on_clear(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.config(state=tk.DISABLED)
        self._update_status("✓ Ready")

    def _on_load(self):
        path = filedialog.askopenfilename(
            title="Open GravLang File",
            filetypes=[("GravLang files", "*.grav"), ("All files", "*.*")],
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", code)
            self._on_change()

    def _on_save(self):
        path = filedialog.asksaveasfilename(
            title="Save GravLang File",
            defaultextension=".grav",
            filetypes=[("GravLang files", "*.grav"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", tk.END))


def launch_gui():
    """Create and run the GravLang IDE window."""
    root = tk.Tk()
    GravLangIDE(root)
    root.mainloop()
