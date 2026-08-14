import tkinter as tk
from tkinter import ttk
from .themes import THEMES
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

def _offset_to_pos(text, offset):
    before = text[:offset]
    lines  = before.split("\n")
    return len(lines), len(lines[-1])


# ─────────────────────────────────────────────────────────────────────────────
#  AST PRETTY-PRINTER  (for the Stages panel)
# ─────────────────────────────────────────────────────────────────────────────
import ast_nodes as _ast

def _ast_to_text(node, indent=0) -> str:
    """Convert an AST node to a readable indented text representation."""
    pad = "  " * indent
    if node is None:
        return pad + "None"
    if isinstance(node, (int, float, str, bool)):
        return pad + repr(node)
    if isinstance(node, list):
        if not node:
            return pad + "[]"
        lines = [pad + "["]
        for item in node:
            lines.append(_ast_to_text(item, indent + 1))
        lines.append(pad + "]")
        return "\n".join(lines)
    # dataclass node
    name = type(node).__name__
    import dataclasses
    if not dataclasses.is_dataclass(node):
        return pad + repr(node)
    fields = dataclasses.fields(node)
    if not fields:
        return pad + name + "()"
    lines = [pad + name + " {"]
    for f in fields:
        if f.name == "line":
            continue  # skip line numbers to keep it clean
        val = getattr(node, f.name)
        child = _ast_to_text(val, indent + 1)
        # put field name on same line as the first thing
        first_line = child.lstrip()
        rest = child[len(child) - len(child.lstrip()):]
        lines.append(pad + "  " + f.name + ": " + first_line)
    lines.append(pad + "}")
    return "\n".join(lines)

