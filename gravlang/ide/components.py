import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import re
import os
from .constants import *
from .constants import _AC_KEYWORDS, _AC_BUILTINS, _CAT_ICON

class LintTooltip:
    """Small floating label that shows an error message near the cursor.

    Usage
    -----
    tt = LintTooltip(root, theme)
    tt.show("Unexpected token 'x'", screen_x, screen_y)
    tt.hide()
    """

    _DELAY_MS = 300   # ms to wait before showing (avoid flicker on fast moves)

    def __init__(self, root: tk.Tk | tk.Toplevel, theme: dict):
        self._root    = root
        self.theme    = theme
        self._win     = None
        self._after   = None   # pending after() id
        self._pending: tuple[str, int, int] | None = None

    def update_theme(self, theme: dict):
        self.theme = theme

    def schedule(self, message: str, sx: int, sy: int):
        """Schedule a tooltip to appear after _DELAY_MS.  Call hide() first."""
        self._cancel()
        self._pending = (message, sx, sy)
        self._after = self._root.after(self._DELAY_MS, self._show_pending)

    def _show_pending(self):
        if self._pending:
            msg, sx, sy = self._pending
            self._do_show(msg, sx, sy)

    def _do_show(self, message: str, sx: int, sy: int):
        self.hide()
        t   = self.theme
        win = tk.Toplevel(self._root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=t["RED"])
        # Outer border using frame
        frm = tk.Frame(win, bg=t["BG_CRUST"], padx=1, pady=1)
        frm.pack(fill="both", expand=True)
        lbl = tk.Label(
            frm, text=message,
            bg=t["BG_CRUST"], fg=t["RED"],
            font=("Segoe UI", 9),
            justify="left", anchor="w",
            padx=8, pady=4,
            wraplength=420,
        )
        lbl.pack()
        # Position just above cursor so it never overlaps the line being read
        win.update_idletasks()
        h = win.winfo_reqheight()
        win.geometry(f"+{sx + 12}+{sy - h - 6}")
        self._win = win

    def hide(self):
        self._cancel()
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None

    def _cancel(self):
        if self._after:
            try:
                self._root.after_cancel(self._after)
            except Exception:
                pass
            self._after  = None
            self._pending = None

