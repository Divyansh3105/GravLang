"""
GravLang — Source formatter / pretty-printer.

Usage (CLI):
    python formatter.py program.grav            # prints to stdout
    python formatter.py program.grav -w         # writes back in-place
    python formatter.py program.grav -o out.grav

API:
    from formatter import format_source, format_file
    formatted_str = format_source(source_code)
    formatted_str = format_file("program.grav")

The formatter walks the AST produced by the Parser and emits *canonical*
GravLang source with:
  - 4-space indentation per block level
  - One statement per line with a trailing semicolon
  - Spaces around binary operators
  - No trailing whitespace
  - A single trailing newline
  - Blank lines between top-level function / class declarations

Because f-strings are desugared into BinOp(+) chains during parsing, the
formatter cannot reconstruct them. Interpolated strings are emitted as
regular string concatenation (which is semantically identical).
"""

from __future__ import annotations

import os
import sys

# Allow running as a standalone script from the project root
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from . import ast_nodes as ast
from .lexer import Lexer
from .parser import Parser
from .errors import GravLangError


# ── Operator precedence table (used for parenthesis insertion) ───────────────
# Higher number = tighter binding.
_PREC: dict[str, int] = {
    "or":  1,
    "and": 2,
    "not": 3,      # unary — handled separately
    "==":  4,
    "!=":  4,
    "<":   4,
    ">":   4,
    "<=":  4,
    ">=":  4,
    "+":   5,
    "-":   5,
    "*":   6,
    "/":   6,
    "//":  6,
    "%":   6,
    "**":  7,      # right-associative but handled by wrapping the left side
}


def _binop_prec(op: str) -> int:
    return _PREC.get(op, 0)


# ── Literal formatting helpers ───────────────────────────────────────────────

