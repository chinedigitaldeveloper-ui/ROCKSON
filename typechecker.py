from parser import (
    Program, ClassDecl, FuncDecl, ConstructorDecl, VarDecl, Assignment,
    IfStmt, WhileStmt, ForStmt, BreakStmt, ContinueStmt, ReturnStmt, PrintStmt, ExprStmt,
    TryCatchStmt, ThrowStmt,
    BinaryExpr, UnaryExpr, MemberAccess, MethodCall, FuncCall, LambdaExpr,
    NewExpr, NewArrayExpr, IndexAccess,
    Variable, Number, StringLiteral, BoolLiteral, NullLiteral
)

class TypeError(Exception):
    pass

class TypeChecker:
    def __init__(self, ast: Program):
        self.ast = ast
        self.classes = {}
        self.functions = {}
        self.current_scope = {}
        self.outer_scopes = []
        self.current_return_type = 'void'
        self.loop_depth = 0

    @staticmethod
    def is_function_type(t: str) -> bool:
        return '(' in t and t.endswith(')')

    @staticmethod
    def parse_function_type(t: str):
        idx = t.index('(')
        ret_t = t[:idx]
        params_str = t[idx + 1:-1]
        if not params_str:
            return ret_t, []
        params = []
        curr = []
        depth = 0
        for ch in params_str:
            if ch == '(':
                depth += 1
                curr.append(ch)
            elif ch == ')':
                depth -= 1
                curr.append(ch)
            elif ch == ',' and depth == 0:
                params.append("".join(curr).strip())
                curr = []
            else:
                curr.append(ch)
        if curr:
            params.append("".join(curr).strip())
        return ret_t, params

    def check(self):
        builtins = [
            FuncDecl('void', 'gc_collect', [], []),
            FuncDecl('int', 'gc_heap_size', [], []),
            FuncDecl('int', 'gc_free_bytes', [], []),
            FuncDecl('string', 'read_file', [('string', 'path')], []),
            FuncDecl('int', 'write_file', [('string', 'path'), ('string', 'content')], []),
            FuncDecl('int', 'file_exists', [('string', 'path')], []),
            FuncDecl('int', 'remove_file', [('string', 'path')], []),
            FuncDecl('int', 'str_len', [('string', 's')], []),
            FuncDecl('string', 'str_sub', [('string', 's'), ('int', 'start'), ('int', 'len')], []),
            FuncDecl('int', 'str_to_int', [('string', 's')], []),
        ]
        for b in builtins:
            self.functions[b.name] = b

        for decl in self.ast.declarations:
            if isinstance(decl, ClassDecl):
                if decl.name in self.classes:
                    raise TypeError(f"Redefinition of class '{decl.name}'")
                self.classes[decl.name] = decl
            elif isinstance(decl, FuncDecl):
                if decl.name in self.functions:
                    raise TypeError(f"Redefinition of function '{decl.name}'")
                self.functions[decl.name] = decl

        if 'main' not in self.functions:
            raise TypeError("Undefined reference to entry point 'main()'")

        main_func = self.functions['main']
        if main_func.return_type != 'int':
            raise TypeError("Entry point 'main' must return 'int'")
        if len(main_func.params) > 1 or (len(main_func.params) == 1 and main_func.params[0][0] != 'string[]'):
            raise TypeError("Entry point 'main' must have signature 'int main()' or 'int main(string[] args)'")

        self.check_inheritance()

        for cls in self.classes.values():
            self.check_class(cls)

        for func in self.functions.values():
            if func.body:
                self.check_function(func)

    def check_inheritance(self):
        for name, cls in self.classes.items():
            visited = set()
            curr = cls
            while curr and curr.parent:
                if curr.parent in visited or curr.parent == name:
                    raise TypeError(f"Circular inheritance detected involving class '{name}'")
                if curr.parent not in self.classes:
                    raise TypeError(f"Class '{curr.name}' extends undefined class '{curr.parent}'")
                visited.add(curr.parent)
                curr = self.classes[curr.parent]

    def find_ancestor_method(self, parent_name: str, method_name: str):
        curr = self.classes.get(parent_name)
        while curr:
            for m in curr.methods:
                if m.name == method_name:
                    return m
            curr = self.classes.get(curr.parent) if curr.parent else None
        return None

    def is_subtype(self, sub: str, base: str) -> bool:
        if sub == base:
            return True
        cls = self.classes.get(sub)
        while cls and cls.parent:
            if cls.parent == base:
                return True
            cls = self.classes.get(cls.parent)
        return False

    def is_assignable(self, target_type: str, val_type: str) -> bool:
        if target_type == val_type:
            return True
        if val_type == 'null':
            return (target_type in self.classes or
                    target_type.endswith('[]') or
                    self.is_function_type(target_type))
        if self.is_function_type(target_type) and self.is_function_type(val_type):
            t_ret, t_params = self.parse_function_type(target_type)
            v_ret, v_params = self.parse_function_type(val_type)
            if len(t_params) != len(v_params):
                return False
            if not self.is_assignable(t_ret, v_ret):
                return False
            for tp, vp in zip(t_params, v_params):
                if not self.is_assignable(tp, vp):
                    return False
            return True
        if target_type in self.classes and val_type in self.classes:
            return self.is_subtype(val_type, target_type)
        return False

    def is_valid_type(self, type_name: str) -> bool:
        if self.is_function_type(type_name):
            ret_t, params = self.parse_function_type(type_name)
            if not self.is_valid_type(ret_t):
                return False
            for p in params:
                if not self.is_valid_type(p):
                    return False
            return True
        if type_name.endswith('[]'):
            return self.is_valid_type(type_name[:-2])
        return type_name in ('int', 'string', 'void') or type_name in self.classes

    def check_class(self, cls: ClassDecl):
        if cls.parent:
            for method in cls.methods:
                ancestor_m = self.find_ancestor_method(cls.parent, method.name)
                if ancestor_m:
                    if method.return_type != ancestor_m.return_type:
                        raise TypeError(
                            f"Method '{method.name}' in class '{cls.name}' overrides parent method "
                            f"with incompatible return type (expected '{ancestor_m.return_type}', got '{method.return_type}')"
                        )
                    if len(method.params) != len(ancestor_m.params):
                        raise TypeError(
                            f"Method '{method.name}' in class '{cls.name}' overrides parent method "
                            f"with different parameter count (expected {len(ancestor_m.params)}, got {len(method.params)})"
                        )
                    for (p_t, _), (exp_t, _) in zip(method.params, ancestor_m.params):
                        if p_t != exp_t:
                            raise TypeError(
                                f"Method '{method.name}' in class '{cls.name}' overrides parent method "
                                f"with incompatible parameter type (expected '{exp_t}', got '{p_t}')"
                            )

        for ctor in cls.constructors:
            old_scope = self.current_scope.copy()
            old_ret = self.current_return_type
            self.current_scope = {"this": cls.name}
            self.current_return_type = 'void'
            for p_type, p_name in ctor.params:
                if not self.is_valid_type(p_type):
                    raise TypeError(f"Unknown parameter type '{p_type}' in constructor of '{cls.name}'")
                self.current_scope[p_name] = p_type
            for stmt in ctor.body:
                self.check_statement(stmt)
            self.current_scope = old_scope
            self.current_return_type = old_ret

        for method in cls.methods:
            old_scope = self.current_scope.copy()
            old_ret = self.current_return_type
            self.current_scope = {"this": cls.name}
            self.current_return_type = method.return_type
            for p_type, p_name in method.params:
                if not self.is_valid_type(p_type):
                    raise TypeError(f"Unknown parameter type '{p_type}' in method '{method.name}'")
                self.current_scope[p_name] = p_type
            for stmt in method.body:
                self.check_statement(stmt)
            self.current_scope = old_scope
            self.current_return_type = old_ret

    def check_function(self, func: FuncDecl):
        old_scope = self.current_scope.copy()
        old_ret = self.current_return_type
        self.current_scope = {}
        self.current_return_type = func.return_type
        for p_type, p_name in func.params:
            if not self.is_valid_type(p_type):
                raise TypeError(f"Unknown parameter type '{p_type}' in function '{func.name}'")
            self.current_scope[p_name] = p_type

        for stmt in func.body:
            self.check_statement(stmt)
        self.current_scope = old_scope
        self.current_return_type = old_ret

    def check_statement(self, stmt):
        if isinstance(stmt, VarDecl):
            if not self.is_valid_type(stmt.type_name):
                raise TypeError(f"Unknown type '{stmt.type_name}' for variable '{stmt.name}'")

            if stmt.init_expr:
                expr_type = self.check_expression(stmt.init_expr)
                if not self.is_assignable(stmt.type_name, expr_type):
                    raise TypeError(
                        f"Type mismatch on '{stmt.name}': cannot assign '{expr_type}' to variable of type '{stmt.type_name}'"
                    )
            self.current_scope[stmt.name] = stmt.type_name

        elif isinstance(stmt, Assignment):
            target_type = self.check_expression(stmt.target)
            val_type = self.check_expression(stmt.value)
            if not self.is_assignable(target_type, val_type):
                raise TypeError(f"Cannot assign expression of type '{val_type}' to target of type '{target_type}'")

        elif isinstance(stmt, IfStmt):
            cond_type = self.check_expression(stmt.condition)
            if cond_type != 'int':
                raise TypeError(f"If condition must evaluate to 'int' (boolean), got '{cond_type}'")
            for s in stmt.then_body:
                self.check_statement(s)
            if stmt.else_body:
                for s in stmt.else_body:
                    self.check_statement(s)

        elif isinstance(stmt, WhileStmt):
            cond_type = self.check_expression(stmt.condition)
            if cond_type != 'int':
                raise TypeError(f"While condition must evaluate to 'int' (boolean), got '{cond_type}'")
            self.loop_depth += 1
            for s in stmt.body:
                self.check_statement(s)
            self.loop_depth -= 1

        elif isinstance(stmt, ForStmt):
            old_scope = self.current_scope.copy()
            if stmt.init:
                self.check_statement(stmt.init)
            if stmt.condition:
                cond_type = self.check_expression(stmt.condition)
                if cond_type != 'int':
                    raise TypeError(f"For condition must evaluate to 'int' (boolean), got '{cond_type}'")
            if stmt.step:
                self.check_statement(stmt.step)
            self.loop_depth += 1
            for s in stmt.body:
                self.check_statement(s)
            self.loop_depth -= 1
            self.current_scope = old_scope

        elif isinstance(stmt, BreakStmt):
            if self.loop_depth == 0:
                raise TypeError("Cannot use 'break' outside of a loop")

        elif isinstance(stmt, ContinueStmt):
            if self.loop_depth == 0:
                raise TypeError("Cannot use 'continue' outside of a loop")

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                val_t = self.check_expression(stmt.value)
                if self.current_return_type is None:
                    self.current_return_type = val_t
                elif not self.is_assignable(self.current_return_type, val_t):
                    raise TypeError(
                        f"Cannot return expression of type '{val_t}' from function expecting '{self.current_return_type}'"
                    )
            else:
                if self.current_return_type is None:
                    self.current_return_type = 'void'
                elif self.current_return_type != 'void':
                    raise TypeError(f"Empty return statement in function expecting '{self.current_return_type}'")

        elif isinstance(stmt, PrintStmt):
            t = self.check_expression(stmt.expr)
            if t not in ('int', 'string'):
                raise TypeError(f"'print()' only supports 'int' or 'string', got '{t}'")

        elif isinstance(stmt, ThrowStmt):
            t = self.check_expression(stmt.expr)
            if t != 'string':
                raise TypeError(f"Can only throw 'string' exception, got '{t}'")

        elif isinstance(stmt, TryCatchStmt):
            if not self.is_valid_type(stmt.catch_param_type):
                raise TypeError(f"Unknown catch parameter type '{stmt.catch_param_type}'")
            if stmt.catch_param_type != 'string':
                raise TypeError(f"Catch parameter type must be 'string', got '{stmt.catch_param_type}'")
            for s in stmt.try_body:
                self.check_statement(s)
            old_scope = self.current_scope.copy()
            self.current_scope[stmt.catch_param_name] = stmt.catch_param_type
            for s in stmt.catch_body:
                self.check_statement(s)
            self.current_scope = old_scope

        elif isinstance(stmt, ExprStmt):
            self.check_expression(stmt.expr)

    def check_expression(self, expr) -> str:
        if isinstance(expr, Number):
            return 'int'

        if isinstance(expr, StringLiteral):
            return 'string'

        if isinstance(expr, BoolLiteral):
            return 'int'

        if isinstance(expr, NullLiteral):
            return 'null'

        if isinstance(expr, Variable):
            if expr.name in self.current_scope:
                return self.current_scope[expr.name]
            if any(expr.name in s for s in self.outer_scopes):
                raise TypeError(f"Cannot capture outer variable '{expr.name}' in non-capturing lambda")
            # Reference to top-level function as first-class value
            if expr.name in self.functions:
                func = self.functions[expr.name]
                param_types = [pt for pt, _ in func.params]
                return f"{func.return_type}({','.join(param_types)})"
            raise TypeError(f"Undeclared variable '{expr.name}'")

        if isinstance(expr, UnaryExpr):
            if expr.op == '!':
                op_type = self.check_expression(expr.operand)
                if op_type != 'int':
                    raise TypeError(f"Unary '!' operator expects 'int' operand, got '{op_type}'")
                return 'int'
            if expr.op == '-':
                op_type = self.check_expression(expr.operand)
                if op_type != 'int':
                    raise TypeError(f"Unary '-' operator expects 'int' operand, got '{op_type}'")
                return 'int'
            raise TypeError(f"Unsupported unary operator '{expr.op}'")

        if isinstance(expr, BinaryExpr):
            lt = self.check_expression(expr.left)
            rt = self.check_expression(expr.right)

            if expr.op == '+':
                if lt == 'string' and rt in ('string', 'int'):
                    return 'string'
                if lt == 'int' and rt == 'string':
                    return 'string'
                if lt == 'int' and rt == 'int':
                    return 'int'
                raise TypeError(f"Operator '+' cannot concatenate '{lt}' and '{rt}'")

            if expr.op in ('-', '*', '/'):
                if lt != 'int' or rt != 'int':
                    raise TypeError(f"Arithmetic operator '{expr.op}' requires 'int' operands, got '{lt}' and '{rt}'")
                return 'int'

            if expr.op in ('&&', '||'):
                if lt != 'int' or rt != 'int':
                    raise TypeError(f"Logical operator '{expr.op}' requires 'int' operands, got '{lt}' and '{rt}'")
                return 'int'

            if expr.op in ('==', '!='):
                if not (self.is_assignable(lt, rt) or self.is_assignable(rt, lt)):
                    raise TypeError(f"Cannot compare incomparable types '{lt}' and '{rt}' with '{expr.op}'")
                return 'int'

            if expr.op in ('<', '>', '<=', '>='):
                if lt != 'int' or rt != 'int':
                    raise TypeError(f"Comparison operator '{expr.op}' requires 'int' operands, got '{lt}' and '{rt}'")
                return 'int'

        if isinstance(expr, FuncCall):
            ret_type = None
            param_types = None

            # 1. Call via local variable or parameter of function type
            if expr.name in self.current_scope:
                var_type = self.current_scope[expr.name]
                if self.is_function_type(var_type):
                    ret_type, param_types = self.parse_function_type(var_type)
                else:
                    raise TypeError(f"Cannot call variable '{expr.name}' of non-function type '{var_type}'")
            elif any(expr.name in s for s in self.outer_scopes):
                raise TypeError(f"Cannot capture outer variable '{expr.name}' in non-capturing lambda")
            # 2. Call to declared or built-in function
            elif expr.name in self.functions:
                func = self.functions[expr.name]
                ret_type = func.return_type
                param_types = [pt for pt, _ in func.params]
            else:
                raise TypeError(f"Undefined function or variable '{expr.name}'")

            if len(param_types) != len(expr.args):
                raise TypeError(f"Function '{expr.name}' expects {len(param_types)} arguments, got {len(expr.args)}")

            for p_type, arg in zip(param_types, expr.args):
                arg_type = self.check_expression(arg)
                if not self.is_assignable(p_type, arg_type):
                    raise TypeError(f"Function '{expr.name}' expected argument '{p_type}', got '{arg_type}'")

            return ret_type

        if isinstance(expr, NewExpr):
            if expr.class_name not in self.classes:
                raise TypeError(f"Cannot instantiate undefined class '{expr.class_name}'")
            cls = self.classes[expr.class_name]
            if cls.constructors:
                ctor = cls.constructors[0]
                if len(ctor.params) != len(expr.args):
                    raise TypeError(
                        f"Constructor for '{expr.class_name}' expects {len(ctor.params)} arguments, got {len(expr.args)}"
                    )
                for (p_type, _), arg in zip(ctor.params, expr.args):
                    arg_type = self.check_expression(arg)
                    if not self.is_assignable(p_type, arg_type):
                        raise TypeError(f"Constructor expected argument '{p_type}', got '{arg_type}'")
            elif expr.args:
                raise TypeError(f"Class '{expr.class_name}' defines no constructor taking arguments")
            return expr.class_name

        if isinstance(expr, NewArrayExpr):
            if not self.is_valid_type(expr.element_type):
                raise TypeError(f"Unknown element type '{expr.element_type}' in array allocation")
            size_type = self.check_expression(expr.size)
            if size_type != 'int':
                raise TypeError(f"Array size must evaluate to 'int', got '{size_type}'")
            return f"{expr.element_type}[]"

        if isinstance(expr, IndexAccess):
            obj_type = self.check_expression(expr.obj)
            if not obj_type.endswith('[]'):
                raise TypeError(f"Cannot index non-array type '{obj_type}'")
            idx_type = self.check_expression(expr.index)
            if idx_type != 'int':
                raise TypeError(f"Array index must evaluate to 'int', got '{idx_type}'")
            return obj_type[:-2]

        if isinstance(expr, MemberAccess):
            obj_type = self.check_expression(expr.obj)

            if obj_type.endswith('[]'):
                if expr.member == 'length':
                    return 'int'
                raise TypeError(f"Arrays have no property '{expr.member}' (only '.length' is supported)")

            if obj_type not in self.classes:
                raise TypeError(f"Member access '{expr.member}' on non-class type '{obj_type}'")

            cls = self.classes[obj_type]
            while cls:
                for f in cls.fields:
                    if f.name == expr.member:
                        return f.type_name
                cls = self.classes.get(cls.parent) if cls.parent else None

            raise TypeError(f"Class '{obj_type}' and its ancestors have no field '{expr.member}'")

        if isinstance(expr, MethodCall):
            obj_type = self.check_expression(expr.obj)
            if obj_type not in self.classes:
                raise TypeError(f"Method call '{expr.method}' on non-class type '{obj_type}'")

            # Check regular methods
            cls = self.classes[obj_type]
            target_method = None
            while cls:
                for m in cls.methods:
                    if m.name == expr.method:
                        target_method = m
                        break
                if target_method:
                    break
                cls = self.classes.get(cls.parent) if cls.parent else None

            if target_method:
                if len(target_method.params) != len(expr.args):
                    raise TypeError(
                        f"Method '{target_method.name}' expects {len(target_method.params)} arguments, got {len(expr.args)}"
                    )
                for (p_type, _), arg in zip(target_method.params, expr.args):
                    arg_type = self.check_expression(arg)
                    if not self.is_assignable(p_type, arg_type):
                        raise TypeError(f"Method '{target_method.name}' expected arg of type '{p_type}', got '{arg_type}'")
                return target_method.return_type

            # Check if calling a function pointer field
            cls = self.classes[obj_type]
            target_field = None
            while cls:
                for f in cls.fields:
                    if f.name == expr.method:
                        target_field = f
                        break
                if target_field:
                    break
                cls = self.classes.get(cls.parent) if cls.parent else None

            if target_field and self.is_function_type(target_field.type_name):
                ret_t, param_types = self.parse_function_type(target_field.type_name)
                if len(param_types) != len(expr.args):
                    raise TypeError(
                        f"Field '{target_field.name}' expects {len(param_types)} arguments, got {len(expr.args)}"
                    )
                for p_type, arg in zip(param_types, expr.args):
                    arg_type = self.check_expression(arg)
                    if not self.is_assignable(p_type, arg_type):
                        raise TypeError(f"Field '{target_field.name}' expected arg of type '{p_type}', got '{arg_type}'")
                return ret_t

            raise TypeError(f"Class '{obj_type}' and its ancestors have no method '{expr.method}'")

        if isinstance(expr, LambdaExpr):
            for pt, _ in expr.params:
                if not self.is_valid_type(pt):
                    raise TypeError(f"Unknown parameter type '{pt}' in lambda")

            self.outer_scopes.append(dict(self.current_scope))
            old_scope = self.current_scope
            self.current_scope = {pn: pt for pt, pn in expr.params}

            if isinstance(expr.body, list):
                old_ret = self.current_return_type
                self.current_return_type = None
                for s in expr.body:
                    self.check_statement(s)
                ret_t = self.current_return_type if self.current_return_type is not None else 'void'
                self.current_return_type = old_ret
            else:
                ret_t = self.check_expression(expr.body)

            self.current_scope = old_scope
            self.outer_scopes.pop()

            expr._return_type = ret_t
            param_types = [pt for pt, _ in expr.params]
            return f"{ret_t}({','.join(param_types)})"

        raise TypeError(f"Unknown expression node: {expr}")
