from dataclasses import dataclass
from typing import List, Any, Optional
from lexer import tokenize, Token

# --- AST Node Definitions ---
@dataclass
class Program:
    declarations: List[Any]

@dataclass
class ImportDecl:
    path: str

@dataclass
class FieldDecl:
    type_name: str
    name: str

@dataclass
class MethodDecl:
    return_type: str
    name: str
    params: List[tuple]
    body: List[Any]

@dataclass
class ConstructorDecl:
    class_name: str
    params: List[tuple]
    body: List[Any]

@dataclass
class ClassDecl:
    name: str
    parent: Optional[str]
    fields: List[FieldDecl]
    constructors: List[ConstructorDecl]
    methods: List[MethodDecl]

@dataclass
class FuncDecl:
    return_type: str
    name: str
    params: List[tuple]
    body: List[Any]

@dataclass
class VarDecl:
    type_name: str
    name: str
    init_expr: Any

@dataclass
class Assignment:
    target: Any
    value: Any

@dataclass
class IfStmt:
    condition: Any
    then_body: List[Any]
    else_body: Optional[List[Any]]

@dataclass
class WhileStmt:
    condition: Any
    body: List[Any]

@dataclass
class ForStmt:
    init: Optional[Any]
    condition: Optional[Any]
    step: Optional[Any]
    body: List[Any]

@dataclass
class BreakStmt:
    pass

@dataclass
class ContinueStmt:
    pass

@dataclass
class ReturnStmt:
    value: Any

@dataclass
class TryCatchStmt:
    try_body: List[Any]
    catch_param_type: str
    catch_param_name: str
    catch_body: List[Any]

@dataclass
class ThrowStmt:
    expr: Any

@dataclass
class PrintStmt:
    expr: Any

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class BinaryExpr:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryExpr:
    op: str
    operand: Any

@dataclass
class MemberAccess:
    obj: Any
    member: str

@dataclass
class MethodCall:
    obj: Any
    method: str
    args: List[Any]

@dataclass
class FuncCall:
    name: str
    args: List[Any]

@dataclass
class LambdaExpr:
    params: List[tuple]
    body: Any

@dataclass
class NewExpr:
    class_name: str
    args: List[Any]

@dataclass
class NewArrayExpr:
    element_type: str
    size: Any

@dataclass
class IndexAccess:
    obj: Any
    index: Any

@dataclass
class Variable:
    name: str

@dataclass
class Number:
    value: int

@dataclass
class StringLiteral:
    value: str

@dataclass
class BoolLiteral:
    value: bool

@dataclass
class NullLiteral:
    pass


