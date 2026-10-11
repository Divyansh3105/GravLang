"""Regression tests for the high-severity bugs found in the codebase audit."""

import dataclasses
import tkinter as tk
from types import SimpleNamespace
from unittest import mock

import pytest

from gravlang.core.errors import GravLangError
from gravlang.core.formatter import format_source
from gravlang.core.lexer import Lexer
from gravlang.core.parser import Parser
from gravlang.ide.editor import EditorTab
from gravlang.ide.themes import THEMES
from helpers import run_grav


def _shape(n):
    if dataclasses.is_dataclass(n):
        return (type(n).__name__, tuple(_shape(getattr(n, f.name))
                for f in dataclasses.fields(n) if f.name not in ("line", "end_line")))
    if isinstance(n, (list, tuple)):
        return tuple(_shape(x) for x in n)
    return n


def _ast(src):
    return _shape(Parser(Lexer(src).tokenize()).parse())


# ── interpreter ──────────────────────────────────────────────────────

def test_loop_else_skipped_on_return_and_error():
    assert run_grav('func f(){ while(true){ return 1; } else { print("E"); } } print(f());') == ["1"]
    assert run_grav('func f(){ for(let i=0;i<3;i+=1){ return i; } else { print("E"); } } print(f());') == ["0"]
    assert run_grav('try { while(true){ throw "x"; } else { print("E"); } } catch(e){ print(e); }') == ["x"]
    assert run_grav('while (false) { } else { print("E"); }') == ["E"]
    assert run_grav('for (x in [1]) { break; } else { print("E"); }') == []


@pytest.mark.parametrize("src", [
    'print(-"a");', 'let x = 1; x += null;', 'print([1,2,3][1.5:2]);',
    'let d = {}; d[[1]] = 2;', 'print(0 ** -1);', 'print((-8) ** 0.5);',
    'return 5;', 'break;',
])
def test_python_errors_become_grav_errors(src):
    with pytest.raises(GravLangError):
        run_grav(src)


def test_python_error_is_catchable():
    assert run_grav('try { print(-"a"); } catch(e) { print("caught"); }') == ["caught"]


def test_string_escapes_single_pass():
    assert run_grav(r'print(len("a\\nb"));') == ["4"]
    assert run_grav(r'print("a\nb");') == ["a\nb"]


def test_diamond_import(tmp_path):
    (tmp_path / "m1.grav").write_text("func helper(){ return 42; }")
    (tmp_path / "m2.grav").write_text('import "m1.grav"; func useit(){ return helper(); }')
    main = tmp_path / "main.grav"
    src = 'import "m1.grav"; import "m2.grav"; print(useit());'
    assert run_grav(src, path=str(main)) == ["42"]


def test_multiline_string_line_numbers():
    toks = Lexer('let s = "a\nb";\nlet y = 1;').tokenize()
    assert [t.line for t in toks if t.value == "y"] == [3]


# ── formatter ────────────────────────────────────────────────────────

def test_formatter_keeps_comments():
    src = "# top\nfunc f() {\n    # inside\n    return 1;  # tail\n}\n"
    out = format_source(src)
    assert "# top" in out and "# inside" in out and "# tail" in out
    assert format_source(out) == out


@pytest.mark.parametrize("src", [
    "print((a + b)[0]);", "print((x or [5])[0]);", "print((g or f)());",
    "print((not a) == b);", "print((2 ** 3) ** 2);", "print(2 ** 3 ** 2);",
    "print((a + b).m());", "print(-(a + b));", "let x = 0.000001;",
    "let x = 100000000000000000000.0;", 'print("a\\\\nb");',
])
def test_formatter_preserves_meaning(src):
    out = format_source(src)
    assert _ast(out) == _ast(src)
    assert format_source(out) == out


def test_std_library_formats_cleanly():
    import os
    import gravlang
    path = os.path.join(os.path.dirname(gravlang.__file__), "lib", "std.grav")
    src = open(path, encoding="utf-8").read()
    assert _ast(format_source(src)) == _ast(src)


# ── IDE ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("Tkinter display not available")
    root.withdraw()
    yield root
    root.destroy()