def _fmt_literal(value: object) -> str:
    """Format a Python value back into canonical GravLang source."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # Preserve at least one decimal place so it stays a float literal
        s = repr(value)
        return s
    if isinstance(value, str):
        # Re-escape the string for round-trip safety
        escaped = (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return str(value)


# ── Formatter class ──────────────────────────────────────────────────────────

class Formatter:
    """
    AST walker that emits canonical GravLang source.

    Parameters
    ----------
    indent_width : int
        Number of spaces per indentation level (default: 4).
    """

    def __init__(self, indent_width: int = 4):
        self._indent_width = indent_width
        self._level = 0         # current indentation depth
        self._lines: list[str] = []   # accumulated output lines

    # ── public API ──────────────────────────────────────────────────────

    def format(self, tree: ast.Program) -> str:
        """Walk *tree* and return the formatted source as a string."""
        self._lines = []
        self._level = 0
        self._fmt_program(tree)
        # Guarantee single trailing newline, strip trailing blank lines
        result = "\n".join(self._lines).rstrip() + "\n"
        return result

    # ── indentation helpers ─────────────────────────────────────────────

    def _indent(self) -> str:
        return " " * (self._indent_width * self._level)

    def _emit(self, text: str) -> None:
        """Append a line at the current indentation level."""
        self._lines.append(f"{self._indent()}{text}")

    def _blank(self) -> None:
        self._lines.append("")

    # ── program ─────────────────────────────────────────────────────────

    def _fmt_program(self, node: ast.Program) -> None:
        prev_was_block = False  # track whether previous stmt was a block-level decl
        for i, stmt in enumerate(node.body):
            is_block = isinstance(stmt, (ast.FuncDecl, ast.ClassDecl))

            # Insert a blank line before / after top-level func / class declarations
            if i > 0 and (is_block or prev_was_block):
                self._blank()

            self._fmt_stmt(stmt)
            prev_was_block = is_block

    # ── statement dispatch ──────────────────────────────────────────────

    def _fmt_stmt(self, node) -> None:
        t = type(node).__name__
        method = getattr(self, f"_fmt_{t}", None)
        if method is None:
            # Fallback: try to emit as expression statement
            self._emit(f"{self._fmt_expr(node)};")
            return
        method(node)

    # ── statements ──────────────────────────────────────────────────────

    def _fmt_VarDecl(self, node: ast.VarDecl) -> None:
        self._emit(f"let {node.name} = {self._fmt_expr(node.value)};")

    def _fmt_Assign(self, node: ast.Assign) -> None:
        self._emit(f"{node.name} = {self._fmt_expr(node.value)};")

    def _fmt_AugAssign(self, node: ast.AugAssign) -> None:
        op_str = node.op
        self._emit(f"{node.name} {op_str}= {self._fmt_expr(node.value)};")

    def _fmt_IfStmt(self, node: ast.IfStmt) -> None:
        cond = self._fmt_expr(node.condition)
        self._emit(f"if ({cond}) {{")
        self._level += 1
        for s in node.body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        # elif clauses
        for elif_cond, elif_body in node.elif_clauses:
            self._emit(f"}} elif ({self._fmt_expr(elif_cond)}) {{")
            self._level += 1
            for s in elif_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        # else
        if node.else_body is not None:
            self._emit("} else {")
            self._level += 1
            for s in node.else_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        self._emit("}")

    def _fmt_WhileStmt(self, node: ast.WhileStmt) -> None:
        cond = self._fmt_expr(node.condition)
        self._emit(f"while ({cond}) {{")
        self._level += 1
        for s in node.body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        if node.else_body is not None:
            self._emit("} else {")
            self._level += 1
            for s in node.else_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        if node.finally_body is not None:
            self._emit("} finally {")
            self._level += 1
            for s in node.finally_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        self._emit("}")

    def _fmt_ForStmt(self, node: ast.ForStmt) -> None:
        # init may be a VarDecl (without trailing ;) or Assign / AugAssign
        init_str = self._fmt_for_init(node.init)
        cond_str = self._fmt_expr(node.condition)
        upd_str  = self._fmt_for_update(node.update)
        self._emit(f"for ({init_str}; {cond_str}; {upd_str}) {{")
        self._level += 1
        for s in node.body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        if node.else_body is not None:
            self._emit("} else {")
            self._level += 1
            for s in node.else_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        if node.finally_body is not None:
            self._emit("} finally {")
            self._level += 1
            for s in node.finally_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        self._emit("}")

    def _fmt_for_init(self, node) -> str:
        """Emit the init clause of a for-loop (no trailing semicolon)."""
        if isinstance(node, ast.VarDecl):
            return f"let {node.name} = {self._fmt_expr(node.value)}"
        if isinstance(node, ast.Assign):
            return f"{node.name} = {self._fmt_expr(node.value)}"
        if isinstance(node, ast.AugAssign):
            return f"{node.name} {node.op}= {self._fmt_expr(node.value)}"
        return self._fmt_expr(node)

    def _fmt_for_update(self, node) -> str:
        """Emit the update clause of a for-loop (no trailing semicolon)."""
        return self._fmt_for_init(node)

    def _fmt_ForInStmt(self, node: ast.ForInStmt) -> None:
        iterable = self._fmt_expr(node.iterable)
        self._emit(f"for ({node.var} in {iterable}) {{")
        self._level += 1
        for s in node.body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        if node.else_body is not None:
            self._emit("} else {")
            self._level += 1
            for s in node.else_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        if node.finally_body is not None:
            self._emit("} finally {")
            self._level += 1
            for s in node.finally_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        self._emit("}")

    def _fmt_FuncDecl(self, node: ast.FuncDecl) -> None:
        params_str = self._fmt_params(node.params, node.variadic)
        self._emit(f"func {node.name}({params_str}) {{")
        self._level += 1
        for s in node.body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        self._emit("}")

    def _fmt_params(self, params: list[str], variadic: str | None) -> str:
        parts = list(params)
        if variadic is not None:
            parts.append(f"...{variadic}")
        return ", ".join(parts)

    def _fmt_ReturnStmt(self, node: ast.ReturnStmt) -> None:
        if node.value is None:
            self._emit("return;")
        else:
            self._emit(f"return {self._fmt_expr(node.value)};")

    def _fmt_BreakStmt(self, node: ast.BreakStmt) -> None:
        self._emit("break;")

    def _fmt_ContinueStmt(self, node: ast.ContinueStmt) -> None:
        self._emit("continue;")

    def _fmt_ImportStmt(self, node: ast.ImportStmt) -> None:
        escaped_path = node.path.replace("\\", "\\\\").replace('"', '\\"')
        self._emit(f'import "{escaped_path}";')

    def _fmt_ThrowStmt(self, node: ast.ThrowStmt) -> None:
        self._emit(f"throw {self._fmt_expr(node.value)};")

    def _fmt_TryCatchStmt(self, node: ast.TryCatchStmt) -> None:
        self._emit("try {")
        self._level += 1
        for s in node.try_body.statements:
            self._fmt_stmt(s)
        self._level -= 1
        if node.catch_body is not None:
            if node.catch_var:
                self._emit(f"}} catch ({node.catch_var}) {{")
            else:
                self._emit("} catch {")
            self._level += 1
            for s in node.catch_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        if node.finally_body is not None:
            self._emit("} finally {")
            self._level += 1
            for s in node.finally_body.statements:
                self._fmt_stmt(s)
            self._level -= 1
        self._emit("}")

    def _fmt_ClassDecl(self, node: ast.ClassDecl) -> None:
        header = f"class {node.name}"
        if node.parent:
            header += f" extends {node.parent}"
        self._emit(f"{header} {{")
        self._level += 1
        for i, method in enumerate(node.methods):
            if i > 0:
                self._blank()  # blank line between methods
            self._fmt_FuncDecl(method)
        self._level -= 1
        self._emit("}")

    def _fmt_Block(self, node: ast.Block) -> None:
        """Format a bare block (not usually a top-level statement)."""
        self._emit("{")
        self._level += 1
        for s in node.statements:
            self._fmt_stmt(s)
        self._level -= 1
        self._emit("}")

    # ── expression-statement wrappers ────────────────────────────────────

    def _fmt_FuncCall(self, node: ast.FuncCall) -> None:
        self._emit(f"{self._fmt_expr(node)};")

    def _fmt_MethodCall(self, node: ast.MethodCall) -> None:
        self._emit(f"{self._fmt_expr(node)};")

    def _fmt_ArrayAssign(self, node: ast.ArrayAssign) -> None:
        arr  = self._fmt_expr(node.array)
        idx  = self._fmt_expr(node.index)
        val  = self._fmt_expr(node.value)
        self._emit(f"{arr}[{idx}] = {val};")

    def _fmt_AttributeSet(self, node: ast.AttributeSet) -> None:
        obj  = self._fmt_expr(node.obj)
        val  = self._fmt_expr(node.value)
        self._emit(f"{obj}.{node.attr} = {val};")

    def _fmt_CallExpr(self, node: ast.CallExpr) -> None:
        self._emit(f"{self._fmt_expr(node)};")

    # ── expression formatter (returns string) ─────────────────────────

    def _fmt_expr(self, node, parent_op: str | None = None) -> str:
        t = type(node).__name__
        method = getattr(self, f"_expr_{t}", None)
        if method is None:
            return f"<{t}>"
        return method(node, parent_op)

    # ── expression visitors ─────────────────────────────────────────────

    def _expr_Literal(self, node: ast.Literal, _pop=None) -> str:
        return _fmt_literal(node.value)

    def _expr_Identifier(self, node: ast.Identifier, _pop=None) -> str:
        return node.name

    def _expr_SelfExpr(self, node: ast.SelfExpr, _pop=None) -> str:
        return "self"

    def _expr_BinOp(self, node: ast.BinOp, parent_op: str | None = None) -> str:
        my_prec = _binop_prec(node.op)
        # Left child: we evaluate without parent_op and add parens here if needed
        left_str  = self._fmt_expr(node.left)
        right_str = self._fmt_expr(node.right)

        # Decide if we need parens around left child
        if isinstance(node.left, ast.BinOp):
            left_prec = _binop_prec(node.left.op)
            if left_prec < my_prec:
                left_str = f"({left_str})"

        # Decide if we need parens around right child
        if isinstance(node.right, ast.BinOp):
            right_prec = _binop_prec(node.right.op)
            # ** is right-associative so same prec on right is OK
            if right_prec < my_prec or (right_prec == my_prec and node.op != "**"):
                right_str = f"({right_str})"

        return f"{left_str} {node.op} {right_str}"

    def _expr_UnaryOp(self, node: ast.UnaryOp, _pop=None) -> str:
        operand = self._fmt_expr(node.operand)
        # Put parens around binary sub-expression to be safe
        if isinstance(node.operand, ast.BinOp):
            operand = f"({operand})"
        if node.op == "not":
            return f"not {operand}"
        # Unary minus
        return f"{node.op}{operand}"

    def _expr_FuncCall(self, node: ast.FuncCall, _pop=None) -> str:
        args = ", ".join(self._fmt_expr(a) for a in node.args)
        return f"{node.name}({args})"

    def _expr_CallExpr(self, node: ast.CallExpr, _pop=None) -> str:
        callee = self._fmt_expr(node.callee)
        # Wrap callee in parens if it's a lambda or complex expression
        if isinstance(node.callee, ast.LambdaExpr):
            callee = f"({callee})"
        args = ", ".join(self._fmt_expr(a) for a in node.args)
        return f"{callee}({args})"

    def _expr_LambdaExpr(self, node: ast.LambdaExpr, _pop=None) -> str:
        params_str = self._fmt_params(node.params, node.variadic)
        # Format the body inline if it's a single return or single statement
        stmts = node.body.statements
        if len(stmts) == 1 and isinstance(stmts[0], ast.ReturnStmt):
            ret_val = stmts[0].value
            if ret_val is not None:
                body_str = f"return {self._fmt_expr(ret_val)};"
                return f"func({params_str}) {{ {body_str} }}"
        # Multi-statement lambda body — use indented block
        # (formatted as a multi-line expression with a helper)
        return self._fmt_lambda_multiline(params_str, stmts)

    def _fmt_lambda_multiline(self, params_str: str, stmts: list) -> str:
        """Produce a compact inline representation of a multi-statement lambda."""
        inner_parts = []
        saved_level = self._level
        self._level = 0
        saved_lines = self._lines
        self._lines = []
        for s in stmts:
            self._fmt_stmt(s)
        inner_parts = [line.strip() for line in self._lines]
        self._lines = saved_lines
        self._level = saved_level
        body = " ".join(inner_parts)
        return f"func({params_str}) {{ {body} }}"

    def _expr_ArrayLiteral(self, node: ast.ArrayLiteral, _pop=None) -> str:
        if not node.elements:
            return "[]"
        elems = ", ".join(self._fmt_expr(e) for e in node.elements)
        return f"[{elems}]"

    def _expr_ArrayIndex(self, node: ast.ArrayIndex, _pop=None) -> str:
        arr = self._fmt_expr(node.array)
        idx = self._fmt_expr(node.index)
        return f"{arr}[{idx}]"

    def _expr_ArraySlice(self, node: ast.ArraySlice, _pop=None) -> str:
        arr   = self._fmt_expr(node.array)
        start = self._fmt_expr(node.start) if node.start is not None else ""
        stop  = self._fmt_expr(node.stop)  if node.stop  is not None else ""
        return f"{arr}[{start}:{stop}]"

    def _expr_ArrayAssign(self, node: ast.ArrayAssign, _pop=None) -> str:
        # When used as expression (rare — usually a statement)
        arr = self._fmt_expr(node.array)
        idx = self._fmt_expr(node.index)
        val = self._fmt_expr(node.value)
        return f"{arr}[{idx}] = {val}"

    def _expr_DictLiteral(self, node: ast.DictLiteral, _pop=None) -> str:
        if not node.keys:
            return "{}"
        pairs = []
        for k, v in zip(node.keys, node.values):
            pairs.append(f"{self._fmt_expr(k)}: {self._fmt_expr(v)}")
        return "{" + ", ".join(pairs) + "}"

    def _expr_DictIndex(self, node: ast.DictIndex, _pop=None) -> str:
        return f"{self._fmt_expr(node.obj)}[{self._fmt_expr(node.key)}]"

    def _expr_DictAssign(self, node: ast.DictAssign, _pop=None) -> str:
        return f"{self._fmt_expr(node.obj)}[{self._fmt_expr(node.key)}] = {self._fmt_expr(node.value)}"

    def _expr_AttributeGet(self, node: ast.AttributeGet, _pop=None) -> str:
        return f"{self._fmt_expr(node.obj)}.{node.attr}"

    def _expr_AttributeSet(self, node: ast.AttributeSet, _pop=None) -> str:
        return f"{self._fmt_expr(node.obj)}.{node.attr} = {self._fmt_expr(node.value)}"

    def _expr_MethodCall(self, node: ast.MethodCall, _pop=None) -> str:
        obj  = self._fmt_expr(node.obj)
        args = ", ".join(self._fmt_expr(a) for a in node.args)
        return f"{obj}.{node.method}({args})"

    # Expression stubs for nodes that only appear as statements
    def _expr_FuncDecl(self, node: ast.FuncDecl, _pop=None) -> str:
        return f"<func {node.name}>"

    def _expr_LambdaExpr_as_expr(self, node, _pop=None) -> str:
        return self._expr_LambdaExpr(node, _pop)


# ── Public API ───────────────────────────────────────────────────────────────

def format_source(source: str, *, indent_width: int = 4) -> str:
    """
    Parse *source* and return the canonically-formatted string.

    Parameters
    ----------
    source : str
        Raw GravLang source code.
    indent_width : int
        Spaces per indentation level (default 4).

    Returns
    -------
    str
        Formatted source with a single trailing newline.

    Raises
    ------
    GravLangError
        If the source contains lexer or parse errors.
    """
    tokens = Lexer(source).tokenize()
    tree   = Parser(tokens).parse()
    return Formatter(indent_width=indent_width).format(tree)


def format_file(path: str, *, indent_width: int = 4) -> str:
    """
    Read *path*, format it, and return the formatted string.

    Parameters
    ----------
    path : str
        Path to a ``.grav`` source file.
    indent_width : int
        Spaces per indentation level (default 4).

    Returns
    -------
    str
        Formatted source.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    return format_source(source, indent_width=indent_width)


