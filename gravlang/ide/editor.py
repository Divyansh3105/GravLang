import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import threading
from .constants import *
from .constants import _AC_KEYWORDS, _AC_BUILTINS
from .themes import THEMES
from .components import LintTooltip, AutoCompletePopup, FindReplaceBar
from .compiler_view import _offset_to_pos
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    HAS_GRAVLANG: bool = True
    from ..core.lexer import Lexer
    from ..core.parser import Parser
    from ..core.interpreter import Interpreter
    from ..core.errors import GravLangError
else:
    try:
        from ..core.lexer import Lexer
        from ..core.parser import Parser
        from ..core.interpreter import Interpreter
        from ..core.errors import GravLangError
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

class EditorTab:
    _autocomplete: AutoCompletePopup

    def __init__(self, parent_frame, theme, on_change_cb, on_cursor_cb):
        self.theme = theme
        self.filepath: str  = ""
        self.modified: bool = False
        self._on_change = on_change_cb
        self._on_cursor = on_cursor_cb
        self.breakpoints: set[int] = set()
        self.paused_line: int | None = None
        self.folded_blocks: set[int] = set()
        self._frame = tk.Frame(parent_frame, bg=theme["BG_BASE"])
        self._build()

    def _build(self):
        t = self.theme
        self.container = tk.Frame(self._frame, bg=t["BG_BASE"])
        self.container.pack(fill="both", expand=True)

        # line numbers & gutter
        self.line_frame = tk.Frame(self.container, bg=t["BG_BASE"], width=58)
        self.line_frame.pack(side="left", fill="y")
        self.line_frame.pack_propagate(False)
        self.ln_canvas = tk.Canvas(self.line_frame, bg=t["BG_BASE"],
                                   width=58, highlightthickness=0, cursor="hand2")
        self.ln_canvas.pack(fill="both", expand=True)
        self.ln_canvas.bind("<Button-1>", self._on_gutter_click)

        # editor
        self.editor = tk.Text(
            self.container,
            bg=t["BG_BASE"], fg=t["TEXT_MAIN"],
            insertbackground=t["FG_CURSOR"],
            selectbackground=t["BG_SURFACE1"],
            selectforeground=t["TEXT_MAIN"],
            font=("Consolas", 12),
            relief="flat", bd=0, wrap="none",
            undo=True,
            tabs=("40p",),
        )
        self.vsb = tk.Scrollbar(self.container, orient="vertical",
                                command=self._on_yscroll)
        self.hsb = tk.Scrollbar(self._frame, orient="horizontal",
                                command=self.editor.xview)
        self.editor.configure(yscrollcommand=self._on_yscroll_set,
                              xscrollcommand=self.hsb.set)
        self.hsb.pack(side="bottom", fill="x")
        self.vsb.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True, side="left")

        self._autocomplete = AutoCompletePopup(
            self.editor, self.theme, on_accept=self._insert_completion
        )

        # ── Linting state ────────────────────────────────────────────────────
        self._lint_timer:  threading.Timer | None = None   # debounce handle
        self._lint_errors: dict[int, str]         = {}     # line -> message
        # Tooltip lives on the root window (shared across all tabs would be
        # fine, but per-tab is simpler since each tab has its own editor)
        _root = self._frame.winfo_toplevel()
        self._lint_tooltip = LintTooltip(_root, self.theme)

        self._setup_tags()
        self._setup_bindings()
        self._update_line_numbers()

    def _on_yscroll(self, *args):
        self.editor.yview(*args)
        self._update_line_numbers()

    def _on_yscroll_set(self, lo, hi):
        self.vsb.set(lo, hi)
        self._update_line_numbers()

    def _setup_tags(self):
        t = self.theme
        self.editor.tag_configure("keyword",        foreground=t["BLUE"])
        self.editor.tag_configure("builtin",        foreground=t["TEAL"])
        self.editor.tag_configure("string",         foreground=t["GREEN"])
        self.editor.tag_configure("number",         foreground=t["MAUVE"])
        self.editor.tag_configure("comment",        foreground=t["TEXT_SUB"])
        self.editor.tag_configure("boolean",        foreground=t["RED"])
        self.editor.tag_configure("self_kw",        foreground=t["LAVENDER"])
        self.editor.tag_configure("class_nm",       foreground=t["PEACH"])
        self.editor.tag_configure("augop",          foreground=t["MAUVE"])
        self.editor.tag_configure("active_ln",      background=t["BG_SURFACE0"])
        self.editor.tag_configure("step_highlight", background=t["LAVENDER"], foreground=t["BG_BASE"])
        self.editor.tag_configure("folded_hidden",  elide=True)
        self.editor.tag_configure("match_hl",       background=t["PEACH"], foreground="#1e1e2e")
        self.editor.tag_configure("match_cur",      background=t["PEACH"], foreground="#1e1e2e",
                                  font=("Consolas", 12, "bold"))
        # Error squiggle: red underline only — text colour stays as-is
        self.editor.tag_configure(
            "error_squiggle",
            underline=True,
            underlinefg=t["RED"],   # Tk 9 / Python 3.12+ coloured underline
        )
        # error_squiggle must render on top of syntax tags
        self.editor.tag_raise("error_squiggle")

    def _setup_bindings(self):
        ed = self.editor
        ed.bind("<KeyRelease>",     self._on_key_release)
        ed.bind("<ButtonRelease>",  self._on_cursor_move)
        ed.bind("<Return>",         self._on_return)
        ed.bind("<Tab>",            self._on_tab)
        ed.bind("(", lambda e: self._auto_close("(", ")"))
        ed.bind("[", lambda e: self._auto_close("[", "]"))
        ed.bind("{", lambda e: self._auto_close("{", "}"))
        ed.bind('"', lambda e: self._auto_close('"', '"'))
        ed.bind("<Control-slash>",  self._toggle_comment)
        ed.bind("<Control-d>",      self._duplicate_line)
        ed.bind("<Up>",    self._ac_up)
        ed.bind("<Down>",  self._ac_down)
        ed.bind("<Escape>", lambda e: self._autocomplete.hide())
        ed.bind("<Control-space>",  self._force_autocomplete)
        ed.bind("<Motion>",         self._on_editor_motion)
        ed.bind("<Leave>",          lambda e: self._lint_tooltip.hide())

    def _on_key_release(self, event):
        if event.keysym in ("Up","Down","Left","Right","Escape"):
            self._on_cursor_move(event)
            return
        if event.keysym not in ("Return","Tab","space","BackSpace"):
            self._maybe_autocomplete()
        self._on_change()
        self.modified = True
        self._highlight()
        self._update_line_numbers()
        self._on_cursor_move(event)
        # Take a source snapshot on the main thread so the worker is safe
        self._lint_source_snap = self.editor.get("1.0", "end-1c")
        self._start_lint_timer()

    def _on_cursor_move(self, event=None):
        pos = self.editor.index("insert")
        row, col = pos.split(".")
        self._on_cursor(int(row), int(col) + 1)

    def _on_return(self, event):
        self._autocomplete.hide()
        idx = self.editor.index("insert")
        line_start = f"{idx.split('.')[0]}.0"
        line_text  = self.editor.get(line_start, idx)
        indent = len(line_text) - len(line_text.lstrip())
        stripped = line_text.strip()
        extra = 4 if stripped.endswith("{") else 0
        self.editor.insert(idx, "\n" + " " * (indent + extra))
        return "break"

    def _on_tab(self, event):
        if self._autocomplete.visible():
            self._autocomplete._accept()
            return "break"
        self.editor.insert("insert", "    ")
        return "break"

    def _ac_up(self, event):
        if self._autocomplete.visible():
            self._autocomplete.navigate(-1)
            return "break"

    def _ac_down(self, event):
        if self._autocomplete.visible():
            self._autocomplete.navigate(1)
            return "break"

    # ── Autocomplete helpers ───────────────────────────────────────────────────

    def _collect_user_symbols(self) -> list[str]:
        """Scan the editor content and return user-defined identifiers.

        Extracts names after ``let``, ``func``, ``class``, and plain
        identifiers so that variables declared earlier in the file appear
        in the completion list.
        """
        content = self.editor.get("1.0", "end-1c")
        symbols: set[str] = set()
        # Explicitly declared names
        for m in re.finditer(r'\b(?:let|func|class)\s+([A-Za-z_]\w*)', content):
            symbols.add(m.group(1))
        # All identifiers ≥ 3 chars (catches method names, loop vars, etc.)
        for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]{2,})\b', content):
            word = m.group(1)
            # Skip words already in static lists to avoid duplication
            if word not in _AC_KEYWORDS and word not in _AC_BUILTINS:
                symbols.add(word)
        return sorted(symbols)

    def _get_current_prefix(self) -> str:
        """Return the identifier fragment immediately before the cursor."""
        idx  = self.editor.index("insert")
        row, col = idx.split(".")
        line = self.editor.get(f"{row}.0", idx)
        m = re.search(r'[A-Za-z_]\w*$', line)
        return m.group() if m else ""

    def _maybe_autocomplete(self):
        """Auto-trigger the popup if the current prefix is ≥ 2 chars."""
        prefix = self._get_current_prefix()
        if len(prefix) >= 2:
            self._autocomplete.show(prefix, self._collect_user_symbols())
        else:
            self._autocomplete.hide()

    def _force_autocomplete(self, event=None):
        """Ctrl+Space: show autocomplete regardless of prefix length."""
        prefix = self._get_current_prefix()
        self._autocomplete.show(prefix, self._collect_user_symbols())
        return "break"

    def _insert_completion(self, word: str):
        """Insert the chosen completion word, replacing the typed prefix."""
        if not word:
            return
        idx      = self.editor.index("insert")
        row, col = idx.split(".")
        line     = self.editor.get(f"{row}.0", idx)
        m        = re.search(r'[A-Za-z_]\w*$', line)
        if m:
            start = f"{row}.{int(col) - len(m.group())}"
            self.editor.delete(start, idx)
        self.editor.insert("insert", word)
        self.editor.focus_set()  # ensure editor regains focus after popup closes
        self._highlight()

    def _auto_close(self, open_ch, close_ch):
        self.editor.insert("insert", open_ch + close_ch)
        pos = self.editor.index("insert")
        row, col = pos.split(".")
        self.editor.mark_set("insert", f"{row}.{int(col)-1}")
        return "break"

    def _toggle_comment(self, event=None):
        idx  = self.editor.index("insert")
        row  = idx.split(".")[0]
        line = self.editor.get(f"{row}.0", f"{row}.end")
        if line.lstrip().startswith("#"):
            new = line.replace("# ", "", 1).replace("#", "", 1)
        else:
            new = "# " + line
        self.editor.delete(f"{row}.0", f"{row}.end")
        self.editor.insert(f"{row}.0", new)
        return "break"

    def _duplicate_line(self, event=None):
        idx  = self.editor.index("insert")
        row  = idx.split(".")[0]
        line = self.editor.get(f"{row}.0", f"{row}.end")
        self.editor.insert(f"{row}.end", "\n" + line)
        return "break"

    # ── Real-time linting ────────────────────────────────────────────────────────────

    def _start_lint_timer(self):
        """(Re-)start the 500 ms debounce timer for background linting."""
        if self._lint_timer:
            self._lint_timer.cancel()
        self._lint_timer = threading.Timer(0.5, self._run_lint)
        self._lint_timer.daemon = True
        self._lint_timer.start()

    def _run_lint(self):
        """Worker: run Lexer + Parser on a snapshot of the current source.

        Runs in a daemon thread.  Results are posted to the main thread via
        root.after() so we never touch tk widgets from a worker thread.
        """
        try:
            source = self._lint_source_snap  # snapshot captured on main thread
        except AttributeError:
            return

        error_line   = None
        error_msg    = ""

        if not HAS_GRAVLANG:
            # No runtime available: post empty results
            self._schedule_lint_apply(None, "")
            return

        try:
            tokens = Lexer(source).tokenize()
            Parser(tokens).parse()
        except Exception as exc:
            # Both LexerError and ParseError carry a .line attribute
            error_line = getattr(exc, "line", None)
            error_msg  = getattr(exc, "message", str(exc))

        self._schedule_lint_apply(error_line, error_msg)

    def _schedule_lint_apply(self, error_line, error_msg):
        """Post lint results back to the main thread."""
        try:
            # self.editor.winfo_exists() would need main thread; use tk's after()
            self.editor.after(0, lambda: self._apply_lint_results(error_line, error_msg))
        except Exception:
            pass

    def _apply_lint_results(self, error_line: int | None, error_msg: str):
        """(Main thread) Update the error_squiggle tag and store the error map."""
        ed = self.editor
        ed.tag_remove("error_squiggle", "1.0", "end")
        self._lint_errors.clear()

        if error_line and error_line >= 1:
            # Mark the entire offending line
            line_start = f"{error_line}.0"
            line_end   = f"{error_line}.end"
            content    = ed.get(line_start, line_end)
            # If line is blank, mark at least one space so the tag is visible
            if not content.strip():
                line_end = f"{error_line}.0+1c"
            ed.tag_add("error_squiggle", line_start, line_end)
            # Keep the tag raised above syntax highlighting
            try:
                ed.tag_raise("error_squiggle")
            except Exception:
                pass
            self._lint_errors[error_line] = error_msg

        if hasattr(self, "_on_change") and callable(self._on_change):
            self._on_change()

    def _on_editor_motion(self, event):
        """Show the lint tooltip only when hovering directly over squiggled text."""
        try:
            idx  = self.editor.index(f"@{event.x},{event.y}")
            tags = self.editor.tag_names(idx)
        except Exception:
            self._lint_tooltip.hide()
            return

        if "error_squiggle" in tags:
            row = int(idx.split(".")[0])
            msg = self._lint_errors.get(row, "")
            if msg:
                self._lint_tooltip.schedule(msg, event.x_root, event.y_root)
        else:
            self._lint_tooltip.hide()

    # ── Syntax highlighting ─────────────────────────────────────────────────────────

    def _highlight(self):
        ed = self.editor
        for tag in ("keyword","builtin","string","number","comment",
                    "boolean","self_kw","class_nm","augop"):
            ed.tag_remove(tag, "1.0", "end")
        content = ed.get("1.0", "end-1c")
        patterns = [
            ("comment",  COMMENTS),
            ("string",   STRINGS),
            ("boolean",  BOOLEANS),
            ("self_kw",  SELF_KW),
            ("keyword",  KEYWORDS),
            ("builtin",  BUILTINS),
            ("number",   NUMBERS),
            ("augop",    AUG_OPS),
            ("class_nm", CLASS_NAME),
        ]
        for tag, pat in patterns:
            for m in re.finditer(pat, content):
                s = m.start(); e = m.end()
                l1, c1 = _offset_to_pos(content, s)
                l2, c2 = _offset_to_pos(content, e)
                ed.tag_add(tag, f"{l1}.{c1}", f"{l2}.{c2}")
        # active line
        ed.tag_remove("active_ln", "1.0", "end")
        cur_row = ed.index("insert").split(".")[0]
        ed.tag_add("active_ln", f"{cur_row}.0", f"{cur_row}.end+1c")

    def _find_fold_ranges(self) -> dict[int, int]:
        """Scan editor content for matching block braces { ... } spanning multiple lines."""
        content = self.get_content()
        lines = content.splitlines()
        stack = []
        ranges = {}
        in_string = False
        string_char = ""
        escape = False

        for row_idx, line in enumerate(lines, start=1):
            i = 0
            while i < len(line):
                ch = line[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == string_char:
                        in_string = False
                elif ch == "#":
                    break  # comment rest of line
                elif ch in ('"', "'"):
                    in_string = True
                    string_char = ch
                elif ch == "{":
                    stack.append(row_idx)
                elif ch == "}":
                    if stack:
                        start_line = stack.pop()
                        if row_idx > start_line:
                            ranges[start_line] = row_idx
                i += 1
        return ranges

    def toggle_fold(self, start_line: int) -> bool:
        ranges = self._find_fold_ranges()
        if start_line not in ranges:
            return False
        end_line = ranges[start_line]
        ed = self.editor

        start_idx = f"{start_line + 1}.0"
        end_idx = f"{end_line}.end+1c"

        if start_line in self.folded_blocks:
            # Unfold / Expand
            ed.tag_remove("folded_hidden", start_idx, end_idx)
            self.folded_blocks.remove(start_line)
            is_folded = False
        else:
            # Fold / Collapse
            ed.tag_add("folded_hidden", start_idx, end_idx)
            self.folded_blocks.add(start_line)
            is_folded = True

        self._update_line_numbers()
        return is_folded

    def set_paused_line(self, line: int | None):
        """Set or clear the execution pointer arrow line."""
        self.paused_line = line
        self._update_line_numbers()

    def _on_gutter_click(self, event):
        try:
            idx = self.editor.index(f"@0,{event.y}")
            line = int(idx.split(".")[0])
            total_lines = int(self.editor.index("end-1c").split(".")[0])
            if not (1 <= line <= total_lines):
                return

            fold_ranges = self._find_fold_ranges()
            if event.x > 16 and line in fold_ranges:
                self.toggle_fold(line)
            else:
                self.toggle_breakpoint(line)
        except Exception:
            pass

    def toggle_breakpoint(self, line: int) -> bool:
        if line in self.breakpoints:
            self.breakpoints.remove(line)
            res = False
        else:
            self.breakpoints.add(line)
            res = True
        self._update_line_numbers()
        return res

    def clear_breakpoints(self):
        self.breakpoints.clear()
        self._update_line_numbers()

    def _update_line_numbers(self):
        self.ln_canvas.delete("all")
        t = self.theme
        i = self.editor.index("@0,0")
        cur_row = self.editor.index("insert").split(".")[0]
        red_color = t.get("RED", "#f38ba8")
        border_color = t.get("PEACH", "#f9e2af")
        yellow_color = t.get("YELLOW", "#f9e2af")
        blue_color = t.get("BLUE", "#89b4fa")
        text_sub = t.get("TEXT_SUB", "#6c7086")

        fold_ranges = self._find_fold_ranges()

        # Draw vertical gutter divider line on right edge
        canvas_h = self.ln_canvas.winfo_height() or 800
        self.ln_canvas.create_line(57, 0, 57, canvas_h, fill=t.get("BG_SURFACE0", "#313244"))

        while True:
            dline = self.editor.dlineinfo(i)
            if dline is None: break
            _, dy, _, dh, _ = dline
            linenum = i.split(".")[0]
            line_int = int(linenum)
            cy = dy + dh // 2
            is_active = (linenum == cur_row)

            # 1. Breakpoint Dot (x=8)
            if line_int in self.breakpoints:
                self.ln_canvas.create_oval(
                    4, cy - 4, 12, cy + 4,
                    fill=red_color, outline=border_color, width=1
                )

            # 2. Folding Chevron (x=20)
            if line_int in fold_ranges:
                if line_int in self.folded_blocks:
                    # Right arrow ▶ (collapsed)
                    self.ln_canvas.create_polygon(
                        17, cy - 4, 23, cy, 17, cy + 4,
                        fill=text_sub, outline=""
                    )
                else:
                    # Down arrow ▼ (expanded)
                    self.ln_canvas.create_polygon(
                        16, cy - 3, 24, cy - 3, 20, cy + 3,
                        fill=text_sub, outline=""
                    )

            # 3. Execution Pointer Arrow ➔ (x=30)
            if self.paused_line is not None and line_int == self.paused_line:
                self.ln_canvas.create_polygon(
                    26, cy - 5, 34, cy, 26, cy + 5,
                    fill=yellow_color, outline=border_color, width=1
                )

            # 4. Active Line Accent Bar (x=54..56) & Line Number Text (x=51)
            if is_active:
                color = t.get("TEXT_MAIN", "#cdd6f4")
                font = ("Consolas", 11, "bold")
                self.ln_canvas.create_rectangle(
                    54, dy + 2, 57, dy + dh - 2,
                    fill=blue_color, outline=""
                )
            else:
                color = text_sub
                font = ("Consolas", 11)

            self.ln_canvas.create_text(
                51, cy,
                text=linenum, anchor="e",
                fill=color, font=font
            )

            next_i = self.editor.index(f"{i}+1line")
            if next_i == i: break
            i = next_i

    def apply_theme(self, theme):
        self.theme = theme
        t = theme
        self.editor.configure(
            bg=t["BG_BASE"], fg=t["TEXT_MAIN"],
            insertbackground=t["FG_CURSOR"],
            selectbackground=t["BG_SURFACE1"],
        )
        self.ln_canvas.configure(bg=t["BG_BASE"])
        self.line_frame.configure(bg=t["BG_BASE"])
        self.container.configure(bg=t["BG_BASE"])
        self._frame.configure(bg=t["BG_BASE"])
        self._autocomplete.update_theme(theme)  # keep popup in sync with theme
        self._lint_tooltip.update_theme(theme)  # keep tooltip in sync with theme
        self._setup_tags()
        self._highlight()
        self._update_line_numbers()

    @property
    def frame(self):
        return self._frame

    def get_content(self):
        return self.editor.get("1.0", "end-1c")

    def set_content(self, text):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self._highlight()
        self._update_line_numbers()
        self.modified = False

    def name(self):
        return os.path.basename(self.filepath) if self.filepath else "untitled.grav"