def test_modifier_keys_do_not_mark_modified(tk_root):
    tab = EditorTab(tk.Frame(tk_root), THEMES["Catppuccin Mocha"], lambda: None, lambda r, c: None)
    tab.set_content("let x = 1;")
    for key in ("Shift_L", "Home", "Control_L"):
        tab._on_key_release(SimpleNamespace(keysym=key))
    assert tab.modified is False
    tab.editor.insert("end", "x")
    tab._on_key_release(SimpleNamespace(keysym="x"))
    assert tab.modified is True


def test_close_inactive_tab_saves_that_tab(tk_root, tmp_path):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    a = app.new_tab(filepath=str(tmp_path / "a.grav"), content="")
    b = app.new_tab(filepath=str(tmp_path / "b.grav"), content="")
    a.editor.insert("end", "let a = 1;")
    a.modified = True
    app.switch_tab(b)                      # a is now inactive
    with mock.patch("gravlang.ide.main_window.messagebox.askyesnocancel", return_value=True):
        app.close_tab(a)
    assert (tmp_path / "a.grav").read_text() == "let a = 1;"
    assert not (tmp_path / "b.grav").exists()
    assert a not in app._tabs


def test_cancelled_save_keeps_tab_open(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    t = app.new_tab()
    t.modified = True
    with mock.patch("gravlang.ide.main_window.messagebox.askyesnocancel", return_value=True), \
         mock.patch("gravlang.ide.main_window.filedialog.asksaveasfilename", return_value=""):
        app.close_tab(t)
    assert t in app._tabs


def test_quit_prompts_for_unsaved(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    t = app.new_tab()
    t.modified = True
    with mock.patch("gravlang.ide.main_window.messagebox.askyesnocancel", return_value=None), \
         mock.patch.object(app.root, "destroy") as destroy:
        app._on_quit()
    destroy.assert_not_called()


# ══ medium-severity fixes ════════════════════════════════════════════

def test_print_and_tostring_use_gravlang_spelling():
    assert run_grav('print(true); print(null); print([true, null, "a"], {"k": false});') == \
        ["true", "null", '[true, null, "a"] {"k": false}']
    assert run_grav('print(toString([[true, "a"], {"k": [null]}]));') == ['[[true, "a"], {"k": [null]}]']
    assert run_grav('print("x" + [[true]]);') == ["x[[true]]"]


def test_variadic_init():
    assert run_grav('class A { func init(a, ...xs){ self.a = a; self.xs = xs; } } '
                    'let o = A(1, 2, 3); print(o.a); print(o.xs);') == ["1", "[2, 3]"]


def test_class_declared_in_function_sees_locals():
    assert run_grav('func outer(){ let zz = 7; class B { func m(){ return zz; } } return B(); } '
                    'print(outer().m());') == ["7"]


def test_imported_class_uses_its_own_module_scope(tmp_path):
    (tmp_path / "mod.grav").write_text(
        "func secret(){ return 5; }\nclass K { func m(){ return secret(); } }")
    main = tmp_path / "main.grav"
    assert run_grav('import "mod.grav"; let secret = 0; print(K().m());', path=str(main)) == ["5"]


def test_call_function_stored_in_field():
    assert run_grav('class A { func init(){ self.cb = func(x){ return x * 2; }; } } '
                    'let a = A(); print(a.cb(4));') == ["8"]


def test_keywords_as_member_names():
    assert run_grav('class A { func print(){ return 1; } func init(){ self.in = 2; } } '
                    'let a = A(); print(a.print()); print(a.in);') == ["1", "2"]


def test_call_depth_stays_balanced_after_overflow():
    from gravlang.core.interpreter import Interpreter
    src = ('func f(n){ return f(n+1); } '
           'for (let i = 0; i < 5; i += 1) { try { f(0); } catch (e) { } }')
    it = Interpreter(print_fn=lambda *a: None)
    it.interpret(Parser(Lexer(src).tokenize()).parse())
    assert it._call_depth == 0


def test_repl_parse_errors_flag_eof():
    from gravlang.core.errors import ParseError
    for src, eof in [("func f() {", True), ("let x = [1,", True), ("print(1 +;", False)]:
        with pytest.raises(ParseError) as ei:
            Parser(Lexer(src).tokenize()).parse()
        assert ei.value.at_eof is eof, src


def test_lib_files_are_package_data():
    import pathlib
    tomllib = pytest.importorskip("tomllib")  # py3.11+
    cfg = tomllib.loads((pathlib.Path(__file__).parent.parent / "pyproject.toml").read_text("utf-8"))
    assert "lib/*.grav" in cfg["tool"]["setuptools"]["package-data"]["gravlang"]


def _editor(tk_root, text=""):
    tab = EditorTab(tk.Frame(tk_root), THEMES["Catppuccin Mocha"], lambda: None, lambda r, c: None)
    tab.set_content(text)
    return tab


def test_auto_close_overtype(tk_root):
    tab = _editor(tk_root)
    for ch in 'print("hi")':
        if ch in "([{\"":
            tab._auto_close(ch, {"(": ")", "[": "]", "{": "}", '"': '"'}[ch])
        elif ch in ")]}" and tab._overtype(ch) == "break":
            pass
        else:
            tab.editor.insert("insert", ch)
    assert tab.get_content() == 'print("hi")'


def test_toggle_comment_keeps_inner_hash(tk_root):
    tab = _editor(tk_root, "# x # y\n")
    tab.editor.mark_set("insert", "1.0")
    tab._toggle_comment()
    assert tab.get_content().splitlines()[0] == "x # y"
    tab._toggle_comment()
    assert tab.get_content().splitlines()[0] == "# x # y"


def test_toggle_comment_selection(tk_root):
    tab = _editor(tk_root, "a\nb\nc\n")
    tab.editor.tag_add("sel", "1.0", "2.1")
    tab._toggle_comment()
    assert tab.get_content().splitlines() == ["# a", "# b", "c"]


def test_replace_all(tk_root):
    from gravlang.ide.components import FindReplaceBar
    tab = _editor(tk_root, "foo Foo bar\n")
    edits = []
    bar = FindReplaceBar(tk.Frame(tk_root), lambda: tab.editor, THEMES["Catppuccin Mocha"],
                         on_edit=lambda: edits.append(1))
    bar.find_var.set("")
    bar.replace_var.set("x")
    bar._replace_all()
    assert tab.get_content() == "foo Foo bar\n" and not edits       # empty query: no-op
    bar.find_var.set("foo")
    bar.replace_var.set(r"\1\n")
    bar._replace_all()
    assert tab.get_content().splitlines()[0] == r"\1\n \1\n bar" and edits  # literal replacement
    bar.find_var.set("zzz")
    bar._cur_idx = 5
    bar._replace_one()                                               # stale index: no crash


def test_sample_has_no_fake_path(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    app._load_sample("Hello World")
    assert app._active_tab().filepath == ""


# ══ low-severity fixes ═══════════════════════════════════════════════

def _tags_at(tab, text, needle, tag):
    idx = text.index(needle)
    line = text.count("\n", 0, idx) + 1
    col = idx - (text.rfind("\n", 0, idx) + 1)
    return tag in tab.editor.tag_names(f"{line}.{col}")


def test_syntax_highlighting(tk_root):
    code = 'try { print("Item #1: " + x); } catch (e) { } # note true\nbreak; let n = 5; class Foo {}\n'
    tab = _editor(tk_root, code)
    assert _tags_at(tab, code, "try", "keyword")
    assert _tags_at(tab, code, "catch", "keyword")
    assert _tags_at(tab, code, "break", "keyword")
    assert _tags_at(tab, code, "print", "builtin")
    assert _tags_at(tab, code, '"Item #1: "', "string")
    assert not _tags_at(tab, code, "#1", "comment")          # '#' inside a string
    assert not _tags_at(tab, code, "+ x", "comment")
    assert _tags_at(tab, code, "# note", "comment")
    assert not _tags_at(tab, code, "true", "boolean")          # inside a comment
    assert _tags_at(tab, code, "5", "number")
    assert _tags_at(tab, code, "Foo", "class_nm")


def test_user_output_containing_error_is_not_red(tk_root):
    from gravlang.ide.bottom_panel import BottomPanel
    bp = BottomPanel(tk.Frame(tk_root), THEMES["Catppuccin Mocha"])
    bp.append_output("No Error found\n")
    assert "error" not in bp.output_txt.tag_names("1.0")
    bp.append_output("boom\n", "error")
    assert "error" in bp.output_txt.tag_names("2.0")


def test_inspector_formats(tk_root):
    from gravlang.ide.components import VariableInspector
    insp = VariableInspector(tk.Frame(tk_root), THEMES["Catppuccin Mocha"])
    assert insp._format(None)[0] == "null"
    assert insp._format({"a": 1})[0] == "{1 keys}"
    from gravlang.core.interpreter import Interpreter
    it = Interpreter(print_fn=lambda *a: None)
    it.interpret(Parser(Lexer("func f(a, b){} class K{} let k = K();").tokenize()).parse())
    env = it.global_env
    assert insp._format(env.get("f"))[0] == "ƒ f(a, b)"
    assert insp._format(env.get("K"))[0] == "class K"
    assert insp._format(env.get("k"))[0].startswith("K ")


def test_open_missing_file_leaves_state_alone(tk_root, tmp_path):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    before = list(app._recent_files)
    with mock.patch("gravlang.ide.main_window.messagebox.showerror") as err:
        app.open_file_path(str(tmp_path / "nope.grav"))
    err.assert_called_once()
    assert app._recent_files == before and not app._tabs


def test_theme_switch_rethemes_bottom_panel(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    names = list(THEMES)
    other = next(n for n in names if THEMES[n]["BG_CRUST"] != app.theme["BG_CRUST"])
    app.apply_theme(other)
    assert str(app._bottom_panel.cget("bg")).lower() == THEMES[other]["BG_CRUST"].lower()
    assert str(app._bottom_panel.hdr.cget("bg")).lower() == THEMES[other]["BG_MANTLE"].lower()


def test_cancel_check_stops_empty_loop():
    from gravlang.core.errors import ExecutionStopped
    from gravlang.core.interpreter import Interpreter
    calls = []
    def check():
        calls.append(1)
        return len(calls) > 50
    it = Interpreter(print_fn=lambda *a: None, cancel_check=check)
    with pytest.raises(ExecutionStopped):
        it.interpret(Parser(Lexer("while (true) { }").tokenize()).parse())


def test_builtin_arity_message_hides_internals():
    with pytest.raises(GravLangError) as ei:
        run_grav("print(len(1, 2));")
    assert "_builtin_" not in str(ei.value)


def test_sort_returns_array():
    assert run_grav("print(sort([3, 1, 2]));") == ["[1, 2, 3]"]


@pytest.mark.parametrize("src", ["print([1 2]);", 'print({"a":1 "b":2});', "func f(a b){}", 'print(f"{1 2}");'])
def test_missing_separators_are_errors(src):
    with pytest.raises(GravLangError):
        run_grav(src)


def test_stray_semicolon_and_fstring_braces():
    assert run_grav("if (true) { print(1); };") == ["1"]
    assert run_grav('let n = 2; print(f"{{n}} = {n}");') == ["{n} = 2"]


# ══ debugger: stepping and breakpoint tracking ═══════════════════════

def _step_lines(src):
    from gravlang.core.interpreter import Interpreter
    seen = []
    Interpreter(print_fn=lambda *a: None, on_step=lambda line, env: seen.append(line)).interpret(
        Parser(Lexer(src).tokenize()).parse())
    return seen


def test_one_pause_per_statement_even_on_one_line():
    # `let x = f(1);` is a single step, not VarDecl + nested call
    lines = _step_lines("func f(a){ return a; }\nlet x = f(1);\n")
    assert lines.count(2) == 1
    # a one-line loop pauses on every iteration's body statement
    assert _step_lines("let n = 0;\nfor (let i = 0; i < 3; i += 1) { n += 1; }\n").count(2) == 4  # for + 3 bodies
    # a bare call statement is a step; same line recursion pauses at each level
    rec = _step_lines("func f(n){ if (n > 0) { f(n - 1); } }\nf(2);\n")
    assert rec.count(1) > 3


def test_breakpoints_and_folds_follow_edits(tk_root):
    tab = _editor(tk_root, "a;\nb;\nfunc f() {\n  x;\n}\nc;\n")
    tab.toggle_breakpoint(2)
    tab.toggle_fold(3)
    assert tab.breakpoints == {2} and tab.folded_blocks == {3}
    tab.editor.insert("1.0", "new1\nnew2\n")          # two lines added above
    assert tab.breakpoints == {4} and tab.folded_blocks == {5}
    tab.editor.delete("1.0", "2.0")                    # one removed
    assert tab.breakpoints == {3} and tab.folded_blocks == {4}
    assert tab.toggle_breakpoint(3) is False           # toggles the moved breakpoint off
    assert tab.breakpoints == set()
    assert tab.toggle_fold(4) is False and tab.folded_blocks == set()
    assert tab.toggle_breakpoint(99) is False          # nonexistent line


def test_fold_removed_when_braces_edited_away(tk_root):
    tab = _editor(tk_root, "func f() {\n  x;\n}\ny;\n")
    tab.toggle_fold(1)
    tab.editor.delete("1.9", "1.10")                   # delete the '{'
    tab._update_line_numbers()
    assert tab.folded_blocks == set()
    assert tab.editor.tag_ranges("fold_hidden_fold1") == ()


# ══ second audit pass ════════════════════════════════════════════════

def test_comment_before_closing_brace_stays_in_block():
    src = "func f() {\n    x = 1;\n    # last\n}\n# after\ny = 2;\n"
    out = format_source(src)
    assert out.index("# last") < out.index("}") < out.index("# after")
    assert "    # last\n}" in out
    assert format_source(out) == out


def test_big_ints_and_resource_guards():
    assert run_grav("let x = 1; for (let i = 0; i < 1500; i += 1) { x = x * 3; } "
                    "print(len(toString(x)));") == ["716"]
    for src in ('print(2 ** 10 ** 10);', 'print(len("ab" * 10 ** 12));'):
        with pytest.raises(GravLangError):
            run_grav(src)


def test_print_as_value_and_type_of_functions():
    assert run_grav("func f(){} class A{} print(type(f), type(A), type(A()), type(print));") == \
        ["function class A function"]


def test_friendly_syntax_errors():
    with pytest.raises(GravLangError, match="Unterminated string"):
        run_grav('print("abc);')
    with pytest.raises(GravLangError, match="elif"):
        run_grav("if (false) { } else if (true) { }")
    assert run_grav('print(f"a}b");') == ["a}b"]


def test_enter_between_braces(tk_root):
    tab = _editor(tk_root, "func f() {}")
    tab.editor.mark_set("insert", "1.10")
    tab._on_return(None)
    assert tab.get_content() == "func f() {\n    \n}"
    assert tab.editor.index("insert") == "2.4"


def test_gutter_skips_folded_lines(tk_root):
    win = tk.Toplevel(tk_root)          # must be mapped for dlineinfo to report lines
    win.geometry("600x400")
    tab = EditorTab(win, THEMES["Catppuccin Mocha"], lambda: None, lambda r, c: None)
    tab.frame.pack(fill="both", expand=True)
    tab.set_content("a;\nfunc f() {\n  x;\n  y;\n}\nz;\n")
    win.update()
    tab.toggle_fold(2)
    win.update()
    nums = [tab.ln_canvas.itemcget(i, "text") for i in tab.ln_canvas.find_all()
            if tab.ln_canvas.type(i) == "text"]
    assert "3" not in nums and "4" not in nums and "5" not in nums and "6" in nums
    win.destroy()


def test_status_counts_ignore_builtins(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    from gravlang.core.interpreter import Interpreter
    app = GravLangIDE(tk_root)
    it = Interpreter(print_fn=lambda *a: None)
    it.interpret(Parser(Lexer("let a = 1; let b = [1];").tokenize()).parse())
    app._update_scope_stats(dict(it.global_env._store))
    assert "Vars: 2" in app._status_stats.cget("text")


# ══ third audit pass ═════════════════════════════════════════════════

@pytest.mark.parametrize("src", [
    "(func(a) { return a; }) > 1;",                 # statement must not start with `func`
    "(func() { return 1; })();",
    "let o = null; (o.f)(1);",                       # call of a field vs. method call
    "print((1)(2).a.b(3));",
])
def test_formatter_roundtrip_edge_cases(src):
    out = format_source(src)
    assert _ast(out) == _ast(src)
    assert format_source(out) == out


def test_python_type_names_do_not_leak():
    for src in ('print(-"a");', "print(1 + null);", "let x = 1; x -= \"a\";"):
        with pytest.raises(GravLangError) as ei:
            run_grav(src)
        msg = str(ei.value)
        assert "NoneType" not in msg and "'str'" not in msg and "bad operand" not in msg


def test_finished_run_clears_arrow_on_the_run_tab(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    a = app.new_tab(content="let x = 1;")
    a.set_paused_line(1)
    app._run_tab = a
    app.new_tab(content="# other")          # a is no longer the active tab
    app._finish_run([], [], 0.0, {"x": 1})
    assert a.paused_line is None


# ══ theme switching ══════════════════════════════════════════════════

def _all_widgets(w):
    yield w
    for c in w.winfo_children():
        yield from _all_widgets(c)


def test_theme_switch_leaves_no_stale_colours(tk_root):
    """Every widget colour belongs to the active theme after any sequence of switches,
    even after hovering buttons (hover handlers used to restore the old theme)."""
    from tkinter import ttk
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    app.new_tab(content="let x = 1;")
    app._inspector.populate({"x": 1})
    names = list(THEMES)
    opts = ("bg", "fg", "activebackground", "activeforeground", "insertbackground",
            "highlightbackground", "highlightcolor", "selectbackground", "selectforeground")
    for name in names + names[::-1]:
        app.apply_theme(name)
        for b in app._toolbar.winfo_children():
            if isinstance(b, tk.Button):
                b.event_generate("<Enter>")
                b.event_generate("<Leave>")
        app._sash.event_generate("<Leave>")
        app._clr_lbl.event_generate("<Leave>")
        valid = {v.lower() for v in THEMES[name].values()}
        stale = []
        for w in _all_widgets(app.root):
            if isinstance(w, tk.Toplevel) and w is not app.root:
                continue
            for opt in opts:
                try:
                    v = str(w.cget(opt)).lower()
                except tk.TclError:
                    continue
                if v.startswith("#") and v not in valid:
                    stale.append((w.winfo_class(), opt, v))
        assert not stale, (name, stale[:5])
        t = THEMES[name]
        st = ttk.Style()
        assert str(st.lookup("Exp.Treeview", "background")).lower() == t["BG_MANTLE"].lower()
        assert str(st.lookup("Insp.Treeview", "background")).lower() == t["BG_MANTLE"].lower()
        assert str(st.lookup("Vertical.TScrollbar", "troughcolor")).lower() == t["BG_MANTLE"].lower()
        assert str(app._statusbar.cget("bg")).lower() == t["STATUS_BG"].lower()
        assert str(app._status_stats.cget("bg")).lower() == t["STATUS_BG"].lower()


# ══ fourth audit pass: CLI, stdlib, encodings ════════════════════════

import subprocess
import sys as _sys
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _cli(*args, cwd=None):
    env = {**_os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([_sys.executable, "-m", "gravlang", *args], cwd=cwd or _ROOT,
                          capture_output=True, encoding="utf-8", env=env, timeout=30)


def test_cli_runs_file_and_reports_errors(tmp_path):
    ok = tmp_path / "ok.grav"
    ok.write_text('print(true, [1, "a"]);')
    r = _cli(str(ok))
    assert r.returncode == 0 and r.stdout.strip() == 'true [1, "a"]'
    bad = tmp_path / "bad.grav"
    bad.write_text("let x = ;")
    r = _cli(str(bad))
    assert r.returncode == 1 and "Parse Error" in r.stdout
    assert _cli(str(tmp_path / "nope.grav")).returncode == 1


def test_cli_version_help_and_unreadable_file(tmp_path):
    assert _cli("--version").stdout.startswith("GravLang ")
    assert "Usage" in _cli("--help").stdout
    binary = tmp_path / "bin.grav"
    binary.write_bytes(b"\xff\xfe\x00")
    r = _cli(str(binary))
    assert r.returncode == 1 and "cannot read" in r.stdout


def test_cli_fmt_check(tmp_path):
    f = tmp_path / "a.grav"
    f.write_text("let   x=1;")
    assert _cli("fmt", str(f), "--check").returncode == 1
    f.write_text("let x = 1;\n")
    assert _cli("fmt", str(f), "--check").returncode == 0


def test_cli_repl_multiline(tmp_path):
    env = {**_os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([_sys.executable, "-m", "gravlang", "--repl"], cwd=_ROOT, env=env,
                       input="func f() {\n return 7;\n}\nprint(f());\nexit\n",
                       capture_output=True, encoding="utf-8", timeout=30)
    assert "7" in r.stdout


def test_utf8_bom_and_nbsp_are_accepted(tmp_path):
    f = tmp_path / "bom.grav"
    f.write_bytes(b"\xef\xbb\xbfprint(1);\r\nprint(2);\r\n")
    assert _cli(str(f)).stdout.split() == ["1", "2"]
    assert run_grav("print(1);" + chr(0xA0) + "print(2);") == ["1", "2"]
    assert _cli("fmt", str(f)).returncode == 0


def test_stdlib_modules(tmp_path):
    src = '''
import "lib/math.grav";
import "lib/strings.grav";
import "lib/std.grav";
print(sqrt(1000000), sqrt(16), Math.sqrt(16), sqrt(0.0001));
print(factorial(300) > 0, fib(30));
print(capitalize("hello"), capitalize("Hi"), capitalize("1a"), capitalize(""));
print(padLeft("7", 3, "0"), padRight("7", 3, "."), padLeft("ab", 5, ""), repeat("ab", 2));
print(Strings.split("a,b,,c", ","), Strings.split("a--b", "--"), Strings.trim("  x "));
'''
    out = run_grav(src, path=str(tmp_path / "main.grav"))
    assert out == [
        "1000.0 4.0 4.0 0.01",
        "true 832040",
        "Hello Hi 1a ",
        "007 7.. ab abab",
        '["a", "b", "", "c"] ["a", "b"] x',
    ]


def test_undo_does_not_erase_a_loaded_file(tk_root):
    tab = _editor(tk_root, "let x = 1;\n")
    try:
        tab.editor.edit_undo()
    except tk.TclError:
        pass                                   # nothing to undo is fine
    assert tab.get_content() == "let x = 1;\n"


def test_format_is_one_undo_step(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    app = GravLangIDE(tk_root)
    tab = app.new_tab(content="let   x=1;\nlet y   =2;\n")
    tab.editor.insert("end-1c", "x;")                 # a real edit first
    tab.editor.edit_separator()
    before = tab.get_content()
    app.format_code()
    assert tab.get_content() != before and tab.modified
    tab.editor.edit_undo()
    assert tab.get_content() == before


def test_autocomplete_hides_for_exact_match(tk_root):
    tab = _editor(tk_root, "print")
    tab.editor.mark_set("insert", "end-1c")
    tab._maybe_autocomplete()
    assert not tab._autocomplete.visible()          # Tab must indent, not "accept print"


def test_config_is_per_user_not_next_to_the_code():
    from gravlang.ide import themes
    assert themes.CONFIG_FILE != themes.LEGACY_CONFIG_FILE
    assert not themes.CONFIG_FILE.startswith(_os.path.dirname(themes.__file__))
    assert _os.environ["GRAVLANG_CONFIG"] == themes.CONFIG_FILE      # tests never touch real settings


def test_config_round_trip(tk_root, tmp_path, monkeypatch):
    from gravlang.ide import main_window
    from gravlang.ide.main_window import GravLangIDE
    cfg = tmp_path / "sub" / "config.json"
    monkeypatch.setattr(main_window, "CONFIG_FILE", str(cfg))
    app = GravLangIDE(tk_root)
    app.apply_theme("GitHub Dark")
    assert cfg.exists() and '"GitHub Dark"' in cfg.read_text()
    assert app._load_config()["theme"] == "GitHub Dark"


def test_output_flushes_in_batches_and_is_capped(tk_root):
    from gravlang.ide.main_window import GravLangIDE
    from gravlang.ide.bottom_panel import BottomPanel
    app = GravLangIDE(tk_root)
    app._pending_output = [f"line {i}" for i in range(500)]
    app._flush_output()
    txt = app._bottom_panel.output_txt.get("1.0", "end-1c").splitlines()
    assert txt[0] == "line 0" and txt[-1] == "line 499" and app._pending_output == []
    app._pending_output = ["x"] * (BottomPanel.MAX_LINES + 500)
    app._flush_output()
    assert int(app._bottom_panel.output_txt.index("end-1c").split(".")[0]) <= BottomPanel.MAX_LINES + 1