class CompilerStagesWindow:
    """Floating window that shows the three compiler pipeline stages."""

    STAGE_DEFS = [
        ("1 — Lexer",       "Tokenises source code into a flat list of tokens.",       "BLUE"),
        ("2 — Parser",      "Builds an Abstract Syntax Tree (AST) from the tokens.",   "MAUVE"),
        ("3 — Interpreter", "Walks the AST and executes the program step-by-step.",    "GREEN"),
    ]

    def __init__(self, parent: tk.Tk, theme: dict):
        self.theme  = theme
        self._win   = None
        self._areas: list[tk.Text] = []  # one Text widget per stage
        self._parent = parent
        self._build()

    # ── build ────────────────────────────────────────────────────────
    def _build(self):
        t = self.theme
        win = tk.Toplevel(self._parent)
        win.title("Compiler Stages")
        win.geometry("780x600")
        win.configure(bg=t["BG_MANTLE"])
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._win = win

        # Header
        hdr = tk.Frame(win, bg=t["BG_CRUST"], height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Compiler Pipeline",
            bg=t["BG_CRUST"], fg=t["BLUE"],
            font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=8)
        tk.Label(hdr, text="Source  →  Tokens  →  AST  →  Output",
            bg=t["BG_CRUST"], fg=t["TEXT_OVERLAY"],
            font=("Segoe UI", 9)).pack(side="left", padx=4, pady=8)
        tk.Button(hdr, text="✕", command=self._on_close,
            bg=t["BG_CRUST"], fg=t["TEXT_OVERLAY"], relief="flat",
            font=("Segoe UI", 11), cursor="hand2", bd=0,
            highlightthickness=0).pack(side="right", padx=8)

        # Three stage columns side-by-side
        body = tk.Frame(win, bg=t["BG_MANTLE"])
        body.pack(fill="both", expand=True, padx=6, pady=6)

        self._areas = []
        for i, (title, desc, color_key) in enumerate(self.STAGE_DEFS):
            col = tk.Frame(body, bg=t["BG_MANTLE"])
            col.pack(side="left", fill="both", expand=True,
                     padx=(0 if i == 0 else 4, 0))

            # Stage header pill
            hd = tk.Frame(col, bg=t[color_key], height=30)
            hd.pack(fill="x")
            hd.pack_propagate(False)
            tk.Label(hd, text=title, bg=t[color_key], fg=t["BG_CRUST"],
                font=("Segoe UI", 10, "bold")).pack(side="left", padx=8, pady=4)

            # Description subtitle
            tk.Label(col, text=desc, bg=t["BG_MANTLE"], fg=t["TEXT_OVERLAY"],
                font=("Segoe UI", 8), wraplength=230, justify="left"
            ).pack(fill="x", padx=4, pady=(2, 3))

            # Separator line matching the header color
            sep = tk.Frame(col, bg=t[color_key], height=1)
            sep.pack(fill="x")

            # Scrollable text area
            frm = tk.Frame(col, bg=t["BG_BASE"])
            frm.pack(fill="both", expand=True, pady=(2, 0))
            sb = tk.Scrollbar(frm, orient="vertical")
            txt = tk.Text(
                frm,
                bg=t["BG_BASE"], fg=t["TEXT_MAIN"],
                font=("Consolas", 9),
                relief="flat", bd=0, wrap="none",
                state="disabled",
                yscrollcommand=sb.set,
            )
            sb.config(command=txt.yview)
            sb.pack(side="right", fill="y")
            txt.pack(fill="both", expand=True, padx=4, pady=4)

            # Per-stage text tags
            txt.tag_configure("header",  foreground=t[color_key], font=("Consolas", 9, "bold"))
            txt.tag_configure("kw",      foreground=t["BLUE"])
            txt.tag_configure("val",     foreground=t["GREEN"])
            txt.tag_configure("num",     foreground=t["MAUVE"])
            txt.tag_configure("type",    foreground=t["PEACH"])
            txt.tag_configure("sym",     foreground=t["TEXT_SUB"])
            txt.tag_configure("err",     foreground=t["RED"])
            txt.tag_configure("trace",   foreground=t["TEAL"])
            txt.tag_configure("muted",   foreground=t["TEXT_OVERLAY"])
            self._areas.append(txt)

        # Status bar
        self._status = tk.Label(win, text="Run your code to see the pipeline.",
            bg=t["BG_CRUST"], fg=t["TEXT_OVERLAY"],
            font=("Segoe UI", 9), anchor="w")
        self._status.pack(fill="x", padx=10, pady=(0, 4))

    # ── public API ───────────────────────────────────────────────────
    def is_open(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def _on_close(self):
        if self._win:
            self._win.destroy()
            self._win = None
            self._areas = []

    def set_status(self, msg: str):
        if self._status.winfo_exists():
            self._status.configure(text=msg)

    def clear_all(self):
        for txt in self._areas:
            self._write(txt, "", clear=True)

    # ── Stage 1 – Lexer ──────────────────────────────────────────────
    def show_tokens(self, tokens):
        if not self._areas:
            return
        txt = self._areas[0]
        self._write(txt, "", clear=True)
        t = self.theme

        # Group tokens by type for a summary header
        by_type: dict[str, int] = {}
        for tok in tokens:
            if tok.type == "EOF":
                continue
            by_type[tok.type] = by_type.get(tok.type, 0) + 1

        self._write(txt, f"  {len(tokens)-1} tokens ({len(by_type)} types)\n", "header")
        self._write(txt, "  " + "─" * 32 + "\n", "sym")

        # Color map for token families
        KW = {"LET","IF","ELIF","ELSE","WHILE","FOR","FUNC","RETURN",
              "CLASS","EXTENDS","BREAK","CONTINUE","IN","SELF","PRINT"}
        LITS = {"INT","FLOAT","STRING","TRUE","FALSE","NULL"}
        OPS  = {"PLUS","MINUS","STAR","SLASH","MOD","FLOORDIV","POWER",
                "EQ","NEQ","LT","GT","LE","GE","ASSIGN",
                "PLUS_ASSIGN","MINUS_ASSIGN","STAR_ASSIGN","SLASH_ASSIGN",
                "FLOORDIV_ASSIGN","MOD_ASSIGN","AND","OR","NOT"}

        for tok in tokens:
            if tok.type == "EOF":
                continue
            tag = "muted"
            if tok.type in KW:   tag = "kw"
            elif tok.type in LITS: tag = "val"
            elif tok.type in OPS:  tag = "num"
            else: tag = "type"

            line_num = f"{tok.line:>3}"
            type_str = f" {tok.type:<20}"
            val_str  = f" {tok.value!r}\n"
            self._write(txt, f"  L{line_num} │", "sym")
            self._write(txt, type_str, tag)
            self._write(txt, val_str, "val" if tok.type in LITS else "muted")

    # ── Stage 2 – Parser / AST ───────────────────────────────────────
    def show_ast(self, tree):
        if not self._areas or len(self._areas) < 2:
            return
        txt = self._areas[1]
        self._write(txt, "", clear=True)

        node_count = [0]
        def count_nodes(n):
            import dataclasses
            if n is None or not dataclasses.is_dataclass(n):
                return
            node_count[0] += 1
            for f in dataclasses.fields(n):
                v = getattr(n, f.name)
                if isinstance(v, list):
                    for item in v:
                        count_nodes(item)
                elif dataclasses.is_dataclass(v):
                    count_nodes(v)
        count_nodes(tree)

        self._write(txt, f"  AST — {node_count[0]} nodes\n", "header")
        self._write(txt, "  " + "─" * 32 + "\n", "sym")

        # Walk AST and write it out with indentation
        import dataclasses
        def dump_node(node, depth=0):
            pad = "  " + "│  " * depth
            if node is None:
                self._write(txt, pad + "null\n", "muted")
                return
            if isinstance(node, bool):
                self._write(txt, pad + str(node).lower() + "\n", "val")
                return
            if isinstance(node, (int, float)):
                self._write(txt, pad + str(node) + "\n", "num")
                return
            if isinstance(node, str):
                self._write(txt, pad + repr(node) + "\n", "val")
                return
            if isinstance(node, list):
                for item in node:
                    dump_node(item, depth)
                return
            if not dataclasses.is_dataclass(node):
                self._write(txt, pad + repr(node) + "\n", "muted")
                return
            name = type(node).__name__
            line_info = ""
            for f in dataclasses.fields(node):
                if f.name == "line":
                    line_info = f" L{getattr(node, f.name)}"
            self._write(txt, pad + "┌ ", "sym")
            self._write(txt, name, "type")
            self._write(txt, line_info + "\n", "muted")
            for f in dataclasses.fields(node):
                if f.name == "line":
                    continue
                v = getattr(node, f.name)
                if v is None or (isinstance(v, list) and not v):
                    continue
                self._write(txt, pad + "│ ", "sym")
                self._write(txt, f.name + ": ", "kw")
                if isinstance(v, list) or dataclasses.is_dataclass(v):
                    self._write(txt, "\n", "")
                    dump_node(v, depth + 1)
                else:
                    self._write(txt, repr(v) + "\n", "val")

        if tree and hasattr(tree, "body"):
            for stmt in tree.body:
                dump_node(stmt, 0)
                self._write(txt, "\n", "")

    # ── Stage 3 – Interpreter trace ──────────────────────────────────
    def show_trace(self, trace_lines: list[tuple[str, str]]):
        """trace_lines = [(text, tag), ...]"""
        if not self._areas or len(self._areas) < 3:
            return
        txt = self._areas[2]
        self._write(txt, "", clear=True)
        self._write(txt, f"  Execution trace ({len(trace_lines)} events)\n", "header")
        self._write(txt, "  " + "─" * 32 + "\n", "sym")
        for line, tag in trace_lines:
            self._write(txt, "  " + line + "\n", tag or "muted")

    # ── helpers ──────────────────────────────────────────────────────
    def _write(self, txt: tk.Text, content: str, tag: str = "", clear=False):
        txt.configure(state="normal")
        if clear:
            txt.delete("1.0", "end")
        if content:
            if tag:
                txt.insert("end", content, tag)
            else:
                txt.insert("end", content)
        txt.configure(state="disabled")
        if not clear:
            txt.see("end")

    def lift(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
