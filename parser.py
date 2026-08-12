"""
GravLang — Recursive-descent parser.

Consumes a list of tokens produced by the Lexer and builds an AST
defined in ast_nodes.py.

Operator precedence (low → high):
    or  →  and  →  not  →  comparison  →  add/sub  →  mul/div/mod/floordiv  →  power  →  unary minus  →  call/index/dot  →  atom
"""

from __future__ import annotations
import re as _re
from lexer import Token, Lexer
from errors import ParseError
import ast_nodes as ast

# Augmented-assignment token map
_AUG_OPS = {
    "PLUS_ASSIGN":     "+",
    "MINUS_ASSIGN":    "-",
    "STAR_ASSIGN":     "*",
    "SLASH_ASSIGN":    "/",
    "FLOORDIV_ASSIGN": "//",  # FIXED: added //= augmented operator
    "MOD_ASSIGN":      "%",   # FIXED: added %= augmented operator
}


class Parser:
    """Recursive-descent parser for GravLang."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ── helpers ──────────────────────────────────────────────────────

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _match(self, *types: str) -> Token | None:
        if self._current().type in types:
            return self._advance()
        return None

    def _expect(self, ttype: str, msg: str | None = None) -> Token:
        tok = self._current()
        if tok.type != ttype:
            msg = msg or f"Expected {ttype}, got {tok.type} ({tok.value!r})"
            raise ParseError(msg, tok.line)
        return self._advance()

    # ── entry point ──────────────────────────────────────────────────

    def parse(self) -> ast.Program:
        stmts: list = []
        while self._current().type != "EOF":
            stmts.append(self._statement())
        return ast.Program(body=stmts)

    # ── statements ───────────────────────────────────────────────────

    def _statement(self):
        tok = self._current()

        if tok.type == "LET":
            return self._var_decl()
        if tok.type == "IF":
            return self._if_stmt()
        if tok.type == "WHILE":
            return self._while_stmt()
        if tok.type == "FOR":
            return self._for_stmt()
        if tok.type == "FUNC":
            return self._func_decl()
        if tok.type == "RETURN":
            return self._return_stmt()
        if tok.type == "CLASS":
            return self._class_decl()
        if tok.type == "BREAK":
            return self._break_stmt()
        if tok.type == "CONTINUE":
            return self._continue_stmt()

        # Expression statement (assignment or bare expression / call)
        return self._expr_statement()

    # let x = expr ;
    def _var_decl(self) -> ast.VarDecl:
        line = self._current().line
        self._expect("LET")
        name_tok = self._expect("ID", "Expected variable name after 'let'")
        self._expect("ASSIGN", "Expected '=' in variable declaration")
        value = self._expression()
        self._expect("SEMI", "Expected ';' after variable declaration")
        return ast.VarDecl(name=name_tok.value, value=value, line=line)

    # if (...) { ... } elif (...) { ... } else { ... }
    def _if_stmt(self) -> ast.IfStmt:
        line = self._current().line
        self._expect("IF")
        self._expect("LPAREN", "Expected '(' after 'if'")
        condition = self._expression()
        self._expect("RPAREN", "Expected ')' after if condition")
        body = self._block()

        elif_clauses: list = []
        while self._match("ELIF"):
            self._expect("LPAREN", "Expected '(' after 'elif'")
            elif_cond = self._expression()
            self._expect("RPAREN", "Expected ')' after elif condition")
            elif_body = self._block()
            elif_clauses.append((elif_cond, elif_body))

        else_body = None
        if self._match("ELSE"):
            else_body = self._block()

        return ast.IfStmt(
            condition=condition, body=body,
            elif_clauses=elif_clauses, else_body=else_body,
            line=line,
        )

    # while (...) { ... }
    def _while_stmt(self) -> ast.WhileStmt:
        line = self._current().line
        self._expect("WHILE")
        self._expect("LPAREN", "Expected '(' after 'while'")
        condition = self._expression()
        self._expect("RPAREN", "Expected ')' after while condition")
        body = self._block()

        else_body    = None
        finally_body = None
        if self._current().type == "ELSE":
            self._advance()
            else_body = self._block()
        if self._current().type == "FINALLY":
            self._advance()
            finally_body = self._block()

        return ast.WhileStmt(
            condition=condition, body=body,
            else_body=else_body, finally_body=finally_body,
            line=line,
        )

    # for (...) { ... }  — classic OR for-in
    def _for_stmt(self):
        line = self._current().line
        self._expect("FOR")
        self._expect("LPAREN", "Expected '(' after 'for'")

        # ── Detect for-in  vs  classic for ───────────────────────────
        is_for_in = False
        if self._current().type == "LET":
            # for (let x in ...)
            if self._peek(1).type == "ID" and self._peek(2).type == "IN":
                is_for_in = True
        elif self._current().type == "ID" and self._peek(1).type == "IN":
            # for (x in ...)
            is_for_in = True

        if is_for_in:
            if self._current().type == "LET":
                self._advance()  # consume optional 'let'
            var_tok = self._expect("ID", "Expected loop variable name")
            self._expect("IN", "Expected 'in' after loop variable")
            iterable = self._expression()
            self._expect("RPAREN", "Expected ')' after iterable")
            body = self._block()

            else_body    = None
            finally_body = None
            if self._current().type == "ELSE":
                self._advance()
                else_body = self._block()
            if self._current().type == "FINALLY":
                self._advance()
                finally_body = self._block()

            return ast.ForInStmt(
                var=var_tok.value, iterable=iterable,
                body=body, else_body=else_body, finally_body=finally_body,
                line=line,
            )

        # ── Classic for (init; cond; update) ─────────────────────────
        if self._current().type == "LET":
            init = self._var_decl_no_semi()
        else:
            init = self._assignment_or_expr()
        self._expect("SEMI", "Expected ';' after for-init")

        condition = self._expression()
        self._expect("SEMI", "Expected ';' after for-condition")

        update = self._assignment_or_expr()
        self._expect("RPAREN", "Expected ')' after for-update")

        body = self._block()

        else_body    = None
        finally_body = None
        if self._current().type == "ELSE":
            self._advance()
            else_body = self._block()
        if self._current().type == "FINALLY":
            self._advance()
            finally_body = self._block()

        return ast.ForStmt(
            init=init, condition=condition, update=update, body=body,
            else_body=else_body, finally_body=finally_body,
            line=line,
        )

    # break ;
    def _break_stmt(self) -> ast.BreakStmt:
        line = self._current().line
        self._expect("BREAK")
        self._expect("SEMI", "Expected ';' after break")
        return ast.BreakStmt(line=line)

    # continue ;
    def _continue_stmt(self) -> ast.ContinueStmt:
        line = self._current().line
        self._expect("CONTINUE")
        self._expect("SEMI", "Expected ';' after continue")
        return ast.ContinueStmt(line=line)

    # Helper: var decl without trailing ;
    def _var_decl_no_semi(self) -> ast.VarDecl:
        line = self._current().line
        self._expect("LET")
        name_tok = self._expect("ID")
        self._expect("ASSIGN")
        value = self._expression()
        return ast.VarDecl(name=name_tok.value, value=value, line=line)

    # Helper: assignment, augmented assignment, or bare expression
    def _assignment_or_expr(self):
        if self._current().type == "ID":
            # id = expr
            if self._peek(1).type == "ASSIGN":
                name_tok = self._advance()
                self._advance()  # consume '='
                value = self._expression()
                return ast.Assign(name=name_tok.value, value=value, line=name_tok.line)
            # id += / -= / *= / /= expr
            if self._peek(1).type in _AUG_OPS:
                name_tok = self._advance()
                op_tok = self._advance()
                value = self._expression()
                return ast.AugAssign(
                    name=name_tok.value, op=_AUG_OPS[op_tok.type],
                    value=value, line=name_tok.line,
                )
        return self._expression()

    # func name(params) { body }
    def _func_decl(self) -> ast.FuncDecl:
        line = self._current().line
        self._expect("FUNC")
        name_tok = self._expect("ID", "Expected function name after 'func'")
        self._expect("LPAREN", "Expected '(' after function name")

        params: list[str] = []
        variadic: str | None = None

        while self._current().type != "RPAREN" and self._current().type != "EOF":
            if self._current().type == "ELLIPSIS":
                # ...rest  — must be the last parameter
                self._advance()
                var_tok = self._expect("ID", "Expected parameter name after '...'")
                variadic = var_tok.value
                # Consume optional trailing comma, then stop
                if self._current().type == "COMMA":
                    self._advance()
                if self._current().type != "RPAREN":
                    raise ParseError(
                        "Variadic parameter '...' must be the last parameter",
                        self._current().line,
                    )
                break
            params.append(self._expect("ID", "Expected parameter name").value)
            if self._current().type == "COMMA":
                self._advance()

        self._expect("RPAREN", "Expected ')' after parameters")
        body = self._block()
        return ast.FuncDecl(
            name=name_tok.value, params=params,
            body=body, variadic=variadic, line=line,
        )


    # return expr? ;
    def _return_stmt(self) -> ast.ReturnStmt:
        line = self._current().line
        self._expect("RETURN")
        value = None
        if self._current().type != "SEMI":
            value = self._expression()
        self._expect("SEMI", "Expected ';' after return statement")
        return ast.ReturnStmt(value=value, line=line)

    # ── class declaration ────────────────────────────────────────────

    def _class_decl(self) -> ast.ClassDecl:
        line = self._current().line
        self._expect("CLASS")
        name_tok = self._expect("ID", "Expected class name after 'class'")

        parent = None
        if self._match("EXTENDS"):
            parent_tok = self._expect("ID", "Expected parent class name after 'extends'")
            parent = parent_tok.value

        self._expect("LBRACE", "Expected '{' after class declaration")

        methods: list[ast.FuncDecl] = []
        while self._current().type != "RBRACE" and self._current().type != "EOF":
            if self._current().type != "FUNC":
                raise ParseError(
                    "Only function (method) declarations allowed inside class body",
                    self._current().line,
                )
            methods.append(self._func_decl())

        self._expect("RBRACE", "Expected '}' after class body")
        return ast.ClassDecl(name=name_tok.value, parent=parent, methods=methods, line=line)

    # ── expression statement ─────────────────────────────────────────
    # Handles:   expr ;   id = expr ;   id += expr ;
    #            arr[i] = expr ;   obj.attr = expr ;   etc.

    def _expr_statement(self):
        expr = self._expression()

        # ── Simple variable assignment: id = expr ; ──────────────────
        if isinstance(expr, ast.Identifier) and self._current().type == "ASSIGN":
            self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after assignment")
            return ast.Assign(name=expr.name, value=value, line=expr.line)

        # ── Augmented variable assignment: id += expr ; ──────────────
        if isinstance(expr, ast.Identifier) and self._current().type in _AUG_OPS:
            op_tok = self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after augmented assignment")
            return ast.AugAssign(
                name=expr.name, op=_AUG_OPS[op_tok.type],
                value=value, line=expr.line,
            )

        # ── Array index assignment: arr[i] = expr ; ─────────────────
        if isinstance(expr, ast.ArrayIndex) and self._current().type == "ASSIGN":
            self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after array assignment")
            return ast.ArrayAssign(array=expr.array, index=expr.index, value=value, line=expr.line)

        # ── Array index augmented: arr[i] += expr ; (desugared) ─────
        if isinstance(expr, ast.ArrayIndex) and self._current().type in _AUG_OPS:
            op_tok = self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after augmented assignment")
            return ast.ArrayAssign(
                array=expr.array, index=expr.index,
                value=ast.BinOp(left=expr, op=_AUG_OPS[op_tok.type], right=value, line=expr.line),
                line=expr.line,
            )

        # ── Attribute assignment: obj.attr = expr ; ──────────────────
        if isinstance(expr, ast.AttributeGet) and self._current().type == "ASSIGN":
            self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after attribute assignment")
            return ast.AttributeSet(obj=expr.obj, attr=expr.attr, value=value, line=expr.line)

        # ── Attribute augmented: obj.attr += expr ; (desugared) ──────
        if isinstance(expr, ast.AttributeGet) and self._current().type in _AUG_OPS:
            op_tok = self._advance()
            value = self._expression()
            self._expect("SEMI", "Expected ';' after augmented assignment")
            return ast.AttributeSet(
                obj=expr.obj, attr=expr.attr,
                value=ast.BinOp(left=expr, op=_AUG_OPS[op_tok.type], right=value, line=expr.line),
                line=expr.line,
            )

        self._expect("SEMI", "Expected ';' after expression")
        return expr

    # { stmt* }
    def _block(self) -> ast.Block:
        self._expect("LBRACE", "Expected '{'")
        stmts: list = []
        while self._current().type != "RBRACE" and self._current().type != "EOF":
            stmts.append(self._statement())
        self._expect("RBRACE", "Expected '}'")
        return ast.Block(statements=stmts)

    # ── expressions (precedence climbing) ────────────────────────────

    def _expression(self):
        return self._or_expr()

    def _or_expr(self):
        left = self._and_expr()
        while self._current().type == "OR":
            op_tok = self._advance()
            right = self._and_expr()
            left = ast.BinOp(left=left, op="or", right=right, line=op_tok.line)
        return left

    def _and_expr(self):
        left = self._not_expr()
        while self._current().type == "AND":
            op_tok = self._advance()
            right = self._not_expr()
            left = ast.BinOp(left=left, op="and", right=right, line=op_tok.line)
        return left

    def _not_expr(self):
        if self._current().type == "NOT":
            op_tok = self._advance()
            operand = self._not_expr()
            return ast.UnaryOp(op="not", operand=operand, line=op_tok.line)
        return self._comparison()

    def _comparison(self):
        left = self._add_sub()
        comp_types = ("EQ", "NEQ", "LT", "GT", "LE", "GE")
        op_map = {"EQ": "==", "NEQ": "!=", "LT": "<", "GT": ">", "LE": "<=", "GE": ">="}
        while self._current().type in comp_types:
            op_tok = self._advance()
            right = self._add_sub()
            left = ast.BinOp(left=left, op=op_map[op_tok.type], right=right, line=op_tok.line)
        return left

    def _add_sub(self):
        left = self._mul_div()
        while self._current().type in ("PLUS", "MINUS"):
            op_tok = self._advance()
            op = "+" if op_tok.type == "PLUS" else "-"
            right = self._mul_div()
            left = ast.BinOp(left=left, op=op, right=right, line=op_tok.line)
        return left

    # * / % //
    def _mul_div(self):
        left = self._power()
        while self._current().type in ("STAR", "SLASH", "MOD", "FLOORDIV"):
            op_tok = self._advance()
            op_map = {"STAR": "*", "SLASH": "/", "MOD": "%", "FLOORDIV": "//"}
            right = self._power()
            left = ast.BinOp(left=left, op=op_map[op_tok.type], right=right, line=op_tok.line)
        return left

    # ** (right-associative)
    def _power(self):
        base = self._unary()
        if self._current().type == "POWER":
            op_tok = self._advance()
            exp = self._power()
            return ast.BinOp(left=base, op="**", right=exp, line=op_tok.line)
        return base

    # unary -
    def _unary(self):
        if self._current().type == "MINUS":
            op_tok = self._advance()
            operand = self._unary()
            return ast.UnaryOp(op="-", operand=operand, line=op_tok.line)
        return self._postfix()

    # ── postfix: function calls, array indexing, dot access ──────────

    def _postfix(self):
        node = self._atom()
        while True:
            if self._current().type == "LPAREN":
                if isinstance(node, ast.Identifier):
                    # Named call — stays as FuncCall for compatibility
                    node = self._finish_call(node.name, node.line)
                else:
                    # Callee is an expression (lambda, returned func, arr[i], etc.)
                    node = self._finish_call_expr(node)
                continue
            if self._current().type == "LBRACKET":
                node = self._finish_index(node)
                continue
            if self._current().type == "DOT":
                self._advance()
                attr_tok = self._expect("ID", "Expected attribute name after '.'")
                if self._current().type == "LPAREN":
                    self._advance()
                    args: list = []
                    if self._current().type != "RPAREN":
                        args.append(self._expression())
                        while self._match("COMMA"):
                            args.append(self._expression())
                    self._expect("RPAREN", "Expected ')' after method arguments")
                    node = ast.MethodCall(obj=node, method=attr_tok.value, args=args, line=attr_tok.line)
                else:
                    node = ast.AttributeGet(obj=node, attr=attr_tok.value, line=attr_tok.line)
                continue
            break
        return node

    def _finish_call(self, name: str, line: int) -> ast.FuncCall:
        self._expect("LPAREN")
        args: list = []
        if self._current().type != "RPAREN":
            args.append(self._expression())
            while self._match("COMMA"):
                args.append(self._expression())
        self._expect("RPAREN", "Expected ')' after arguments")
        return ast.FuncCall(name=name, args=args, line=line)

    def _finish_call_expr(self, callee_node) -> ast.CallExpr:
        """Parse (args) following an arbitrary callee expression."""
        line = self._current().line
        self._expect("LPAREN")
        args: list = []
        if self._current().type != "RPAREN":
            args.append(self._expression())
            while self._match("COMMA"):
                args.append(self._expression())
        self._expect("RPAREN", "Expected ')' after arguments")
        return ast.CallExpr(callee=callee_node, args=args, line=line)

    def _finish_index(self, array_node) -> ast.ArrayIndex | ast.ArraySlice:
        line = self._current().line
        self._expect("LBRACKET")

        if self._current().type == "COLON":
            self._advance()
            stop = self._expression() if self._current().type != "RBRACKET" else None
            self._expect("RBRACKET", "Expected ']' after slice")
            return ast.ArraySlice(array=array_node, start=None, stop=stop, line=line)

        first = self._expression()

        if self._current().type == "COLON":
            self._advance()
            stop = self._expression() if self._current().type != "RBRACKET" else None
            self._expect("RBRACKET", "Expected ']' after slice")
            return ast.ArraySlice(array=array_node, start=first, stop=stop, line=line)

        self._expect("RBRACKET", "Expected ']' after index")
        return ast.ArrayIndex(array=array_node, index=first, line=line)

    # ── atoms ────────────────────────────────────────────────────────

    def _atom(self):
        tok = self._current()

        if tok.type == "INT":
            self._advance()
            return ast.Literal(value=int(tok.value), line=tok.line)
        if tok.type == "FLOAT":
            self._advance()
            return ast.Literal(value=float(tok.value), line=tok.line)
        if tok.type == "STRING":
            self._advance()
            raw = tok.value[1:-1]
            raw = raw.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
            return ast.Literal(value=raw, line=tok.line)
        if tok.type == "TRUE":
            self._advance()
            return ast.Literal(value=True, line=tok.line)
        if tok.type == "FALSE":
            self._advance()
            return ast.Literal(value=False, line=tok.line)
        if tok.type == "NULL":
            self._advance()
            return ast.Literal(value=None, line=tok.line)
        if tok.type == "SELF":
            self._advance()
            return ast.SelfExpr(line=tok.line)
        if tok.type == "PRINT":
            self._advance()
            return self._finish_call("print", tok.line)
        if tok.type == "ID":
            self._advance()
            return ast.Identifier(name=tok.value, line=tok.line)
        if tok.type == "LPAREN":
            self._advance()
            expr = self._expression()
            self._expect("RPAREN", "Expected ')' after expression")
            return expr
        if tok.type == "FSTRING":
            self._advance()
            return self._desugar_fstring(tok.value, tok.line)
        if tok.type == "FUNC":
            return self._lambda_expr()
        if tok.type == "LBRACE":
            return self._dict_literal()
        if tok.type == "LBRACKET":
            return self._array_literal()

        raise ParseError(f"Unexpected token: {tok.type} ({tok.value!r})", tok.line)

    def _array_literal(self) -> ast.ArrayLiteral:
        line = self._current().line
        self._expect("LBRACKET")
        elements = []
        while self._current().type != "RBRACKET":
            elements.append(self._expression())
            if self._current().type == "COMMA":
                self._advance()
        self._expect("RBRACKET", "Expected ']' after array literal")
        return ast.ArrayLiteral(elements=elements, line=line)

    def _dict_literal(self) -> ast.DictLiteral:
        """Parse { key: value, key: value, ... } as a DictLiteral node."""
        line = self._current().line
        self._expect("LBRACE", "Expected '{'")
        keys: list = []
        values: list = []
        while self._current().type != "RBRACE" and self._current().type != "EOF":
            key_node = self._expression()
            self._expect("COLON", "Expected ':' after dict key")
            val_node = self._expression()
            keys.append(key_node)
            values.append(val_node)
            if self._current().type == "COMMA":
                self._advance()
        self._expect("RBRACE", "Expected '}' after dict literal")
        return ast.DictLiteral(keys=keys, values=values, line=line)

    def _lambda_expr(self) -> ast.LambdaExpr:
        """Parse an anonymous function expression: func(params) { body }

        The FUNC keyword is consumed here; there is no name.
        Supports the same parameter syntax as _func_decl, including ...rest.
        """
        line = self._current().line
        self._expect("FUNC")
        self._expect("LPAREN", "Expected '(' after 'func' in lambda expression")

        params: list[str] = []
        variadic: str | None = None

        while self._current().type != "RPAREN" and self._current().type != "EOF":
            if self._current().type == "ELLIPSIS":
                self._advance()
                var_tok = self._expect("ID", "Expected parameter name after '...'")
                variadic = var_tok.value
                if self._current().type == "COMMA":
                    self._advance()
                if self._current().type != "RPAREN":
                    raise ParseError(
                        "Variadic parameter '...' must be the last parameter",
                        self._current().line,
                    )
                break
            params.append(self._expect("ID", "Expected parameter name").value)
            if self._current().type == "COMMA":
                self._advance()

        self._expect("RPAREN", "Expected ')' after lambda parameters")
        body = self._block()
        return ast.LambdaExpr(params=params, body=body, variadic=variadic, line=line)


    def _desugar_fstring(self, raw: str, line: int):
        """Desugar an f-string token into a chain of BinOp(+) concatenations.

        f"Hello, {name}! Age={age}" becomes the AST equivalent of:
            "Hello, " + toString(name) + "! Age=" + toString(age)

        Notes
        -----
        - Expressions inside {…} are re-lexed and re-parsed, so any valid
          GravLang expression works: {x + 1}, {obj.field}, {foo(a, b)}, etc.
        - String literals inside {…} are NOT supported (the outer " would
          terminate the f-string early). Use variable references instead.
        - Each expression is wrapped in toString() so booleans print as
          "true"/"false" and arrays use GravLang format.
        """
        # Strip leading f" and trailing "
        content = raw[2:-1]

        # Apply escape sequences (same as plain STRING handling)
        content = (
            content
            .replace('\\n', '\n')
            .replace('\\t', '\t')
            .replace('\\\'', "'")
            .replace('\\"', '"')
            .replace('\\\\', '\\')
        )

        # Split into alternating [literal, expr, literal, expr, ...]
        # re.split with a capturing group yields:
        #   [lit0, expr0, lit1, expr1, ...]
        parts = _re.split(r'\{([^}]*)\}', content)

        nodes: list = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Literal segment
                if part:   # skip empty strings to keep the tree clean
                    nodes.append(ast.Literal(value=part, line=line))
            else:
                # Expression segment — re-lex + re-parse
                expr_src = part.strip()
                if not expr_src:
                    continue
                sub_tokens = Lexer(expr_src).tokenize()
                sub_parser = Parser(sub_tokens)
                expr_node = sub_parser._expression()
                # Wrap in toString() so GravLang-native types format correctly
                nodes.append(
                    ast.FuncCall(name="toString", args=[expr_node], line=line)
                )

        if not nodes:
            return ast.Literal(value="", line=line)

        # Build left-associative chain:  a + b + c + d
        result = nodes[0]
        for node in nodes[1:]:
            result = ast.BinOp(left=result, op="+", right=node, line=line)
        return result