class AutoCompletePopup:
    """Theme-aware autocomplete dropdown for the GravLang editor.

    Features
    --------
    * Three-tier completions: keywords  →  builtins  →  user-defined symbols.
    * Theme colours applied at popup creation time (no hardcoded palette).
    * Accurate screen position via Text.bbox() instead of pixel guessing.
    * Keyboard: Up/Down to navigate, Tab/Return to accept, Escape to dismiss.
    * Ctrl+Space to trigger manually (bound from EditorTab).
    """

    def __init__(self, editor_widget: tk.Text, theme: dict, on_accept=None):
        self.editor     = editor_widget
        self.theme      = theme
        self.popup      = None
        self.listbox    = None
        self._on_accept = on_accept  # callable(word: str) invoked when user picks an entry
        # Internal list of bare words matching the current prefix (same order as listbox)
        self._words: list[str] = []

    # ── public API ────────────────────────────────────────────────────────────

    def update_theme(self, theme: dict):
        self.theme = theme

    def show(self, prefix: str, user_symbols: list[str] | None = None):
        """Build and display the popup below the current cursor position.

        Parameters
        ----------
        prefix       : the partial word already typed
        user_symbols : extra identifiers harvested from the document
        """
        t = self.theme
        p = prefix.lower()

        # Collect matching entries per category
        seen: set[str] = set()
        entries: list[tuple[str, str, str]] = []  # (label, word, category)

        for word in _AC_KEYWORDS:
            if word.lower().startswith(p) and word != prefix:
                lbl = f"{_CAT_ICON['keyword']} {word}"
                entries.append((lbl, word, "keyword"))
                seen.add(word)

        for word in _AC_BUILTINS:
            if word.lower().startswith(p) and word not in seen:
                lbl = f"{_CAT_ICON['builtin']} {word}"
                entries.append((lbl, word, "builtin"))
                seen.add(word)

        for word in sorted(user_symbols or []):
            if word.lower().startswith(p) and word not in seen and word != prefix:
                lbl = f"{_CAT_ICON['user']} {word}"
                entries.append((lbl, word, "user"))
                seen.add(word)

        if not entries:
            self.hide()
            return

        self.hide()

        # ── Compute popup position using bbox ─────────────────────────────────
        try:
            bbox = self.editor.bbox("insert")
            if bbox:
                bx, by, _, bh = bbox
                sx = self.editor.winfo_rootx() + bx
                sy = self.editor.winfo_rooty() + by + bh + 2
            else:
                raise ValueError("no bbox")
        except Exception:
            sx = self.editor.winfo_rootx() + 40
            sy = self.editor.winfo_rooty() + 40

        # ── Build Toplevel ────────────────────────────────────────────────────
        self.popup = tk.Toplevel(self.editor)
        self.popup.wm_overrideredirect(True)
        self.popup.configure(bg=t["BG_SURFACE0"])

        # Thin border frame
        border = tk.Frame(self.popup, bg=t["BG_SURFACE1"], padx=1, pady=1)
        border.pack(fill="both", expand=True)

        self._words = [word for _, word, _ in entries]
        labels      = [lbl  for lbl,  _, _ in entries]
        cats        = [cat  for _,    _, cat in entries]

        self.listbox = tk.Listbox(
            border,
            bg=t["BG_SURFACE0"],
            fg=t["TEXT_MAIN"],
            selectbackground=t["BLUE"],
            selectforeground=t["BG_CRUST"],
            font=("Consolas", 11),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            height=min(len(entries), 9),
            activestyle="none",
        )
        self.listbox.pack(fill="both", expand=True)

        # Insert items with per-category foreground colours
        cat_colors = {
            "keyword": t["BLUE"],
            "builtin": t["TEAL"],
            "user":    t["TEXT_MAIN"],
        }
        for lbl, cat in zip(labels, cats):
            self.listbox.insert(tk.END, lbl)
            tag = f"ac_{cat}"
            self.listbox.itemconfigure(tk.END, foreground=cat_colors[cat])

        self.listbox.select_set(0)
        self.listbox.bind("<Return>",   self._accept)
        self.listbox.bind("<Tab>",      self._accept)
        self.listbox.bind("<Escape>",   lambda e: self.hide())
        self.listbox.bind("<Double-1>", self._accept)
        # Keep editor focus – don't grab; just close on editor focus-out handled externally
        self.popup.bind("<FocusOut>",  self._on_focus_out)

        self.popup.geometry(f"+{sx}+{sy}")
        self.popup.lift()
        self.popup.attributes("-topmost", True)

    def _on_focus_out(self, event):
        # Only hide if focus moved outside of both popup and its listbox
        if not self.popup:
            self.hide()
            return
        try:
            fw = self.popup.focus_get()
            if fw and (fw == self.popup or fw == self.listbox):
                return
        except Exception:
            pass
        self.hide()

    def _accept(self, event=None):
        if not self.listbox: return
        sel = self.listbox.curselection()
        if not sel: return
        word = self._words[sel[0]]
        self.hide()  # hide first so the editor is clean before insertion
        if self._on_accept:
            self._on_accept(word)
        return "break"

    def navigate(self, direction: int):
        if not self.listbox: return
        cur = self.listbox.curselection()
        idx = (cur[0] if cur else -1) + direction
        idx = max(0, min(idx, self.listbox.size() - 1))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.select_set(idx)
        self.listbox.see(idx)

    def hide(self):
        if self.popup:
            try:
                self.popup.destroy()
            except Exception:
                pass
            self.popup   = None
            self.listbox = None
            self._words  = []

    def visible(self) -> bool:
        return self.popup is not None

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

    def show(self, replace: bool = False):
        """Show the bar.  If replace=True, focus the replace entry."""
        self.pack(fill="x", side="bottom")
        if replace:
            self.replace_entry.focus_set()
            self.replace_entry.select_range(0, "end")
        else:
            self.find_entry.focus_set()
            self.find_entry.select_range(0, "end")
        self._do_find()

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

class FileExplorer(tk.Frame):
    def __init__(self, parent, theme, open_file_cb, **kw):
        super().__init__(parent, **kw)
        self.theme = theme
        self.open_file_cb = open_file_cb
        self._cwd = os.getcwd()
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
            foreground=t["TEXT_MAIN"], rowheight=28, font=("Segoe UI", 10))
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
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)

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
        root_node = self.tree.insert("", "end", text=f" 🖿 {os.path.basename(self._cwd)}",
                                  open=True, iid="__root__", values=(self._cwd,))
        self._populate_node(root_node, self._cwd)

    def _populate_node(self, parent_node, path):
        # Remove any existing children (e.g. dummy nodes)
        for child in self.tree.get_children(parent_node):
            self.tree.delete(child)
        try:
            entries = sorted(os.listdir(path))
        except Exception:
            return
            
        dirs = []
        files = []
        for name in entries:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                dirs.append(name)
            else:
                files.append(name)
                
        for name in dirs:
            full = os.path.join(path, name)
            node = self.tree.insert(parent_node, "end", text=" 🖿 " + name, values=(full,))
            # Insert a dummy child to show the expansion arrow
            self.tree.insert(node, "end", text="dummy")
            
        for name in files:
            full = os.path.join(path, name)
            self.tree.insert(parent_node, "end", text=" 🖹 " + name, values=(full,))

    def _on_tree_open(self, event):
        node = self.tree.focus()
        vals = self.tree.item(node, "values")
        if vals:
            path = vals[0]
            if os.path.isdir(path):
                children = self.tree.get_children(node)
                if len(children) == 1 and self.tree.item(children[0], "text") == "dummy":
                    self._populate_node(node, path)

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
    result: list[str | None] = [None]
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
