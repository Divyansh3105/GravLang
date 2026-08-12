"""
GravLang — AST node definitions.

Every node is a frozen-friendly dataclass so the parser can build an
immutable syntax tree that the interpreter walks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ── Program (root node) ─────────────────────────────────────────────

@dataclass
class Program:
    """Top-level container: a list of statements."""
    body: list = field(default_factory=list)


# ── Statements ──────────────────────────────────────────────────────

@dataclass
class VarDecl:
    """Variable declaration: let <name> = <expr>;"""
    name: str
    value: Any  # expression node
    line: int = 0


@dataclass
class Assign:
    """Variable assignment: <name> = <expr>;"""
    name: str
    value: Any
    line: int = 0


@dataclass
class AugAssign:
    """Augmented assignment: <name> += / -= / *= / /= <expr>;"""
    name: str
    op: str        # "+", "-", "*", "/"
    value: Any     # right-hand expression
    line: int = 0


@dataclass
class IfStmt:
    """if / elif / else chain."""
    condition: Any
    body: Any            # Block
    elif_clauses: list = field(default_factory=list)
    else_body: Any = None
    line: int = 0


@dataclass
class WhileStmt:
    """while (condition) { body } [else { else_body }] [finally { finally_body }]

    else_body   — runs if the loop exits normally (condition became false), NOT via break.
    finally_body — runs unconditionally after the loop, whether or not break was used.
    """
    condition: Any
    body: Any
    else_body: Any = None
    finally_body: Any = None
    line: int = 0


@dataclass
class ForStmt:
    """for (init; condition; update) { body } [else { else_body }] [finally { finally_body }]

    else_body   — runs if the loop exits normally (condition became false), NOT via break.
    finally_body — runs unconditionally after the loop, whether or not break was used.
    """
    init: Any
    condition: Any
    update: Any
    body: Any
    else_body: Any = None
    finally_body: Any = None
    line: int = 0


@dataclass
class ForInStmt:
    """for (item in iterable) { body } [else { else_body }] [finally { finally_body }]

    else_body   — runs if the loop exits normally (no break hit).
    finally_body — runs unconditionally after the loop ends.
    """
    var: str        # loop variable name
    iterable: Any   # expression that evaluates to a list
    body: Any       # Block
    else_body: Any = None
    finally_body: Any = None
    line: int = 0


@dataclass
class FuncDecl:
    """func <name>(<params> [, ...<variadic>]) { body }

    variadic -- if not None, the name of the variadic parameter that
                collects all excess positional arguments into a list.
    """
    name: str
    params: list
    body: Any
    variadic: str | None = None   # name of ...rest param, or None
    line: int = 0


@dataclass
class LambdaExpr:
    """Anonymous function expression: func(params) { body }

    Produces a first-class function value (GravFunction) when evaluated.
    May appear anywhere an expression is valid:
        let double = func(x) { return x * 2; };
        arr.map(func(x) { return x + 1; });
    """
    params: list
    body: Any
    variadic: str | None = None   # same semantics as FuncDecl.variadic
    line: int = 0


@dataclass
class CallExpr:
    """Call an arbitrary expression as a function: callee(args)

    Unlike FuncCall (which looks up a name), CallExpr evaluates 'callee'
    as a full expression first. This enables:
        makeAdder(5)(10)
        funcs[0](x)
        getCallback()()
    """
    callee: Any     # any expression node that evaluates to a callable
    args: list = field(default_factory=list)
    line: int = 0


@dataclass
class ReturnStmt:
    """return <expr>;"""
    value: Any = None
    line: int = 0


@dataclass
class ImportStmt:
    """import "path/to/module.grav";

    path  — the literal string path as written in source (may be relative).
    The interpreter resolves it relative to the importing file's directory.
    """
    path: str
    line: int = 0


@dataclass
class BreakStmt:
    """break;"""
    line: int = 0


@dataclass
class ContinueStmt:
    """continue;"""
    line: int = 0


@dataclass
class Block:
    """A { ... } block containing a list of statements."""
    statements: list = field(default_factory=list)


# ── Expressions ─────────────────────────────────────────────────────

@dataclass
class BinOp:
    """Binary operation: left <op> right."""
    left: Any
    op: str
    right: Any
    line: int = 0


@dataclass
class UnaryOp:
    """Unary operation: <op> operand   (e.g. -x, not flag)."""
    op: str
    operand: Any
    line: int = 0


@dataclass
class Literal:
    """A literal value: int, float, string, bool, or None."""
    value: Any
    line: int = 0


@dataclass
class Identifier:
    """A variable / function name reference."""
    name: str
    line: int = 0


@dataclass
class FuncCall:
    """Function call: <name>(<args>)."""
    name: str
    args: list = field(default_factory=list)
    line: int = 0


# ── Array nodes ─────────────────────────────────────────────────────

@dataclass
class ArrayLiteral:
    """Array literal: [elem1, elem2, ...]."""
    elements: list = field(default_factory=list)
    line: int = 0


@dataclass
class ArrayIndex:
    """Array index read: arr[index]."""
    array: Any
    index: Any
    line: int = 0


@dataclass
class ArrayAssign:
    """Array index write: arr[index] = value;"""
    array: Any
    index: Any
    value: Any
    line: int = 0


@dataclass
class ArraySlice:
    """Array slice: arr[start:stop]."""
    array: Any
    start: Any = None
    stop: Any = None
    line: int = 0


# ── Dictionary nodes ───────────────────────────────────────────────────

@dataclass
class DictLiteral:
    """Dict literal: { key: value, ... }

    keys   — list of expression nodes (evaluated as dict keys).
    values — parallel list of value expression nodes.
    """
    keys: list = field(default_factory=list)
    values: list = field(default_factory=list)
    line: int = 0


@dataclass
class DictIndex:
    """Dict read: dict[key]"""
    obj: Any
    key: Any
    line: int = 0


@dataclass
class DictAssign:
    """Dict write: dict[key] = value"""
    obj: Any
    key: Any
    value: Any
    line: int = 0


# ── Class / OOP nodes ──────────────────────────────────────────────

@dataclass
class ClassDecl:
    """class Name [extends Parent] { methods }"""
    name: str
    parent: str | None = None
    methods: list = field(default_factory=list)
    line: int = 0


@dataclass
class AttributeGet:
    """Attribute read: obj.attr"""
    obj: Any
    attr: str
    line: int = 0


@dataclass
class AttributeSet:
    """Attribute write: obj.attr = value;"""
    obj: Any
    attr: str
    value: Any
    line: int = 0


@dataclass
class MethodCall:
    """Method call: obj.method(args)"""
    obj: Any
    method: str
    args: list = field(default_factory=list)
    line: int = 0


@dataclass
class SelfExpr:
    """Reference to 'self' inside a class method."""
    line: int = 0