# --- Parser Engine ---
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: str = None) -> Token:
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(f"Line {tok.line}: Expected {expected_type}, got {tok.type} ({tok.value!r})")
        self.pos += 1
        return tok

    def match(self, *expected_types) -> bool:
        if self.peek().type in expected_types:
            self.consume()
            return True
        return False

    def parse_type_name(self) -> str:
        ret_type = self.consume().value

        # Array suffix on base type (e.g. int[])
        if (self.peek().type == 'LBRACKET' and
                self.pos + 1 < len(self.tokens) and
                self.tokens[self.pos + 1].type == 'RBRACKET'):
            self.consume('LBRACKET')
            self.consume('RBRACKET')
            ret_type += '[]'

        # Function type syntax: ret_type(param_types...)
        if self.peek().type == 'LPAREN':
            self.consume('LPAREN')
            param_types = []
            if self.peek().type != 'RPAREN':
                while True:
                    param_types.append(self.parse_type_name())
                    if not self.match('COMMA'):
                        break
            self.consume('RPAREN')
            fn_type = f"{ret_type}({','.join(param_types)})"
            if (self.peek().type == 'LBRACKET' and
                    self.pos + 1 < len(self.tokens) and
                    self.tokens[self.pos + 1].type == 'RBRACKET'):
                self.consume('LBRACKET')
                self.consume('RBRACKET')
                fn_type += '[]'
            return fn_type

        return ret_type

    def parse(self) -> Program:
        decls = []
        while self.peek().type != 'EOF':
            if self.peek().type == 'IMPORT':
                decls.append(self.parse_import())
            elif self.peek().type == 'CLASS':
                decls.append(self.parse_class())
            else:
                decls.append(self.parse_function())
        return Program(decls)

    def parse_import(self) -> ImportDecl:
        self.consume('IMPORT')
        tok = self.consume('STRING')
        path = tok.value.strip('"')
        self.consume('SEMICOLON')
        return ImportDecl(path)

    def parse_class(self) -> ClassDecl:
        self.consume('CLASS')
        class_name = self.consume('IDENTIFIER').value

        parent = None
        if self.peek().type == 'EXTENDS':
            self.consume('EXTENDS')
            parent = self.consume('IDENTIFIER').value

        self.consume('LBRACE')

        fields = []
        constructors = []
        methods = []

        while self.peek().type != 'RBRACE':
            first_tok = self.peek()

            # Disambiguate constructor ClassName(...) { vs method/field returning ClassName(...)
            is_constructor = False
            if first_tok.value == class_name and self.tokens[self.pos + 1].type == 'LPAREN':
                i = self.pos + 2
                depth = 1
                while i < len(self.tokens) and depth > 0:
                    if self.tokens[i].type == 'LPAREN':
                        depth += 1
                    elif self.tokens[i].type == 'RPAREN':
                        depth -= 1
                    i += 1
                if depth == 0 and i < len(self.tokens) and self.tokens[i].type == 'LBRACE':
                    is_constructor = True

            if is_constructor:
                self.consume()  # class_name
                self.consume('LPAREN')
                params = self.parse_params()
                self.consume('RPAREN')
                body = self.parse_block()
                constructors.append(ConstructorDecl(class_name, params, body))
                continue

            type_name = self.parse_type_name()
            member_name = self.consume('IDENTIFIER').value

            if self.peek().type == 'LPAREN':
                self.consume('LPAREN')
                params = self.parse_params()
                self.consume('RPAREN')
                body = self.parse_block()
                methods.append(MethodDecl(type_name, member_name, params, body))
            else:
                self.consume('SEMICOLON')
                fields.append(FieldDecl(type_name, member_name))

        self.consume('RBRACE')
        return ClassDecl(class_name, parent, fields, constructors, methods)

    def parse_function(self) -> FuncDecl:
        ret_type = self.parse_type_name()
        name = self.consume('IDENTIFIER').value
        self.consume('LPAREN')
        params = self.parse_params()
        self.consume('RPAREN')
        body = self.parse_block()
        return FuncDecl(ret_type, name, params, body)

    def parse_params(self) -> List[tuple]:
        params = []
        if self.peek().type != 'RPAREN':
            while True:
                p_type = self.parse_type_name()
                p_name = self.consume('IDENTIFIER').value
                params.append((p_type, p_name))
                if not self.match('COMMA'):
                    break
        return params

    def parse_block(self) -> List[Any]:
        self.consume('LBRACE')
        stmts = []
        while self.peek().type != 'RBRACE':
            stmts.append(self.parse_statement())
        self.consume('RBRACE')
        return stmts

    def parse_statement(self):
        tok = self.peek()

        if tok.type == 'IF':
            self.consume('IF')
            self.consume('LPAREN')
            cond = self.parse_expression()
            self.consume('RPAREN')
            then_body = self.parse_block()
            else_body = None
            if self.peek().type == 'ELSE':
                self.consume('ELSE')
                if self.peek().type == 'IF':
                    else_body = [self.parse_statement()]
                else:
                    else_body = self.parse_block()
            return IfStmt(cond, then_body, else_body)

        if tok.type == 'WHILE':
            self.consume('WHILE')
            self.consume('LPAREN')
            cond = self.parse_expression()
            self.consume('RPAREN')
            body = self.parse_block()
            return WhileStmt(cond, body)

        if tok.type == 'FOR':
            self.consume('FOR')
            self.consume('LPAREN')

            init = None
            if self.peek().type != 'SEMICOLON':
                if self._is_var_decl():
                    t_name = self.parse_type_name()
                    v_name = self.consume('IDENTIFIER').value
                    init_val = None
                    if self.match('ASSIGN'):
                        init_val = self.parse_expression()
                    init = VarDecl(t_name, v_name, init_val)
                else:
                    expr = self.parse_expression()
                    if self.match('ASSIGN'):
                        val = self.parse_expression()
                        init = Assignment(expr, val)
                    else:
                        init = ExprStmt(expr)
            self.consume('SEMICOLON')

            cond = None
            if self.peek().type != 'SEMICOLON':
                cond = self.parse_expression()
            self.consume('SEMICOLON')

            step = None
            if self.peek().type != 'RPAREN':
                expr = self.parse_expression()
                if self.match('ASSIGN'):
                    val = self.parse_expression()
                    step = Assignment(expr, val)
                else:
                    step = ExprStmt(expr)
            self.consume('RPAREN')

            body = self.parse_block()
            return ForStmt(init, cond, step, body)

        if tok.type == 'BREAK':
            self.consume('BREAK')
            self.consume('SEMICOLON')
            return BreakStmt()

        if tok.type == 'CONTINUE':
            self.consume('CONTINUE')
            self.consume('SEMICOLON')
            return ContinueStmt()

        if tok.type == 'RETURN':
            self.consume('RETURN')
            val = None
            if self.peek().type != 'SEMICOLON':
                val = self.parse_expression()
            self.consume('SEMICOLON')
            return ReturnStmt(val)

        if tok.type == 'TRY':
            self.consume('TRY')
            try_body = self.parse_block()
            self.consume('CATCH')
            self.consume('LPAREN')
            param_type = self.parse_type_name()
            param_name = self.consume('IDENTIFIER').value
            self.consume('RPAREN')
            catch_body = self.parse_block()
            return TryCatchStmt(try_body, param_type, param_name, catch_body)

        if tok.type == 'THROW':
            self.consume('THROW')
            expr = self.parse_expression()
            self.consume('SEMICOLON')
            return ThrowStmt(expr)

        if tok.type == 'PRINT':
            self.consume('PRINT')
            self.consume('LPAREN')
            val = self.parse_expression()
            self.consume('RPAREN')
            self.consume('SEMICOLON')
            return PrintStmt(val)

        if self._is_var_decl():
            type_name = self.parse_type_name()
            var_name = self.consume('IDENTIFIER').value
            init_val = None
            if self.match('ASSIGN'):
                init_val = self.parse_expression()
            self.consume('SEMICOLON')
            return VarDecl(type_name, var_name, init_val)

        expr = self.parse_expression()
        if self.match('ASSIGN'):
            val = self.parse_expression()
            self.consume('SEMICOLON')
            return Assignment(expr, val)

        self.consume('SEMICOLON')
        return ExprStmt(expr)

    def _is_var_decl(self) -> bool:
        tok = self.peek()
        if tok.type in ('INT_TYPE', 'STRING_TYPE', 'VOID_TYPE'):
            return True
        if tok.type == 'IDENTIFIER':
            next_tok = self.tokens[self.pos + 1]
            if next_tok.type == 'IDENTIFIER':
                return True
            if (next_tok.type == 'LBRACKET' and
                    self.pos + 2 < len(self.tokens) and
                    self.tokens[self.pos + 2].type == 'RBRACKET'):
                return True
            if next_tok.type == 'LPAREN':
                # Check for ClassName(params) var_name;
                i = self.pos + 2
                depth = 1
                while i < len(self.tokens) and depth > 0:
                    if self.tokens[i].type == 'LPAREN':
                        depth += 1
                    elif self.tokens[i].type == 'RPAREN':
                        depth -= 1
                    i += 1
                if depth == 0 and i < len(self.tokens) and self.tokens[i].type == 'IDENTIFIER':
                    return True
        return False

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.peek().type == 'OR':
            op = self.consume().value
            right = self.parse_and()
            left = BinaryExpr(op, left, right)
        return left

    def parse_and(self):
        left = self.parse_equality()
        while self.peek().type == 'AND':
            op = self.consume().value
            right = self.parse_equality()
            left = BinaryExpr(op, left, right)
        return left

    def parse_equality(self):
        left = self.parse_comparison()
        while self.peek().type in ('EQ', 'NEQ'):
            op = self.consume().value
            right = self.parse_comparison()
            left = BinaryExpr(op, left, right)
        return left

    def parse_comparison(self):
        left = self.parse_additive()
        while self.peek().type in ('LT', 'GT', 'LTE', 'GTE'):
            op = self.consume().value
            right = self.parse_additive()
            left = BinaryExpr(op, left, right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.peek().type in ('PLUS', 'MINUS'):
            op = self.consume().value
            right = self.parse_multiplicative()
            left = BinaryExpr(op, left, right)
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.peek().type in ('TIMES', 'DIV'):
            op = self.consume().value
            right = self.parse_unary()
            left = BinaryExpr(op, left, right)
        return left

    def parse_unary(self):
        if self.peek().type in ('NOT', 'MINUS'):
            op = self.consume().value
            operand = self.parse_unary()
            return UnaryExpr(op, operand)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()

        if tok.type == 'NUMBER':
            self.consume()
            return Number(int(tok.value))

        if tok.type == 'STRING':
            self.consume()
            return StringLiteral(tok.value)

        if tok.type == 'TRUE':
            self.consume()
            return BoolLiteral(True)

        if tok.type == 'FALSE':
            self.consume()
            return BoolLiteral(False)

        if tok.type == 'NULL':
            self.consume()
            return NullLiteral()

        if tok.type == 'LPAREN':
            # Lookahead to disambiguate (params) => ... from grouped expression (expr)
            depth = 1
            i = self.pos + 1
            while i < len(self.tokens) and depth > 0:
                if self.tokens[i].type == 'LPAREN':
                    depth += 1
                elif self.tokens[i].type == 'RPAREN':
                    depth -= 1
                i += 1
            if depth == 0 and i < len(self.tokens) and self.tokens[i].type == 'ARROW':
                self.consume('LPAREN')
                params = []
                if self.peek().type != 'RPAREN':
                    while True:
                        p_type = self.parse_type_name()
                        p_name = self.consume('IDENTIFIER').value
                        params.append((p_type, p_name))
                        if not self.match('COMMA'):
                            break
                self.consume('RPAREN')
                self.consume('ARROW')
                if self.peek().type == 'LBRACE':
                    body = self.parse_block()
                else:
                    body = self.parse_expression()
                return self._parse_postfix(LambdaExpr(params=params, body=body))

            self.consume('LPAREN')
            expr = self.parse_expression()
            self.consume('RPAREN')
            return self._parse_postfix(expr)

        if tok.type == 'NEW':
            self.consume('NEW')
            next_tok = self.peek()
            if next_tok.type in ('IDENTIFIER', 'INT_TYPE', 'STRING_TYPE'):
                type_name = self.consume().value
            else:
                raise SyntaxError(
                    f"Line {next_tok.line}: Expected type name after 'new', "
                    f"got {next_tok.type} ({next_tok.value!r})"
                )

            if self.peek().type == 'LBRACKET':
                self.consume('LBRACKET')
                size = self.parse_expression()
                self.consume('RBRACKET')
                return self._parse_postfix(NewArrayExpr(type_name, size))

            self.consume('LPAREN')
            args = []
            if self.peek().type != 'RPAREN':
                while True:
                    args.append(self.parse_expression())
                    if not self.match('COMMA'):
                        break
            self.consume('RPAREN')
            return self._parse_postfix(NewExpr(type_name, args))

        if tok.type in ('IDENTIFIER', 'THIS'):
            name = self.consume().value
            if name != 'this' and self.peek().type == 'LPAREN':
                self.consume('LPAREN')
                args = []
                if self.peek().type != 'RPAREN':
                    while True:
                        args.append(self.parse_expression())
                        if not self.match('COMMA'):
                            break
                self.consume('RPAREN')
                return self._parse_postfix(FuncCall(name, args))

            node = Variable(name)
            return self._parse_postfix(node)

        raise SyntaxError(f"Line {tok.line}: Unexpected token {tok.type} ({tok.value!r})")

    def _parse_postfix(self, node):
        while self.peek().type in ('DOT', 'LBRACKET'):
            if self.peek().type == 'DOT':
                self.consume('DOT')
                member = self.consume('IDENTIFIER').value
                if self.peek().type == 'LPAREN':
                    self.consume('LPAREN')
                    args = []
                    if self.peek().type != 'RPAREN':
                        while True:
                            args.append(self.parse_expression())
                            if not self.match('COMMA'):
                                break
                    self.consume('RPAREN')
                    node = MethodCall(node, member, args)
                else:
                    node = MemberAccess(node, member)
            elif self.peek().type == 'LBRACKET':
                self.consume('LBRACKET')
                index = self.parse_expression()
                self.consume('RBRACKET')
                node = IndexAccess(node, index)
        return node
