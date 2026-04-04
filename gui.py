"""
GravLang IDE — VS Code–style GUI
Built with Python 3.10+ / tkinter only
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, json, time, threading, re
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  TRY to import GravLang components; fall back to stubs for standalone testing
# ─────────────────────────────────────────────────────────────────────────────
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
        def __init__(self, print_fn=None, source=""):
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


# ─────────────────────────────────────────────────────────────────────────────
#  THEMES
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "Catppuccin Mocha": dict(
        BG_BASE="#1e1e2e", BG_MANTLE="#181825", BG_CRUST="#11111b",
        BG_SURFACE0="#313244", BG_SURFACE1="#45475a",
        TEXT_MAIN="#cdd6f4", TEXT_SUB="#585b70", TEXT_OVERLAY="#7f849c",
        BLUE="#89b4fa", TEAL="#94e2d5", GREEN="#a6e3a1",
        MAUVE="#cba6f7", PEACH="#fab387", RED="#f38ba8", LAVENDER="#b4befe",
        STATUS_BG="#89b4fa", STATUS_FG="#1e1e2e",
        FG_CURSOR="#f5e0dc",
    ),
    "GitHub Dark": dict(
        BG_BASE="#0d1117", BG_MANTLE="#161b22", BG_CRUST="#010409",
        BG_SURFACE0="#21262d", BG_SURFACE1="#30363d",
        TEXT_MAIN="#e6edf3", TEXT_SUB="#484f58", TEXT_OVERLAY="#8b949e",
        BLUE="#79c0ff", TEAL="#39d353", GREEN="#3fb950",
        MAUVE="#d2a8ff", PEACH="#ffa657", RED="#ff7b72", LAVENDER="#a5d6ff",
        STATUS_BG="#1f6feb", STATUS_FG="#ffffff",
        FG_CURSOR="#f0f6fc",
    ),
    "Solarized Dark": dict(
        BG_BASE="#002b36", BG_MANTLE="#073642", BG_CRUST="#001f27",
        BG_SURFACE0="#094652", BG_SURFACE1="#0a5160",
        TEXT_MAIN="#839496", TEXT_SUB="#3d6b74", TEXT_OVERLAY="#586e75",
        BLUE="#268bd2", TEAL="#2aa198", GREEN="#859900",
        MAUVE="#6c71c4", PEACH="#cb4b16", RED="#dc322f", LAVENDER="#b58900",
        STATUS_BG="#268bd2", STATUS_FG="#fdf6e3",
        FG_CURSOR="#fdf6e3",
    ),
    "Catppuccin Latte": dict(
        BG_BASE="#eff1f5", BG_MANTLE="#e6e9ef", BG_CRUST="#dce0e8",
        BG_SURFACE0="#ccd0da", BG_SURFACE1="#bcc0cc",
        TEXT_MAIN="#4c4f69", TEXT_SUB="#9ca0b0", TEXT_OVERLAY="#8c8fa1",
        BLUE="#1e66f5", TEAL="#179299", GREEN="#40a02b",
        MAUVE="#8839ef", PEACH="#fe640b", RED="#d20f39", LAVENDER="#7287fd",
        STATUS_BG="#1e66f5", STATUS_FG="#eff1f5",
        FG_CURSOR="#4c4f69",
    ),
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".gravlang_config.json")

# ─────────────────────────────────────────────────────────────────────────────
#  SAMPLE PROGRAMS
# ─────────────────────────────────────────────────────────────────────────────
SAMPLES = {
    "Hello World": '# Hello World\nprint("Hello, World!");\n',

    "Fibonacci": '''\
# Fibonacci sequence
func fib(n) {
    if (n <= 1) { return n; }
    return fib(n - 1) + fib(n - 2);
}

let i = 0;
while (i < 10) {
    print(fib(i));
    i = i + 1;
}
''',
    "FizzBuzz": '''\
# FizzBuzz
let i = 1;
while (i <= 20) {
    if (i % 15 == 0) { print("FizzBuzz"); }
    elif (i % 3 == 0) { print("Fizz"); }
    elif (i % 5 == 0) { print("Buzz"); }
    else { print(i); }
    i = i + 1;
}
''',
    "Bubble Sort": '''\
# Bubble Sort
func bubbleSort(arr) {
    let n = len(arr);
    let i = 0;
    while (i < n) {
        let j = 0;
        while (j < n - i - 1) {
            if (arr[j] > arr[j + 1]) {
                let tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
            j += 1;
        }
        i += 1;
    }
    return arr;
}

let nums = [64, 34, 25, 12, 22, 11, 90];
bubbleSort(nums);
print(toString(nums));
''',
    "Stack Class": '''\
# Stack Class
class Stack {
    func init() {
        self.items = [];
    }
    func push(item) {
        push(self.items, item);
    }
    func pop() {
        return pop(self.items);
    }
    func peek() {
        return self.items[len(self.items) - 1];
    }
    func isEmpty() {
        return len(self.items) == 0;
    }
    func size() {
        return len(self.items);
    }
}

let s = Stack();
s.push(1);
s.push(2);
s.push(3);
print(s.peek());
print(s.pop());
print(s.size());
''',
    "Calculator Class": '''\
# Simple Calculator
class Calculator {
    func init() {
        self.result = 0;
    }
    func add(n) { self.result = self.result + n; return self; }
    func sub(n) { self.result = self.result - n; return self; }
    func mul(n) { self.result = self.result * n; return self; }
    func reset() { self.result = 0; return self; }
    func display() { print(self.result); }
}

let calc = Calculator();
calc.add(10).mul(3).sub(5).display();
''',
    "For-In Loop Demo": '''\
# For-In Loop demo
let fruits = ["apple", "banana", "cherry", "date"];
for (f in fruits) {
    print("Fruit: " + f);
}

let nums = [5, 3, 8, 1, 9, 2];
sort(nums);
print(toString(nums));
''',
    "Animals (Final Test)": '''\
class Animal {
    func init(name, sound) {
        self.name = name;
        self.sound = sound;
    }
    func speak() {
        print(self.name + " says " + self.sound);
    }
}

let animals = [
    Animal("Cat", "meow"),
    Animal("Dog", "woof"),
    Animal("Cow", "moo"),
];

for (a in animals) {
    a.speak();
}

let nums = [5, 3, 8, 1, 9, 2];
sort(nums);
print(toString(nums));
''',
}

# ─────────────────────────────────────────────────────────────────────────────
#  KEYWORDS for syntax highlighting
# ─────────────────────────────────────────────────────────────────────────────
KEYWORDS   = r'\b(let|if|else|while|for|in|func|return|class|extends|import|new|null|and|or|not)\b'
BUILTINS   = r'\b(print|len|type|push|pop|sort|toString|range|input|parseInt|parseFloat|append|insert|remove|keys|values|hasKey)\b'
STRINGS    = r'"(?:[^"\\]|\\.)*"'
NUMBERS    = r'\b\d+(?:\.\d+)?\b'
COMMENTS   = r'#.*'
BOOLEANS   = r'\b(true|false)\b'
SELF_KW    = r'\bself\b'
CLASS_NAME = r'(?<=class\s)\w+'
AUG_OPS    = r'(//=|%=|\+=|-=|\*=|/=)'  # FIXED: added //= and %= for syntax highlighting


# ─────────────────────────────────────────────────────────────────────────────
#  AUTO-COMPLETE POPUP
# ─────────────────────────────────────────────────────────────────────────────
class AutoCompletePopup:
    COMPLETIONS = [
        "print", "len", "type", "push", "pop", "sort", "toString",
        "range", "input", "parseInt", "parseFloat", "append",
        "let", "if", "else", "while", "for", "in", "func", "return",
        "class", "extends", "true", "false", "null", "self",
    ]

    def __init__(self, editor_widget):
        self.editor = editor_widget
        self.popup  = None
        self.listbox = None

    def show(self, x, y, prefix):
        matches = [c for c in self.COMPLETIONS if c.startswith(prefix) and c != prefix]
        if not matches:
            self.hide()
            return
        self.hide()
        self.popup = tk.Toplevel(self.editor)
        self.popup.wm_overrideredirect(True)
        self.popup.geometry(f"+{x}+{y}")
        self.popup.configure(bg="#313244")
        self.listbox = tk.Listbox(
            self.popup, bg="#313244", fg="#cdd6f4",
            selectbackground="#89b4fa", selectforeground="#1e1e2e",
            font=("Consolas", 11), relief="flat", borderwidth=1,
            highlightthickness=1, highlightbackground="#45475a",
            height=min(len(matches), 8),
        )
        self.listbox.pack()
        for m in matches:
            self.listbox.insert(tk.END, m)
        self.listbox.select_set(0)
        self.listbox.bind("<Return>",  self._accept)
        self.listbox.bind("<Tab>",     self._accept)
        self.listbox.bind("<Escape>",  lambda e: self.hide())
        self.listbox.bind("<Double-1>", self._accept)
        self.popup.bind("<FocusOut>", lambda e: self.hide())

    def _accept(self, event=None):
        if not self.listbox: return
        sel = self.listbox.curselection()
        if not sel: return
        word = self.listbox.get(sel[0])
        self.editor.event_generate("<<AutoComplete>>", data=word)
        self.hide()

    def navigate(self, direction):
        if not self.listbox: return
        cur = self.listbox.curselection()
        idx = (cur[0] if cur else -1) + direction
        idx = max(0, min(idx, self.listbox.size() - 1))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.select_set(idx)
        self.listbox.see(idx)

    def hide(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def visible(self):
        return self.popup is not None


# ─────────────────────────────────────────────────────────────────────────────
#  FIND & REPLACE BAR
# ─────────────────────────────────────────────────────────────────────────────
class FindReplaceBar(tk.Frame):
    def __init__(self, parent, editor_getter, theme, **kw):
        super().__init__(parent, **kw)
        self._editor_getter = editor_getter
        self.theme = theme
        self._matches: list = []
        self._cur_idx: int  = -1
        self._build()
        self._apply_theme(theme)

    def _build(self):
        t = self.theme
        row1 = tk.Frame(self, bg=t["BG_MANTLE"])
        row1.pack(fill="x", padx=4, pady=2)

        tk.Label(row1, text="🔍", bg=t["BG_MANTLE"], fg=t["TEXT_SUB"],
                 font=("Segoe UI", 11)).pack(side="left", padx=(4, 0))
        self.find_var = tk.StringVar()
        self.find_entry = tk.Entry(row1, textvariable=self.find_var,
            bg=t["BG_BASE"], fg=t["TEXT_MAIN"], insertbackground=t["FG_CURSOR"],
            relief="flat", font=("Consolas", 11), width=28,
            highlightthickness=1, highlightbackground=t["BG_SURFACE1"])
        self.find_entry.pack(side="left", padx=4)
        self.find_var.trace_add("write", lambda *_: self._do_find())

        self._btn(row1, "▲", self._prev_match)
        self._btn(row1, "▼", self._next_match)
        self.count_lbl = tk.Label(row1, text="", bg=t["BG_MANTLE"],
            fg=t["TEXT_SUB"], font=("Segoe UI", 10))
        self.count_lbl.pack(side="left", padx=4)
        self._btn(row1, "✕", self.hide)

        row2 = tk.Frame(self, bg=t["BG_MANTLE"])
        row2.pack(fill="x", padx=4, pady=(0, 2))
        tk.Label(row2, text="↩", bg=t["BG_MANTLE"], fg=t["TEXT_SUB"],
                 font=("Segoe UI", 11)).pack(side="left", padx=(4, 0))
        self.replace_var = tk.StringVar()
        self.replace_entry = tk.Entry(row2, textvariable=self.replace_var,
            bg=t["BG_BASE"], fg=t["TEXT_MAIN"], insertbackground=t["FG_CURSOR"],
            relief="flat", font=("Consolas", 11), width=28,
            highlightthickness=1, highlightbackground=t["BG_SURFACE1"])
        self.replace_entry.pack(side="left", padx=4)
        self._btn(row2, "Replace",     self._replace_one)
        self._btn(row2, "Replace All", self._replace_all)

        self.find_entry.bind("<Return>",  lambda e: self._next_match())
        self.find_entry.bind("<Escape>",  lambda e: self.hide())
        self.replace_entry.bind("<Escape>", lambda e: self.hide())

    def _btn(self, parent, text, cmd):
        t = self.theme
        b = tk.Button(parent, text=text, command=cmd,
            bg=t["BG_MANTLE"], fg=t["TEXT_MAIN"], relief="flat",
            font=("Segoe UI", 10), padx=6, pady=1,
            activebackground=t["BG_SURFACE0"], cursor="hand2",
            bd=0, highlightthickness=0)
        b.pack(side="left", padx=1)
        return b

    def _apply_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["BG_MANTLE"])

    def show(self, replace=False):
        self.pack(fill="x", side="top")
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")

    def hide(self):
        editor = self._editor_getter()
        if editor:
            editor.tag_remove("match_hl",  "1.0", "end")
            editor.tag_remove("match_cur", "1.0", "end")
        self.pack_forget()

    def _do_find(self):
        editor = self._editor_getter()
        if not editor: return
        editor.tag_remove("match_hl",  "1.0", "end")
        editor.tag_remove("match_cur", "1.0", "end")
        query = self.find_var.get()
        self._matches = []
        if not query:
            self.count_lbl.config(text="")
            return
        t = self.theme
        editor.tag_configure("match_hl",  background=t["PEACH"],   foreground="#1e1e2e")
        editor.tag_configure("match_cur", background=t["PEACH"],   foreground="#1e1e2e",
                                          font=("Consolas", 12, "bold"))
        start = "1.0"
        while True:
            pos = editor.search(query, start, nocase=True, stopindex="end")
            if not pos: break
            end = f"{pos}+{len(query)}c"
            editor.tag_add("match_hl", pos, end)
            self._matches.append(pos)
            start = end
        if self._matches:
            self._cur_idx = 0
            self._highlight_current()
        else:
            self._cur_idx = -1
        self._update_count()

    def _highlight_current(self):
        editor = self._editor_getter()
        if not editor or not self._matches: return
        editor.tag_remove("match_cur", "1.0", "end")
        pos = self._matches[self._cur_idx]
        q   = self.find_var.get()
        editor.tag_add("match_cur", pos, f"{pos}+{len(q)}c")
        editor.see(pos)

    def _update_count(self):
        n = len(self._matches)
        c = self._cur_idx + 1 if n else 0
        self.count_lbl.config(text=f"{c}/{n}" if n else "0/0")

    def _next_match(self):
        if not self._matches: return
        self._cur_idx = (self._cur_idx + 1) % len(self._matches)
        self._highlight_current()
        self._update_count()

    def _prev_match(self):
        if not self._matches: return
        self._cur_idx = (self._cur_idx - 1) % len(self._matches)
        self._highlight_current()
        self._update_count()

    def _replace_one(self):
        editor = self._editor_getter()
        if not editor or self._cur_idx < 0: return
        pos = self._matches[self._cur_idx]
        q   = self.find_var.get()
        r   = self.replace_var.get()
        editor.delete(pos, f"{pos}+{len(q)}c")
        editor.insert(pos, r)
        self._do_find()

    def _replace_all(self):
        editor = self._editor_getter()
        if not editor: return
        q = self.find_var.get()
        r = self.replace_var.get()
        content = editor.get("1.0", "end-1c")
        new_content = re.sub(re.escape(q), r, content, flags=re.IGNORECASE)  # FIXED: case-insensitive replace
        editor.delete("1.0", "end")
        editor.insert("1.0", new_content)
        self._do_find()


# ─────────────────────────────────────────────────────────────────────────────
#  VARIABLE INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────
class VariableInspector(tk.Frame):
    def __init__(self, parent, theme, **kw):
        super().__init__(parent, **kw)
        self.theme = theme
        self._build()
        self._apply_theme(theme)

    def _build(self):
        t = self.theme
        hdr = tk.Frame(self, bg=t["BG_MANTLE"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔬 INSPECTOR", bg=t["BG_MANTLE"],
                 fg=t["TEXT_SUB"], font=("Segoe UI", 9, "bold")).pack(
                 side="left", padx=6, pady=4)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Insp.Treeview",
            background=t["BG_MANTLE"], fieldbackground=t["BG_MANTLE"],
            foreground=t["TEXT_MAIN"], rowheight=20,
            font=("Consolas", 10))
        style.configure("Insp.Treeview.Heading",
            background=t["BG_SURFACE0"], foreground=t["TEXT_SUB"],
            font=("Segoe UI", 9, "bold"))
        style.map("Insp.Treeview",
            background=[("selected", t["BG_SURFACE1"])],
            foreground=[("selected", t["TEXT_MAIN"])])

        self.tree = ttk.Treeview(self, style="Insp.Treeview",
            columns=("Name", "Value"), show="headings", selectmode="browse")
        self.tree.heading("Name",  text="Name")
        self.tree.heading("Value", text="Value")
        self.tree.column("Name",  width=90,  minwidth=60)
        self.tree.column("Value", width=130, minwidth=80)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(fill="both", expand=True, side="left")
        sb.pack(fill="y", side="right")

    def _apply_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["BG_MANTLE"])

    def populate(self, store: dict):
        for item in self.tree.get_children():
            self.tree.delete(item)
        t = self.theme
        for name, val in sorted(store.items()):
            if callable(val) and not isinstance(val, type):  # FIXED: skip plain callables (builtins, GravFunctions)
                continue
            label, color = self._format(val)
            iid = self.tree.insert("", "end", values=(name, label))
            # tag coloring
            tag = f"type_{type(val).__name__}"
            self.tree.item(iid, tags=(tag,))
            self.tree.tag_configure(tag, foreground=color)

    def _format(self, val):
        t = self.theme
        if isinstance(val, bool):
            return str(val).lower(), t["RED"]
        if isinstance(val, int) or isinstance(val, float):
            return str(val), t["MAUVE"]
        if isinstance(val, str):
            return f'"{val}"', t["GREEN"]
        if isinstance(val, list):
            return f"[{len(val)} items]", t["MAUVE"]
        if callable(val):
            name = getattr(val, "__name__", "?")
            return f"ƒ {name}", t["PEACH"]
        cls = type(val).__name__
        return f"<{cls}>", t["PEACH"]


# ─────────────────────────────────────────────────────────────────────────────
#  FILE EXPLORER
# ─────────────────────────────────────────────────────────────────────────────
class FileExplorer(tk.Frame):
    def __init__(self, parent, theme, open_file_cb, **kw):
        super().__init__(parent, **kw)
        self.theme = theme
        self.open_file_cb = open_file_cb
        self._cwd = os.path.expanduser("~")
        self._build()
        self._apply_theme(theme)
        self.refresh()

    def _build(self):
        t = self.theme
        hdr = tk.Frame(self, bg=t["BG_MANTLE"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="EXPLORER", bg=t["BG_MANTLE"],
                 fg=t["TEXT_SUB"], font=("Segoe UI", 9, "bold")).pack(
                 side="left", padx=8, pady=5)

        style = ttk.Style()
        style.configure("Exp.Treeview",
            background=t["BG_MANTLE"], fieldbackground=t["BG_MANTLE"],
            foreground=t["TEXT_MAIN"], rowheight=22, font=("Segoe UI", 10))
        style.configure("Exp.Treeview.Heading",
            background=t["BG_MANTLE"], foreground=t["TEXT_SUB"],
            font=("Segoe UI", 9))
        style.map("Exp.Treeview",
            background=[("selected", t["BG_SURFACE0"])],
            foreground=[("selected", t["BLUE"])])

        self.tree = ttk.Treeview(self, style="Exp.Treeview", show="tree",
                                 selectmode="browse")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(fill="both", expand=True, side="left")
        sb.pack(fill="y", side="right")

        self.tree.bind("<Double-1>",   self._on_double)
        self.tree.bind("<Button-3>",   self._on_right)

        self.ctx_menu = tk.Menu(self, tearoff=0,
            bg=t["BG_SURFACE0"], fg=t["TEXT_MAIN"],
            activebackground=t["BG_SURFACE1"],
            activeforeground=t["TEXT_MAIN"], bd=0)
        self.ctx_menu.add_command(label="New File",  command=self._new_file)
        self.ctx_menu.add_command(label="Rename",    command=self._rename)
        self.ctx_menu.add_command(label="Delete",    command=self._delete)

    def _apply_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["BG_MANTLE"])

    def set_cwd(self, path):
        self._cwd = path
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            entries = sorted(os.listdir(self._cwd))
        except Exception:
            return
        folder = self.tree.insert("", "end", text=f"📁 {os.path.basename(self._cwd)}",
                                  open=True, iid="__root__")
        for name in entries:
            full = os.path.join(self._cwd, name)
            icon = "📄 " if os.path.isfile(full) else "📁 "
            self.tree.insert(folder, "end", text=icon + name, values=(full,))

    def _on_double(self, event):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        if vals:
            path = vals[0]
            if os.path.isfile(path):
                self.open_file_cb(path)

    def _on_right(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        self.ctx_menu.post(event.x_root, event.y_root)

    def _new_file(self):
        name = _simple_dialog(self.winfo_toplevel(), "New File", "Filename:")
        if name:
            full = os.path.join(self._cwd, name)
            open(full, "a", encoding="utf-8").close()
            self.refresh()

    def _rename(self):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        if not vals: return
        old = vals[0]
        new_name = _simple_dialog(self.winfo_toplevel(), "Rename", "New name:",
                                  initial=os.path.basename(old))
        if new_name:
            new_path = os.path.join(os.path.dirname(old), new_name)
            os.rename(old, new_path)
            self.refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        if not vals: return
        path = vals[0]
        if messagebox.askyesno("Delete", f"Delete {os.path.basename(path)}?"):
            try:
                os.remove(path)
            except Exception:
                pass
            self.refresh()


def _simple_dialog(parent, title, prompt, initial=""):
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg="#181825")
    dlg.resizable(False, False)
    result = [None]
    tk.Label(dlg, text=prompt, bg="#181825", fg="#cdd6f4",
             font=("Segoe UI", 10)).pack(padx=16, pady=(12, 4))
    var = tk.StringVar(value=initial)
    ent = tk.Entry(dlg, textvariable=var, bg="#1e1e2e", fg="#cdd6f4",
                   font=("Consolas", 11), relief="flat",
                   insertbackground="#f5e0dc", width=28)
    ent.pack(padx=16, pady=4)
    ent.select_range(0, "end")
    ent.focus_set()
    def ok(*_):
        result[0] = var.get()
        dlg.destroy()
    def cancel(*_):
        dlg.destroy()
    row = tk.Frame(dlg, bg="#181825")
    row.pack(pady=10)
    tk.Button(row, text="OK",     command=ok,     bg="#89b4fa", fg="#1e1e2e",
              relief="flat", font=("Segoe UI", 10, "bold"), padx=14).pack(side="left", padx=4)
    tk.Button(row, text="Cancel", command=cancel, bg="#313244", fg="#cdd6f4",
              relief="flat", font=("Segoe UI", 10), padx=10).pack(side="left", padx=4)
    ent.bind("<Return>", ok)
    ent.bind("<Escape>", cancel)
    dlg.transient(parent)
    dlg.grab_set()
    parent.wait_window(dlg)
    return result[0]


# ─────────────────────────────────────────────────────────────────────────────
#  EDITOR TAB
# ─────────────────────────────────────────────────────────────────────────────
class EditorTab:
    def __init__(self, parent_frame, theme, on_change_cb, on_cursor_cb):
        self.theme = theme
        self.filepath: str  = ""
        self.modified: bool = False
        self._on_change = on_change_cb
        self._on_cursor = on_cursor_cb
        self._autocomplete: AutoCompletePopup = None
        self._frame = tk.Frame(parent_frame, bg=theme["BG_BASE"])
        self._build()

    def _build(self):
        t = self.theme
        self.container = tk.Frame(self._frame, bg=t["BG_BASE"])
        self.container.pack(fill="both", expand=True)

        # line numbers
        self.line_frame = tk.Frame(self.container, bg=t["BG_BASE"], width=44)
        self.line_frame.pack(side="left", fill="y")
        self.line_frame.pack_propagate(False)
        self.ln_canvas = tk.Canvas(self.line_frame, bg=t["BG_BASE"],
                                   width=44, highlightthickness=0)
        self.ln_canvas.pack(fill="both", expand=True)

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

        self._autocomplete = AutoCompletePopup(self.editor)
        self.editor.bind("<<AutoComplete>>", self._accept_autocomplete)

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
        self.editor.tag_configure("keyword",   foreground=t["BLUE"])
        self.editor.tag_configure("builtin",   foreground=t["TEAL"])
        self.editor.tag_configure("string",    foreground=t["GREEN"])
        self.editor.tag_configure("number",    foreground=t["MAUVE"])
        self.editor.tag_configure("comment",   foreground=t["TEXT_SUB"])
        self.editor.tag_configure("boolean",   foreground=t["RED"])
        self.editor.tag_configure("self_kw",   foreground=t["LAVENDER"])
        self.editor.tag_configure("class_nm",  foreground=t["PEACH"])
        self.editor.tag_configure("augop",     foreground=t["MAUVE"])
        self.editor.tag_configure("active_ln", background=t["BG_SURFACE0"])
        self.editor.tag_configure("match_hl",  background=t["PEACH"], foreground="#1e1e2e")
        self.editor.tag_configure("match_cur", background=t["PEACH"], foreground="#1e1e2e",
                                  font=("Consolas", 12, "bold"))

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

    def _maybe_autocomplete(self):
        idx = self.editor.index("insert")
        row, col = idx.split(".")
        line = self.editor.get(f"{row}.0", idx)
        m = re.search(r'[a-zA-Z_]\w*$', line)
        if m and len(m.group()) >= 2:
            prefix = m.group()
            x = self.editor.winfo_rootx() + int(col) * 7
            y = self.editor.winfo_rooty() + int(row) * 18 + 24
            self._autocomplete.show(x, y, prefix)
        else:
            self._autocomplete.hide()

    def _accept_autocomplete(self, event):
        word = event.data if hasattr(event, "data") else ""
        if not word: return
        idx  = self.editor.index("insert")
        row, col = idx.split(".")
        line = self.editor.get(f"{row}.0", idx)
        m    = re.search(r'[a-zA-Z_]\w*$', line)
        if m:
            start = f"{row}.{int(col) - len(m.group())}"
            self.editor.delete(start, idx)
        self.editor.insert("insert", word)

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

    def _update_line_numbers(self):
        self.ln_canvas.delete("all")
        t = self.theme
        i = self.editor.index("@0,0")
        cur_row = self.editor.index("insert").split(".")[0]
        y = 4
        while True:
            dline = self.editor.dlineinfo(i)
            if dline is None: break
            _, dy, _, dh, _ = dline
            linenum = i.split(".")[0]
            color = t["TEXT_MAIN"] if linenum == cur_row else t["TEXT_SUB"]
            self.ln_canvas.create_text(38, dy + dh // 2,
                text=linenum, anchor="e",
                fill=color, font=("Consolas", 11))
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


# ─────────────────────────────────────────────────────────────────────────────
#  COMPILER STAGES WINDOW
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN IDE CLASS
# ─────────────────────────────────────────────────────────────────────────────
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

        self.root.configure(bg=self.theme["BG_BASE"])
        self._build_ui()
        self._bind_global()
        self.new_tab()

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
        bar = tk.Frame(self.root, bg=t["BG_MANTLE"], height=36,
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
        sep()
        btn("📂 Open",  self.open_file)
        btn("💾 Save",  self.save_file)
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
        t = self.theme
        self._findbar = FindReplaceBar(
            self.root,
            editor_getter=self._active_editor,
            theme=t, bg=t["BG_MANTLE"])
        # not packed yet — shown on demand

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
        self._editor_stack.pack(fill="both", expand=True, side="left")

    def _build_activity_bar(self):
        t   = self.theme
        bar = self._activity_bar
        icons = [("⬜", self._toggle_sidebar, True),
                 ("🔍", self._toggle_find, False)]
        self._act_btns = []
        for text, cmd, active in icons:
            btn = tk.Button(bar, text=text, command=cmd,
                bg=t["BG_MANTLE"], fg=t["BLUE"] if active else t["TEXT_SUB"],
                relief="flat", font=("Segoe UI", 14), padx=0, pady=6,
                cursor="hand2", width=3, bd=0, highlightthickness=0,
                activebackground=t["BG_SURFACE0"])
            btn.pack(fill="x", pady=2)
            self._act_btns.append(btn)

        # info at bottom
        info = tk.Button(bar, text="ⓘ", command=self._show_shortcuts,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 13), cursor="hand2", width=3, bd=0,
            highlightthickness=0, activebackground=t["BG_SURFACE0"])
        info.place(relx=0.5, rely=1.0, anchor="s", y=-6)

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

        # ── Output area (left) ───────────────────────────────────────────────
        self._out_frame = tk.Frame(self._bottom, bg=t["BG_CRUST"])
        self._out_frame.pack(side="left", fill="both", expand=True)

        hdr = tk.Frame(self._out_frame, bg=t["BG_MANTLE"], height=28)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="OUTPUT", bg=t["BG_MANTLE"], fg=t["TEXT_SUB"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=8, pady=4)

        # ── Clear on Run toggle ──────────────────────────────────────────────
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
        clr_lbl.pack(side="left", pady=4)
        clr_lbl.bind("<Button-1>", lambda e: (
            self._clear_on_run.set(not self._clear_on_run.get()),
            _toggle_clear_on_run(),
        ))
        clr_lbl.bind("<Enter>", lambda e: clr_lbl.configure(fg=t["BLUE"]))
        clr_lbl.bind("<Leave>", lambda e: clr_lbl.configure(
            fg=t["BLUE"] if self._clear_on_run.get() else t["TEXT_SUB"]))
        self._clr_lbl = clr_lbl   # keep ref for theme updates

        tk.Button(hdr, text="📋 Copy",  command=self._copy_output,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 9), cursor="hand2", bd=0,
            highlightthickness=0).pack(side="right", padx=4, pady=2)
        tk.Button(hdr, text="✕ Clear", command=self._clear_output,
            bg=t["BG_MANTLE"], fg=t["TEXT_SUB"], relief="flat",
            font=("Segoe UI", 9), cursor="hand2", bd=0,
            highlightthickness=0).pack(side="right", pady=2)

        self._output = tk.Text(self._out_frame, bg=t["BG_CRUST"],
            fg=t["GREEN"], font=("Consolas", 11), relief="flat",
            state="disabled", wrap="word", bd=0)
        self._output.pack(fill="both", expand=True, padx=4, pady=4)
        self._output.tag_configure("error",  foreground=t["RED"])
        self._output.tag_configure("timing", foreground=t["BLUE"])
        self._output.tag_configure("sep",    foreground=t["TEXT_SUB"])

        # ── Inspector (right) ────────────────────────────────────────────────
        self._insp_frame = tk.Frame(self._bottom, bg=t["BG_MANTLE"], width=260)
        self._insp_frame.pack(side="right", fill="y")
        self._insp_frame.pack_propagate(False)
        self._inspector = VariableInspector(self._insp_frame, t)
        self._inspector.pack(fill="both", expand=True)

    def _build_statusbar(self):
        t  = self.theme
        sb = tk.Frame(self.root, bg=t["STATUS_BG"], height=22)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self._status_lang = tk.Label(sb, text="⬤ GravLang",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"],
            font=("Segoe UI", 10, "bold"))
        self._status_lang.pack(side="left", padx=8)

        self._status_file = tk.Label(sb, text="untitled.grav",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 10))
        self._status_file.pack(side="left", padx=4)

        self._status_cursor = tk.Label(sb, text="Ln 1, Col 1",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 10))
        self._status_cursor.pack(side="right", padx=8)

        self._status_lines = tk.Label(sb, text="1 line",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 10))
        self._status_lines.pack(side="right", padx=8)

        self._status_run = tk.Label(sb, text="UTF-8",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"], font=("Segoe UI", 10))
        self._status_run.pack(side="right", padx=8)

        self._statusbar = sb

    # ── TAB MANAGEMENT ────────────────────────────────────────────────────────

    def new_tab(self, filepath="", content=""):
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

        def on_click(e, i=idx):    self.switch_tab(i)
        def on_close(e, i=idx):    self.close_tab(i)
        def on_enter(e, w=frame, d=_frame_data):
            d["close"].pack(side="left")
        def on_leave(e, w=frame, d=_frame_data):
            pass  # keep close visible always for simplicity

        for w in [frame, inner, lbl, ic]:
            w.bind("<Button-1>", on_click)
        close.bind("<Button-1>", on_close)

        self._tab_labels.append(_frame_data)

    def switch_tab(self, idx: int):
        t = self.theme
        for i, tab in enumerate(self._tabs):
            tab.frame.pack_forget()
        if 0 <= idx < len(self._tabs):
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

    def close_tab(self, idx: int):
        if len(self._tabs) == 1:
            self._tabs[0].set_content("")
            self._tabs[0].filepath = ""
            self._tabs[0].modified = False
            self._refresh_tab_labels()
            self._update_title()
            return
        tab = self._tabs[idx]
        if tab.modified:
            ans = messagebox.askyesnocancel("Unsaved", f"Save {tab.name()} before closing?")
            if ans is None: return
            if ans: self.save_file()
        tab.frame.destroy()
        self._tabs.pop(idx)
        lbl_data = self._tab_labels.pop(idx)
        lbl_data["frame"].destroy()  # FIXED: use stored frame reference instead of fragile .master.master
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
        # check if already open
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
            self._file_explorer.set_cwd(os.path.dirname(path))
        else:
            self.new_tab(filepath=path, content=content)
            self._file_explorer.set_cwd(os.path.dirname(path))

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

    # ── RUN ───────────────────────────────────────────────────────────────────

    def run_code(self):
        tab = self._active_tab()
        if not tab: return
        code = tab.get_content()

        # Clear output before run if the toggle is enabled
        if getattr(self, "_clear_on_run", None) and self._clear_on_run.get():
            self._clear_output()

        ts = datetime.now().strftime("%H:%M:%S")
        self._append_output(f"── Run at {ts} {'─'*30}\n", "sep")
        self._set_status_running()
        # Guard: don't start a second run if one is already running
        if getattr(self, "_is_running", False):
            return
        self._is_running = True
        self._cancel_flag = False
        self.root.update_idletasks()   # flush the UI so "Running…" shows up

        t_start = time.time()
        lines: list[str] = []

        def capture(*args):  # accept multiple args like print(a, b)
            lines.append(" ".join(str(a) for a in args))

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

                if stages_ref:
                    # Wrap Interpreter to intercept variable declarations/assignments
                    orig_visit_VarDecl   = None
                    orig_visit_Assign    = None
                    orig_visit_AugAssign = None
                    orig_call            = None

                    interp = Interpreter(print_fn=capture, source=code)

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
                    interp = Interpreter(print_fn=capture, source=code)

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
                self.root.after(0, lambda: self._finish_run(output_lines, [str(e)], elapsed, {}))

            except Exception as e:
                elapsed = time.time() - t_start
                output_lines = list(lines)
                if stages_ref:
                    self.root.after(0, lambda: stages_ref.set_status(f"❌  Internal error: {e}"))
                self.root.after(0, lambda: self._finish_run(output_lines, [f"Internal error: {e}"], elapsed, {}))

        self._run_thread = threading.Thread(target=_run_in_thread, daemon=True)
        self._run_thread.start()

    def _stop_code(self):
        """Signal the running thread to stop; show cancellation message."""
        self._cancel_flag = True
        # Don't call _finish_run directly — the thread will call it via root.after.
        # Just show a message immediately and let the thread clean up.
        self._append_output("⚠ Stop requested — waiting for current operation...\n", "error")

    def _finish_run(self, lines, errors, elapsed, store):
        self._is_running = False  # clear running guard
        for line in lines:
            self._append_output(line + "\n")
        for err in errors:
            self._append_output(f"❌ {err}\n", "error")
        if errors:
            self._append_output(f"✗ Error in {elapsed:.3f}s\n", "timing")
            self._set_status_error(elapsed)
        else:
            self._append_output(f"✓ Done in {elapsed:.3f}s\n", "timing")
            self._set_status_done(elapsed)
        if store:
            self._inspector.populate(store)

    def _append_output(self, text: str, tag: str = ""):
        self._output.configure(state="normal")
        if tag:
            self._output.insert("end", text, tag)
        else:
            self._output.insert("end", text)
        self._output.configure(state="disabled")
        self._output.see("end")

    def _clear_output(self):
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")

    def _copy_output(self):
        content = self._output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    # ── STATUS ────────────────────────────────────────────────────────────────

    def _set_status_running(self):
        t = self.theme
        self._status_run.configure(text="⏳ Running...",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"])

    def _set_status_done(self, elapsed):
        t = self.theme
        self._status_run.configure(text=f"✓ Done in {elapsed:.3f}s",
            bg=t["STATUS_BG"], fg=t["STATUS_FG"])

    def _set_status_error(self, elapsed):
        t = self.theme
        self._status_run.configure(text=f"✗ Error {elapsed:.3f}s",
            bg=t["RED"], fg="#1e1e2e")

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
        """Toggle maximize / restore using geometry only — no ctypes, no glitches."""
        self._is_maximized = not getattr(self, "_is_maximized", False)

        if self._is_maximized:
            self._prev_geometry = self.root.geometry()
            # Get usable screen area (excludes taskbar on most systems)
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            # Place at 0,0 with full screen size; taskbar sits on top naturally
            self.root.geometry(f"{sw}x{sh}+0+0")
        else:
            geo = getattr(self, "_prev_geometry", "1280x800+100+100")
            self.root.geometry(geo)

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
        r.bind("<Control-f>",    lambda e: self._toggle_find())
        r.bind("<Control-h>",    lambda e: self._toggle_find())
        r.bind("<Control-l>",    lambda e: self._clear_output())
        r.bind("<Control-i>",    lambda e: self._toggle_inspector())

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
                json.dump({"theme": self.theme_name}, f)
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

        # Remove title bar / resize chrome (keep WS_MINIMIZEBOX so taskbar btn works)
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MAXIMIZEBOX | WS_SYSMENU)
        style |= WS_MINIMIZEBOX          # keep so Win+D / taskbar click restores
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


if __name__ == "__main__":
    launch_gui()
