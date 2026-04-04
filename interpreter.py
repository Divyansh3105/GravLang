"""
GravLang — Tree-walk interpreter.

Uses the visitor pattern: ``visit(node)`` dispatches to
``visit_<NodeType>(node)`` for each AST class.
"""

from __future__ import annotations
import sys
import ast_nodes as ast
from environment import Environment
from grav_builtins import register_builtins
from errors import GravLangRuntimeError, BreakSignal, ContinueSignal
from gravlang_class import GravLangClass, GravLangInstance

# Raise Python's own recursion limit so our depth check always fires first
sys.setrecursionlimit(5000)


# ── Sentinel for function returns ────────────────────────────────────

class ReturnSignal(Exception):
    """Raised inside functions to unwind the call stack and carry the return value."""
    def __init__(self, value: object = None):
        self.value = value


# ── GravLang callable wrapper ────────────────────────────────────────

class GravFunction:
    """A user-defined GravLang function (stores the AST node + closure env)."""

    def __init__(self, decl: ast.FuncDecl, closure: Environment):
        self.decl = decl
        self.closure = closure

    def __repr__(self) -> str:
        return f"<func {self.decl.name}>"


# ── Interpreter ──────────────────────────────────────────────────────

class Interpreter:
    """Tree-walk interpreter for GravLang ASTs."""

    def __init__(self, *, print_fn=None, source: str = ""):
        """
        Parameters
        ----------
        print_fn : callable, optional
            Override for ``print()`` — used by the GUI to redirect output.
        source : str, optional
            Original source code — used for contextual error messages.
        """
        self.global_env = Environment()
        register_builtins(self.global_env)

        # Source lines for error messages
        self._source_lines = source.splitlines() if source else []

        # Call-stack depth tracking
        self._call_depth = 0
        self._max_depth = 200

        if print_fn is not None:
            self.global_env.set("print", print_fn)

    # ── source-line helper ───────────────────────────────────────────

    def _get_source_line(self, line_no) -> str:
        """Return stripped source text for a 1-based line number."""
        if line_no and 1 <= line_no <= len(self._source_lines):
            return self._source_lines[line_no - 1].strip()
        return ""

    # ── public API ───────────────────────────────────────────────────

    def interpret(self, program: ast.Program) -> None:
        for stmt in program.body:
            self._exec(stmt, self.global_env)

    # ── dispatch ─────────────────────────────────────────────────────

    def _exec(self, node, env: Environment):
        method_name = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            raise GravLangRuntimeError(f"Unknown AST node: {type(node).__name__}")
        return visitor(node, env)

    # ── statements ───────────────────────────────────────────────────

    def _visit_Program(self, node: ast.Program, env: Environment):
        for stmt in node.body:
            self._exec(stmt, env)

    def _visit_VarDecl(self, node: ast.VarDecl, env: Environment):
        value = self._exec(node.value, env)
        env.set(node.name, value)

    def _visit_Assign(self, node: ast.Assign, env: Environment):
        value = self._exec(node.value, env)
        try:
            env.assign(node.name, value)
        except GravLangRuntimeError:
            raise GravLangRuntimeError(
                f"Cannot assign to undefined variable: '{node.name}'",
                node.line, self._get_source_line(node.line),
            )

    def _visit_AugAssign(self, node: ast.AugAssign, env: Environment):
        """Handle  x += expr ;  etc."""
        try:
            current = env.get(node.name)
        except GravLangRuntimeError:
            raise GravLangRuntimeError(
                f"Undefined variable: '{node.name}'",
                node.line, self._get_source_line(node.line),
            )
        new_val = self._exec(node.value, env)
        if node.op == "+":
            if isinstance(current, str) or isinstance(new_val, str):
                result = str(current) + str(new_val)
            else:
                result = current + new_val
        elif node.op == "-":
            result = current - new_val
        elif node.op == "*":
            result = current * new_val
        elif node.op == "/":
            if new_val == 0:
                raise GravLangRuntimeError("Division by zero", node.line,
                                           self._get_source_line(node.line))
            result = current / new_val
        elif node.op == "//":  # FIXED: added //= augmented floor-div support
            if new_val == 0:
                raise GravLangRuntimeError("Division by zero", node.line,
                                           self._get_source_line(node.line))
            result = current // new_val
        elif node.op == "%":   # FIXED: added %= augmented modulo support
            if new_val == 0:
                raise GravLangRuntimeError("Modulo by zero", node.line,
                                           self._get_source_line(node.line))
            result = current % new_val
        else:
            raise GravLangRuntimeError(f"Unknown augmented operator: {node.op}", node.line)
        env.assign(node.name, result)

    def _visit_IfStmt(self, node: ast.IfStmt, env: Environment):
        if self._truthy(self._exec(node.condition, env)):
            return self._exec(node.body, env)
        for cond, body in node.elif_clauses:
            if self._truthy(self._exec(cond, env)):
                return self._exec(body, env)
        if node.else_body is not None:
            return self._exec(node.else_body, env)

    def _visit_WhileStmt(self, node: ast.WhileStmt, env: Environment):
        while self._truthy(self._exec(node.condition, env)):
            try:
                self._exec(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _visit_ForStmt(self, node: ast.ForStmt, env: Environment):
        loop_env = Environment(parent=env)
        self._exec(node.init, loop_env)
        while self._truthy(self._exec(node.condition, loop_env)):
            try:
                self._exec(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                pass  # fall through to update (correct for-loop continue)
            self._exec(node.update, loop_env)

    def _visit_ForInStmt(self, node: ast.ForInStmt, env: Environment):
        iterable = self._exec(node.iterable, env)
        if not isinstance(iterable, list):
            raise GravLangRuntimeError(
                "for...in loop requires an array", node.line,
                self._get_source_line(node.line),
            )
        for item in iterable:
            loop_env = Environment(parent=env)
            loop_env.set(node.var, item)
            try:
                self._exec(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _visit_FuncDecl(self, node: ast.FuncDecl, env: Environment):
        fn = GravFunction(node, closure=env)
        env.set(node.name, fn)

    def _visit_ReturnStmt(self, node: ast.ReturnStmt, env: Environment):
        value = None
        if node.value is not None:
            value = self._exec(node.value, env)
        raise ReturnSignal(value)

    def _visit_BreakStmt(self, node: ast.BreakStmt, env: Environment):
        raise BreakSignal()

    def _visit_ContinueStmt(self, node: ast.ContinueStmt, env: Environment):
        raise ContinueSignal()

    def _visit_Block(self, node: ast.Block, env: Environment):
        block_env = Environment(parent=env)
        for stmt in node.statements:
            self._exec(stmt, block_env)

    # ── class statements ─────────────────────────────────────────────

    def _visit_ClassDecl(self, node: ast.ClassDecl, env: Environment):
        parent = None
        if node.parent is not None:
            try:
                parent = env.get(node.parent)
            except GravLangRuntimeError:
                raise GravLangRuntimeError(
                    f"Undefined parent class: '{node.parent}'",
                    node.line, self._get_source_line(node.line),
                )
            if not isinstance(parent, GravLangClass):
                raise GravLangRuntimeError(
                    f"'{node.parent}' is not a class", node.line,
                )
        methods = {m.name: m for m in node.methods}
        klass = GravLangClass(name=node.name, parent=parent, methods=methods)
        env.set(node.name, klass)

    # ── expressions ──────────────────────────────────────────────────

    def _visit_Literal(self, node: ast.Literal, _env: Environment):
        return node.value

    def _visit_Identifier(self, node: ast.Identifier, env: Environment):
        try:
            return env.get(node.name)
        except GravLangRuntimeError:
            raise GravLangRuntimeError(
                f"Undefined variable: '{node.name}'",
                node.line, self._get_source_line(node.line),
            )

    def _visit_SelfExpr(self, node: ast.SelfExpr, env: Environment):
        try:
            return env.get("self")
        except GravLangRuntimeError:
            raise GravLangRuntimeError(
                "'self' used outside of a class method",
                node.line, self._get_source_line(node.line),
            )

    def _visit_UnaryOp(self, node: ast.UnaryOp, env: Environment):
        operand = self._exec(node.operand, env)
        if node.op == "-":
            return -operand
        if node.op == "not":
            return not self._truthy(operand)
        raise GravLangRuntimeError(f"Unknown unary operator: {node.op}", node.line)

    def _visit_BinOp(self, node: ast.BinOp, env: Environment):
        # FIXED: documented that and/or return the last evaluated value
        # (Python-style short-circuit), NOT a boolean.  e.g.:
        #   0 and "hi"  → 0      (falsy left returned)
        #   1 and "hi"  → "hi"   (right returned)
        #   0 or  "hi"  → "hi"   (right returned)
        #   1 or  "hi"  → 1      (truthy left returned)
        if node.op == "and":
            left = self._exec(node.left, env)
            return self._exec(node.right, env) if self._truthy(left) else left
        if node.op == "or":
            left = self._exec(node.left, env)
            return left if self._truthy(left) else self._exec(node.right, env)

        left = self._exec(node.left, env)
        right = self._exec(node.right, env)

        try:
            match node.op:
                case "+":
                    if isinstance(left, str) or isinstance(right, str):
                        return str(left) + str(right)
                    return left + right
                case "-":  return left - right
                case "*":  return left * right
                case "/":
                    if right == 0:
                        raise GravLangRuntimeError("Division by zero", node.line,
                                                   self._get_source_line(node.line))
                    return left / right        # always true division
                case "//":
                    if right == 0:
                        raise GravLangRuntimeError("Division by zero", node.line,
                                                   self._get_source_line(node.line))
                    return left // right        # floor (integer) division
                case "%":
                    if right == 0:
                        raise GravLangRuntimeError("Modulo by zero", node.line,
                                                   self._get_source_line(node.line))
                    return left % right
                case "**": return left ** right
                case "==": return left == right
                case "!=": return left != right
                case "<":  return left < right
                case ">":  return left > right
                case "<=": return left <= right
                case ">=": return left >= right
                case _:
                    raise GravLangRuntimeError(f"Unknown operator: {node.op}", node.line)
        except TypeError as e:
            raise GravLangRuntimeError(
                f"Type error in '{node.op}': {e}",
                node.line, self._get_source_line(node.line),
            )

    def _visit_FuncCall(self, node: ast.FuncCall, env: Environment):
        try:
            callee = env.get(node.name)
        except GravLangRuntimeError:
            raise GravLangRuntimeError(
                f"Undefined function: '{node.name}'",
                node.line, self._get_source_line(node.line),
            )
        args = [self._exec(arg, env) for arg in node.args]

        # Class instantiation
        if isinstance(callee, GravLangClass):
            return self._instantiate(callee, args, node.line)

        # Python callable (built-in)
        if callable(callee) and not isinstance(callee, GravFunction):
            try:
                return callee(*args)
            except TypeError as e:
                raise GravLangRuntimeError(str(e), node.line)

        # User-defined function
        if isinstance(callee, GravFunction):
            return self._call_function(callee, args, node.line)

        raise GravLangRuntimeError(f"'{node.name}' is not callable", node.line)

    # ── array expressions ────────────────────────────────────────────

    def _visit_ArrayLiteral(self, node: ast.ArrayLiteral, env: Environment):
        return [self._exec(elem, env) for elem in node.elements]

    def _visit_ArrayIndex(self, node: ast.ArrayIndex, env: Environment):
        array = self._exec(node.array, env)
        index = self._exec(node.index, env)
        if isinstance(array, str):  # FIXED: support string indexing
            if not isinstance(index, int):
                raise GravLangRuntimeError("String index must be an integer", node.line)
            try:
                return array[index]  # FIXED: return single-character string
            except IndexError:
                raise GravLangRuntimeError(
                    f"String index {index} out of range (length {len(array)})", node.line,
                )
        if not isinstance(array, list):
            raise GravLangRuntimeError("Indexing requires an array or string", node.line)  # FIXED: updated error msg
        if not isinstance(index, int):
            raise GravLangRuntimeError("Array index must be an integer", node.line)
        try:
            return array[index]
        except IndexError:
            raise GravLangRuntimeError(
                f"Array index {index} out of range (length {len(array)})", node.line,
            )

    def _visit_ArrayAssign(self, node: ast.ArrayAssign, env: Environment):
        array = self._exec(node.array, env)
        index = self._exec(node.index, env)
        value = self._exec(node.value, env)
        if not isinstance(array, list):
            raise GravLangRuntimeError("Index assignment requires an array", node.line)
        if not isinstance(index, int):
            raise GravLangRuntimeError("Array index must be an integer", node.line)
        try:
            array[index] = value
        except IndexError:
            raise GravLangRuntimeError(
                f"Array index {index} out of range (length {len(array)})", node.line,
            )

    def _visit_ArraySlice(self, node: ast.ArraySlice, env: Environment):
        array = self._exec(node.array, env)
        start = self._exec(node.start, env) if node.start is not None else None
        stop = self._exec(node.stop, env) if node.stop is not None else None
        if not isinstance(array, list):
            raise GravLangRuntimeError("Slicing requires an array", node.line)
        return array[start:stop]

    # ── OOP expressions ──────────────────────────────────────────────

    def _visit_AttributeGet(self, node: ast.AttributeGet, env: Environment):
        obj = self._exec(node.obj, env)
        if isinstance(obj, GravLangInstance):
            try:
                return obj.get(node.attr)
            except AttributeError:
                raise GravLangRuntimeError(
                    f"'{obj.klass.name}' object has no attribute '{node.attr}'",
                    node.line, self._get_source_line(node.line),
                )
        raise GravLangRuntimeError(
            f"Cannot read attribute '{node.attr}' on non-object", node.line,
        )

    def _visit_AttributeSet(self, node: ast.AttributeSet, env: Environment):
        obj = self._exec(node.obj, env)
        value = self._exec(node.value, env)
        if isinstance(obj, GravLangInstance):
            obj.set(node.attr, value)
            return
        raise GravLangRuntimeError(
            f"Cannot set attribute '{node.attr}' on non-object", node.line,
        )

    def _visit_MethodCall(self, node: ast.MethodCall, env: Environment):
        obj = self._exec(node.obj, env)
        if not isinstance(obj, GravLangInstance):
            raise GravLangRuntimeError(
                f"Cannot call method '{node.method}' on non-object", node.line,
            )
        method_decl = obj.klass.find_method(node.method)
        if method_decl is None:
            raise GravLangRuntimeError(
                f"'{obj.klass.name}' object has no method '{node.method}'",
                node.line, self._get_source_line(node.line),
            )
        args = [self._exec(arg, env) for arg in node.args]
        if len(args) != len(method_decl.params):
            raise GravLangRuntimeError(
                f"Method '{node.method}' expects {len(method_decl.params)} "
                f"argument(s), got {len(args)}", node.line,
            )
        # Call with depth tracking
        self._call_depth += 1
        if self._call_depth > self._max_depth:
            self._call_depth = 0
            raise GravLangRuntimeError(
                f"Stack overflow: maximum call depth ({self._max_depth}) exceeded",
                node.line, self._get_source_line(node.line),
            )
        try:
            method_env = Environment(parent=self.global_env)
            method_env.set("self", obj)
            for param, arg in zip(method_decl.params, args):
                method_env.set(param, arg)
            try:
                self._exec(method_decl.body, method_env)
            except ReturnSignal as ret:
                return ret.value
            return None
        finally:
            self._call_depth -= 1

    # ── helper: call a GravFunction (with depth tracking) ────────────

    def _call_function(self, fn: GravFunction, args: list, line: int):
        if len(args) != len(fn.decl.params):
            raise GravLangRuntimeError(
                f"Function '{fn.decl.name}' expects {len(fn.decl.params)} "
                f"argument(s), got {len(args)}", line,
            )
        self._call_depth += 1
        if self._call_depth > self._max_depth:
            self._call_depth = 0
            raise GravLangRuntimeError(
                f"Stack overflow: maximum call depth ({self._max_depth}) exceeded",
                line, self._get_source_line(line),
            )
        try:
            call_env = Environment(parent=fn.closure)
            for param, arg in zip(fn.decl.params, args):
                call_env.set(param, arg)
            try:
                self._exec(fn.decl.body, call_env)
            except ReturnSignal as ret:
                return ret.value
            return None
        finally:
            self._call_depth -= 1

    # ── helper: instantiate a class (with depth tracking) ────────────

    def _instantiate(self, klass: GravLangClass, args: list, line: int):
        instance = GravLangInstance(klass)
        init_method = klass.find_method("init")
        if init_method is not None:
            if len(args) != len(init_method.params):
                raise GravLangRuntimeError(
                    f"Class '{klass.name}' init() expects {len(init_method.params)} "
                    f"argument(s), got {len(args)}", line,
                )
            self._call_depth += 1
            if self._call_depth > self._max_depth:
                self._call_depth = 0
                raise GravLangRuntimeError(
                    f"Stack overflow: maximum call depth ({self._max_depth}) exceeded",
                    line, self._get_source_line(line),
                )
            try:
                init_env = Environment(parent=self.global_env)
                init_env.set("self", instance)
                for param, arg in zip(init_method.params, args):
                    init_env.set(param, arg)
                try:
                    self._exec(init_method.body, init_env)
                except ReturnSignal:
                    pass
            finally:
                self._call_depth -= 1
        else:
            if args:
                raise GravLangRuntimeError(
                    f"Class '{klass.name}' has no init() but received arguments", line,
                )
        return instance

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _truthy(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return True
