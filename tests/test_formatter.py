"""
tests/test_formatter.py — pytest tests for the GravLang formatter.

Strategy
--------
1. **Idempotency** — format(source) == format(format(source)):
   the most important property; a second pass must produce identical output.
2. **Semantic equivalence** — format then run the interpreter and compare
   the output to the original program's output.
3. **Canonical style** — spot-check specific formatting rules (indentation,
   spacing, operator layout, etc.).
4. **Fixture files** — run both idempotency and semantic checks over all 25
   .grav test programs in tests/grav/.
"""

from __future__ import annotations

import os
import sys
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from helpers import run_grav
from gravlang.core.formatter import format_source, format_file, Formatter
from gravlang.core.errors import GravLangError

GRAV_DIR = os.path.join(_HERE, "grav")


# ── helpers ──────────────────────────────────────────────────────────────────

def _grav(name: str) -> str:
    return os.path.join(GRAV_DIR, name)


def _fmt(src: str) -> str:
    return format_source(src)


def _idempotent(src: str) -> None:
    """Assert that formatting twice gives the same result."""
    once  = _fmt(src)
    twice = _fmt(once)
    assert once == twice, (
        f"Formatter is NOT idempotent!\n"
        f"--- first pass ---\n{once}\n"
        f"--- second pass ---\n{twice}"
    )


def _semantically_equal(original_src: str) -> None:
    """Assert that the formatted source produces the same output as the original."""
    formatted = _fmt(original_src)
    orig_out = run_grav(original_src)
    fmt_out  = run_grav(formatted)
    assert orig_out == fmt_out, (
        f"Semantic mismatch after formatting!\n"
        f"Original output : {orig_out}\n"
        f"Formatted output: {fmt_out}\n"
        f"Formatted source:\n{formatted}"
    )


# ── 01  Idempotency on all fixture files ─────────────────────────────────────

class TestIdempotency:
    """The formatter is idempotent: format(format(x)) == format(x)."""

    @pytest.mark.parametrize(
        "fname",
        sorted(f for f in os.listdir(GRAV_DIR) if f.endswith(".grav")),
    )
    def test_fixture_files(self, fname: str):
        src = open(_grav(fname), encoding="utf-8").read()
        _idempotent(src)

    def test_simple_expression(self):
        _idempotent("print(1 + 2);")

    def test_nested_blocks(self):
        _idempotent("""
        func outer(x) {
            func inner(y) {
                return x + y;
            }
            return inner(10);
        }
        print(outer(5));
        """)

    def test_class_with_methods(self):
        _idempotent("""
        class Foo extends Bar {
            func init(x) {
                self.x = x;
            }
            func get() {
                return self.x;
            }
        }
        """)


# ── 02  Semantic equivalence on all fixture files ─────────────────────────────

class TestSemanticEquivalence:
    """format(program) runs and produces the same stdout as the original."""

    @pytest.mark.parametrize(
        "fname",
        sorted(f for f in os.listdir(GRAV_DIR) if f.endswith(".grav")),
    )
    def test_fixture_files(self, fname: str):
        src = open(_grav(fname), encoding="utf-8").read()
        _semantically_equal(src)


# ── 03  Canonical style rules ─────────────────────────────────────────────────

