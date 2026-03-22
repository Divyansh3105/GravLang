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
    """while (condition) { body }"""
    condition: Any
    body: Any
    line: int = 0


@dataclass
class ForStmt:
    """for (init; condition; update) { body }"""
    init: Any
    condition: Any
    update: Any
    body: Any
    line: int = 0


@dataclass
class ForInStmt:
    """for (item in iterable) { body }"""
    var: str        # loop variable name
    iterable: Any   # expression that evaluates to a list
    body: Any       # Block
    line: int = 0


@dataclass
class FuncDecl:
    """func <name>(<params>) { body }"""
    name: str
    params: list
    body: Any
    line: int = 0


@dataclass
class ReturnStmt:
    """return <expr>;"""
    value: Any = None
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