# ── CLI entry point ──────────────────────────────────────────────────────────

def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        prog="grav fmt",
        description="GravLang source formatter — reads a .grav file and "
                    "writes canonical, consistently-indented source.",
    )
    ap.add_argument("file", help="Path to the .grav source file")
    ap.add_argument(
        "-w", "--write",
        action="store_true",
        help="Write formatted output back to the input file in-place",
    )
    ap.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write formatted output to FILE instead of stdout",
    )
    ap.add_argument(
        "--indent",
        type=int,
        default=4,
        metavar="N",
        help="Number of spaces per indentation level (default: 4)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if the file is not already formatted (dry-run)",
    )
    args = ap.parse_args()

    try:
        with open(args.file, encoding="utf-8") as fh:
            original = fh.read()
        formatted = format_source(original, indent_width=args.indent)
    except FileNotFoundError:
        print(f"grav fmt: file not found — {args.file}", file=sys.stderr)
        sys.exit(1)
    except GravLangError as exc:
        print(f"grav fmt: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        if formatted != original:
            print(f"grav fmt: {args.file} would be reformatted", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"grav fmt: {args.file} is already formatted")
        return

    if args.write:
        with open(args.file, "w", encoding="utf-8") as fh:
            fh.write(formatted)
        print(f"grav fmt: reformatted {args.file}")
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(formatted)
        print(f"grav fmt: wrote {args.output}")
    else:
        sys.stdout.write(formatted)


if __name__ == "__main__":
    _cli()