class TestStyle:
    """Spot-check that the formatter emits specific canonical patterns."""

    def test_4_space_indent(self):
        src = "if (true) { print(1); }"
        out = _fmt(src)
        lines = out.splitlines()
        # The print statement inside the if must be indented by exactly 4 spaces
        inner = [l for l in lines if "print" in l][0]
        assert inner.startswith("    ") and not inner.startswith("     "), repr(inner)

    def test_nested_indent_8_spaces(self):
        src = "if (true) { if (true) { print(1); } }"
        out = _fmt(src)
        inner = [l for l in out.splitlines() if "print" in l][0]
        assert inner.startswith("        ") and not inner.startswith("         "), repr(inner)

    def test_binary_op_spaces(self):
        out = _fmt("print(1+2*3);")
        assert "1 + 2 * 3" in out or "1 + 2*3" in out or "1+2*3" not in out
        # No adjacent digits without spaces around the top-level +
        assert " + " in out

    def test_let_keyword(self):
        out = _fmt("let  x=42;")
        assert "let x = 42;" in out

    def test_single_trailing_newline(self):
        out = _fmt('print("hi");')
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_no_trailing_whitespace(self):
        src = """
        func f(x) {
            return x + 1;
        }
        """
        out = _fmt(src)
        for line in out.splitlines():
            assert line == line.rstrip(), f"Trailing whitespace in: {line!r}"

    def test_blank_line_between_top_level_funcs(self):
        src = "func a() { return 1; } func b() { return 2; }"
        out = _fmt(src)
        assert "\n\n" in out, f"No blank line between top-level funcs:\n{out}"

    def test_blank_line_between_class_methods(self):
        src = """
        class C {
            func a() { return 1; }
            func b() { return 2; }
        }
        """
        out = _fmt(src)
        lines = out.splitlines()
        # Find the lines inside the class and ensure a blank line appears
        in_class = False
        blank_found = False
        for line in lines:
            if "class C" in line:
                in_class = True
            if in_class and line.strip() == "":
                blank_found = True
        assert blank_found, f"No blank line between class methods:\n{out}"

    def test_func_params_comma_space(self):
        out = _fmt("func add(a,b,c) { return a+b+c; }")
        assert "func add(a, b, c)" in out

    def test_variadic_ellipsis(self):
        out = _fmt("func f(a, ...rest) { return rest; }")
        assert "...rest" in out

    def test_array_literal_spaces(self):
        out = _fmt("let a = [1,2,3];")
        assert "[1, 2, 3]" in out

    def test_dict_literal_spaces(self):
        out = _fmt('let d = {"a":1,"b":2};')
        assert '"a": 1' in out
        assert '"b": 2' in out

    def test_boolean_literals(self):
        out = _fmt("let x = true; let y = false;")
        assert "true" in out and "false" in out

    def test_null_literal(self):
        out = _fmt("let x = null;")
        assert "null" in out

    def test_self_keyword(self):
        src = "class C { func init() { self.x = 1; } }"
        out = _fmt(src)
        assert "self.x = 1;" in out

    def test_import_stmt(self):
        out = _fmt('import "lib/math.grav";')
        assert 'import "lib/math.grav";' in out

    def test_throw_stmt(self):
        out = _fmt('throw "error";')
        assert 'throw "error";' in out

    def test_break_continue(self):
        src = "while (true) { break; }"
        out = _fmt(src)
        assert "break;" in out

        src2 = "for (let i = 0; i < 5; i += 1) { continue; }"
        out2 = _fmt(src2)
        assert "continue;" in out2

    def test_return_no_value(self):
        out = _fmt("func f() { return; }")
        assert "return;" in out

    def test_return_with_value(self):
        out = _fmt("func f(x) { return x * 2; }")
        assert "return x * 2;" in out

    def test_elif_chain(self):
        src = 'if (a) { print(1); } elif (b) { print(2); } elif (c) { print(3); } else { print(4); }'
        out = _fmt(src)
        assert "} elif (" in out
        assert "} else {" in out

    def test_for_in(self):
        src = "for (x in arr) { print(x); }"
        out = _fmt(src)
        assert "for (x in arr) {" in out

    def test_try_catch_finally(self):
        src = 'try { print(1); } catch (e) { print(e); } finally { print("done"); }'
        out = _fmt(src)
        assert "try {" in out
        assert "} catch (e) {" in out
        assert "} finally {" in out

    def test_method_call(self):
        src = "obj.doSomething(1, 2);"
        out = _fmt(src)
        assert "obj.doSomething(1, 2);" in out

    def test_attribute_get(self):
        src = "let x = obj.field;"
        out = _fmt(src)
        assert "obj.field" in out

    def test_augmented_assign(self):
        out = _fmt("x += 1;")
        assert "x += 1;" in out

    def test_while_else_finally(self):
        src = "while (i < 5) { i += 1; } else { print(0); } finally { print(1); }"
        out = _fmt(src)
        assert "} else {" in out
        assert "} finally {" in out

    def test_array_slice_both(self):
        out = _fmt("let s = arr[1:4];")
        assert "arr[1:4]" in out

    def test_array_slice_open_end(self):
        out = _fmt("let s = arr[2:];")
        assert "arr[2:]" in out

    def test_array_slice_open_start(self):
        out = _fmt("let s = arr[:3];")
        assert "arr[:3]" in out


# ── 04  Operator precedence / parenthesis tests ───────────────────────────────

class TestPrecedence:
    """The formatter adds parens only where necessary."""

    def test_lower_prec_right_gets_parens(self):
        # (a + b) * c — the right operand of * has lower prec, needs parens
        src = "let x = (1 + 2) * 3;"
        out = _fmt(src)
        assert "(1 + 2) * 3" in out

    def test_same_prec_left_no_parens(self):
        # 1 + 2 + 3 is left-associative, no parens needed on left
        src = "let x = 1 + 2 + 3;"
        out = _fmt(src)
        assert "1 + 2 + 3" in out

    def test_unary_minus(self):
        out = _fmt("let x = -5;")
        assert "-5" in out

    def test_not_expr(self):
        out = _fmt("let x = not true;")
        assert "not true" in out

    def test_power(self):
        out = _fmt("let x = 2 ** 10;")
        assert "2 ** 10" in out


# ── 05  Indent width option ───────────────────────────────────────────────────

class TestIndentWidth:
    """The --indent option controls indentation width."""

    def test_2_space_indent(self):
        src = "if (true) { print(1); }"
        out = format_source(src, indent_width=2)
        inner = [l for l in out.splitlines() if "print" in l][0]
        assert inner.startswith("  ") and not inner.startswith("   ")

    def test_8_space_indent(self):
        src = "if (true) { print(1); }"
        out = format_source(src, indent_width=8)
        inner = [l for l in out.splitlines() if "print" in l][0]
        assert inner.startswith("        ") and not inner.startswith("         ")


# ── 06  Error reporting ───────────────────────────────────────────────────────

class TestErrors:
    """format_source re-raises GravLangError on bad input."""

    def test_lexer_error(self):
        with pytest.raises(GravLangError):
            format_source("let x = @;")

    def test_parse_error(self):
        with pytest.raises(GravLangError):
            format_source("let x = 1")  # missing semicolon


# ── 07  format_file helper ────────────────────────────────────────────────────

class TestFormatFile:
    """format_file() reads a path and formats it."""

    @pytest.mark.parametrize(
        "fname",
        sorted(f for f in os.listdir(GRAV_DIR) if f.endswith(".grav")),
    )
    def test_all_fixtures(self, fname: str):
        out = format_file(_grav(fname))
        # Basic sanity: non-empty and ends with newline
        assert out.strip()
        assert out.endswith("\n")
