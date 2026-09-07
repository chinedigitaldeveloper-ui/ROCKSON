from parser import (
    Program, ClassDecl, FuncDecl, FieldDecl, MethodDecl, ConstructorDecl,
    VarDecl, Assignment, IfStmt, WhileStmt, ForStmt, BreakStmt, ContinueStmt,
    ReturnStmt, PrintStmt, ExprStmt,
    TryCatchStmt, ThrowStmt,
    BinaryExpr, UnaryExpr, MemberAccess, MethodCall, FuncCall, LambdaExpr,
    NewExpr, NewArrayExpr, IndexAccess,
    Variable, Number, StringLiteral, BoolLiteral, NullLiteral
)

class CodeGenerator:
    def __init__(self, ast: Program):
        self.ast = ast
        self.lines = []
        self.indent_level = 0
        self.classes = {decl.name: decl for decl in ast.declarations if isinstance(decl, ClassDecl)}
        self.scope = {}
        self.lifted_lambdas = []
        self.try_frame_counter = 0
        self.active_try_frames = []
        self.loop_try_frames = []
        self.current_func_ret_type = 'void'

    def indent(self) -> str:
        return "    " * self.indent_level

    def emit(self, text: str):
        self.lines.append(f"{self.indent()}{text}")

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

    def fn_typedef_name(self, t: str) -> str:
        ret_t, params = self.parse_function_type(t)
        parts = [ret_t.replace('[]', '_arr')]
        if not params:
            parts.append("void")
        else:
            for p in params:
                parts.append(p.replace('[]', '_arr'))
        return "Fn_" + "_".join(parts)

    def c_type(self, type_name: str) -> str:
        if self.is_function_type(type_name):
            return self.fn_typedef_name(type_name)
        if type_name == 'null':
            return 'void*'
        if type_name.endswith('[]'):
            elem = type_name[:-2]
            return f"Array_{elem}*"
        if type_name == 'string':
            return 'const char*'
        if type_name in self.classes:
            return f"{type_name}*"
        return type_name

    def c_elem_type(self, elem_type: str) -> str:
        if self.is_function_type(elem_type):
            return self.fn_typedef_name(elem_type)
        if elem_type == 'string':
            return 'const char*'
        if elem_type in self.classes:
            return f'{elem_type}*'
        return elem_type

    def infer_type(self, expr) -> str:
        if isinstance(expr, Number):
            return 'int'
        if isinstance(expr, StringLiteral):
            return 'string'
        if isinstance(expr, BoolLiteral):
            return 'int'
        if isinstance(expr, NullLiteral):
            return 'null'

        if isinstance(expr, Variable):
            if expr.name in self.scope:
                return self.scope[expr.name]
            for decl in self.ast.declarations:
                if isinstance(decl, FuncDecl) and decl.name == expr.name:
                    param_types = [pt for pt, _ in decl.params]
                    return f"{decl.return_type}({','.join(param_types)})"
            return 'int'

        if isinstance(expr, UnaryExpr):
            return 'int'

        if isinstance(expr, BinaryExpr):
            if expr.op == '+':
                lt = self.infer_type(expr.left)
                rt = self.infer_type(expr.right)
                if lt == 'string' or rt == 'string':
                    return 'string'
            return 'int'

        if isinstance(expr, FuncCall):
            if expr.name in self.scope and self.is_function_type(self.scope[expr.name]):
                ret_t, _ = self.parse_function_type(self.scope[expr.name])
                return ret_t
            if expr.name in ('gc_heap_size', 'gc_free_bytes', 'write_file', 'file_exists', 'remove_file', 'str_len', 'str_to_int'):
                return 'int'
            if expr.name in ('read_file', 'str_sub'):
                return 'string'
            if expr.name == 'gc_collect':
                return 'void'
            for decl in self.ast.declarations:
                if isinstance(decl, FuncDecl) and decl.name == expr.name:
                    return decl.return_type
            return 'int'

        if isinstance(expr, NewExpr):
            return expr.class_name

        if isinstance(expr, NewArrayExpr):
            return f"{expr.element_type}[]"

        if isinstance(expr, IndexAccess):
            obj_type = self.infer_type(expr.obj)
            if obj_type.endswith('[]'):
                return obj_type[:-2]
            return 'int'

        if isinstance(expr, MemberAccess):
            obj_type = self.infer_type(expr.obj)
            if obj_type.endswith('[]'):
                if expr.member == 'length':
                    return 'int'
                return 'int'
            cls = self.classes.get(obj_type)
            while cls:
                for f in cls.fields:
                    if f.name == expr.member:
                        return f.type_name
                cls = self.classes.get(cls.parent) if cls.parent else None
            return 'int'

        if isinstance(expr, MethodCall):
            obj_type = self.infer_type(expr.obj)
            cls = self.classes.get(obj_type)
            while cls:
                for m in cls.methods:
                    if m.name == expr.method:
                        return m.return_type
                for f in cls.fields:
                    if f.name == expr.method and self.is_function_type(f.type_name):
                        ret_t, _ = self.parse_function_type(f.type_name)
                        return ret_t
                cls = self.classes.get(cls.parent) if cls.parent else None
            return 'int'

        if isinstance(expr, LambdaExpr):
            ret_t, params = self.get_lambda_signature(expr)
            return f"{ret_t}({','.join(params)})"

        return 'int'

    def get_lambda_signature(self, expr: LambdaExpr):
        param_types = [pt for pt, _ in expr.params]
        if hasattr(expr, '_return_type'):
            return expr._return_type, param_types

        old_scope = self.scope.copy()
        for pt, pn in expr.params:
            self.scope[pn] = pt

        def find_ret(stmts):
            for s in stmts:
                if isinstance(s, VarDecl):
                    self.scope[s.name] = s.type_name
                elif isinstance(s, ReturnStmt) and s.value:
                    return self.infer_type(s.value)
                elif isinstance(s, IfStmt):
                    r = find_ret(s.then_body)
                    if r:
                        return r
                    if s.else_body:
                        r = find_ret(s.else_body)
                        if r:
                            return r
                elif isinstance(s, WhileStmt):
                    r = find_ret(s.body)
                    if r:
                        return r
                elif isinstance(s, ForStmt):
                    if s.init and isinstance(s.init, VarDecl):
                        self.scope[s.init.name] = s.init.type_name
                    r = find_ret(s.body)
                    if r:
                        return r
                elif isinstance(s, TryCatchStmt):
                    r = find_ret(s.try_body)
                    if r:
                        return r
                    r = find_ret(s.catch_body)
                    if r:
                        return r
            return None

        if isinstance(expr.body, list):
            ret_t = find_ret(expr.body) or 'void'
        else:
            ret_t = self.infer_type(expr.body)
        self.scope = old_scope
        return ret_t, param_types

    def lift_lambdas(self):
        self.lifted_lambdas = []

        def visit_expr(expr):
            if expr is None:
                return
            if isinstance(expr, LambdaExpr):
                if isinstance(expr.body, list):
                    for s in expr.body:
                        visit_stmt(s)
                else:
                    visit_expr(expr.body)
                expr._lambda_id = len(self.lifted_lambdas)
                self.lifted_lambdas.append(expr)
            elif isinstance(expr, BinaryExpr):
                visit_expr(expr.left)
                visit_expr(expr.right)
            elif isinstance(expr, UnaryExpr):
                visit_expr(expr.operand)
            elif isinstance(expr, MemberAccess):
                visit_expr(expr.obj)
            elif isinstance(expr, MethodCall):
                visit_expr(expr.obj)
                for a in expr.args:
                    visit_expr(a)
            elif isinstance(expr, FuncCall):
                for a in expr.args:
                    visit_expr(a)
            elif isinstance(expr, NewExpr):
                for a in expr.args:
                    visit_expr(a)
            elif isinstance(expr, NewArrayExpr):
                visit_expr(expr.size)
            elif isinstance(expr, IndexAccess):
                visit_expr(expr.obj)
                visit_expr(expr.index)

        def visit_stmt(stmt):
            if stmt is None:
                return
            if isinstance(stmt, VarDecl):
                visit_expr(stmt.init_expr)
            elif isinstance(stmt, Assignment):
                visit_expr(stmt.target)
                visit_expr(stmt.value)
            elif isinstance(stmt, IfStmt):
                visit_expr(stmt.condition)
                for s in stmt.then_body:
                    visit_stmt(s)
                if stmt.else_body:
                    for s in stmt.else_body:
                        visit_stmt(s)
            elif isinstance(stmt, WhileStmt):
                visit_expr(stmt.condition)
                for s in stmt.body:
                    visit_stmt(s)
            elif isinstance(stmt, ForStmt):
                if stmt.init:
                    visit_stmt(stmt.init)
                if stmt.condition:
                    visit_expr(stmt.condition)
                if stmt.step:
                    visit_stmt(stmt.step)
                for s in stmt.body:
                    visit_stmt(s)
            elif isinstance(stmt, ReturnStmt):
                visit_expr(stmt.value)
            elif isinstance(stmt, ThrowStmt):
                visit_expr(stmt.expr)
            elif isinstance(stmt, TryCatchStmt):
                for s in stmt.try_body:
                    visit_stmt(s)
                for s in stmt.catch_body:
                    visit_stmt(s)
            elif isinstance(stmt, PrintStmt):
                visit_expr(stmt.expr)
            elif isinstance(stmt, ExprStmt):
                visit_expr(stmt.expr)

        for decl in self.ast.declarations:
            if isinstance(decl, ClassDecl):
                for ctor in decl.constructors:
                    for s in ctor.body:
                        visit_stmt(s)
                for m in decl.methods:
                    for s in m.body:
                        visit_stmt(s)
            elif isinstance(decl, FuncDecl):
                for s in decl.body:
                    visit_stmt(s)

    def collect_function_types(self) -> list:
        types = set()

        def check_type(t):
            if not t:
                return
            if self.is_function_type(t):
                types.add(t)
                ret_t, params = self.parse_function_type(t)
                check_type(ret_t)
                for p in params:
                    check_type(p)

        def collect_stmts(stmts):
            for s in stmts:
                if isinstance(s, VarDecl):
                    check_type(s.type_name)
                elif isinstance(s, IfStmt):
                    collect_stmts(s.then_body)
                    if s.else_body:
                        collect_stmts(s.else_body)
                elif isinstance(s, WhileStmt):
                    collect_stmts(s.body)
                elif isinstance(s, ForStmt):
                    if s.init and isinstance(s.init, VarDecl):
                        check_type(s.init.type_name)
                    collect_stmts(s.body)
                elif isinstance(s, TryCatchStmt):
                    check_type(s.catch_param_type)
                    collect_stmts(s.try_body)
                    collect_stmts(s.catch_body)

        for decl in self.ast.declarations:
            if isinstance(decl, ClassDecl):
                for f in decl.fields:
                    check_type(f.type_name)
                for ctor in decl.constructors:
                    for pt, _ in ctor.params:
                        check_type(pt)
                for m in decl.methods:
                    check_type(m.return_type)
                    for pt, _ in m.params:
                        check_type(pt)
                    collect_stmts(m.body)
            elif isinstance(decl, FuncDecl):
                check_type(decl.return_type)
                for pt, _ in decl.params:
                    check_type(pt)
                collect_stmts(decl.body)

        for expr in self.lifted_lambdas:
            ret_t, params = self.get_lambda_signature(expr)
            fn_t = f"{ret_t}({','.join(params)})"
            check_type(fn_t)

        return sorted(list(types))

    def get_root_class(self, class_name: str) -> str:
        curr = self.classes.get(class_name)
        while curr and curr.parent:
            curr = self.classes.get(curr.parent)
        return curr.name if curr else class_name

    def find_field_class(self, class_name: str, field_name: str):
        cls = self.classes.get(class_name)
        while cls:
            for f in cls.fields:
                if f.name == field_name:
                    return cls.name
            cls = self.classes.get(cls.parent) if cls.parent else None
        return None

    def find_method_intro_class(self, class_name: str, method_name: str) -> str:
        chain = []
        curr = class_name
        while curr:
            chain.append(curr)
            curr = self.classes[curr].parent if self.classes[curr].parent else None
        chain.reverse()
        for cname in chain:
            cls = self.classes.get(cname)
            if cls:
                for m in cls.methods:
                    if m.name == method_name:
                        return cname
        return class_name

    def get_hierarchy_methods(self, class_name: str):
        chain = []
        curr = class_name
        while curr:
            chain.append(curr)
            curr = self.classes[curr].parent if self.classes[curr].parent else None
        chain.reverse()

        methods_order = []
        methods_info = {}
        overrides = {}

        for cname in chain:
            cls = self.classes.get(cname)
            if not cls:
                continue
            for m in cls.methods:
                if m.name not in methods_info:
                    methods_order.append(m.name)
                    methods_info[m.name] = (m.return_type, m.params, cname)
                overrides[m.name] = cname

        return methods_order, methods_info, overrides

    def topo_sort_classes(self):
        sorted_names = []
        visited = set()

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            cls = self.classes.get(name)
            if cls and cls.parent:
                visit(cls.parent)
            sorted_names.append(name)

        for name in self.classes:
            visit(name)

        return [self.classes[name] for name in sorted_names]

    def generate(self) -> str:
        self.lines = []
        self.indent_level = 0
        self.lift_lambdas()

        self.emit("// Generated by myc Compiler")
        self.emit("#include <stdio.h>")
        self.emit("#include <string.h>")
        self.emit("#include <stdlib.h>")
        self.emit("#include <setjmp.h>")
        self.emit("#include <gc.h>")
        self.emit("")

        # 1. Forward struct declarations
        sorted_classes = self.topo_sort_classes()
        for cls in sorted_classes:
            self.emit(f"typedef struct {cls.name} {cls.name};")
            self.emit(f"typedef struct {cls.name}_VTable {cls.name}_VTable;")
        if sorted_classes:
            self.emit("")

        # 2. Function pointer typedefs
        fn_types = self.collect_function_types()
        for fn_t in fn_types:
            ret_t, params = self.parse_function_type(fn_t)
            c_ret = self.c_type(ret_t)
            c_params = [self.c_type(p) for p in params]
            if not c_params:
                c_params = ["void"]
            td_name = self.fn_typedef_name(fn_t)
            self.emit(f"typedef {c_ret} (*{td_name})({', '.join(c_params)});")
        if fn_types:
            self.emit("")

        # 3. Array types
        array_elem_types = ['int', 'string'] + [cls.name for cls in sorted_classes]
        for elem in array_elem_types:
            c_elem = self.c_elem_type(elem)
            arr_type = f"Array_{elem}"
            self.emit(f"typedef struct {{ int length; {c_elem} data[]; }} {arr_type};")
        self.emit("")

        # 4. Method prototypes for static vtables
        for cls in sorted_classes:
            for method in cls.methods:
                p_sig = [f"{cls.name}* this"] + [f"{self.c_type(pt)} {pn}" for pt, pn in method.params]
                self.emit(f"{self.c_type(method.return_type)} {cls.name}_{method.name}({', '.join(p_sig)});")
        if sorted_classes:
            self.emit("")

        # 5. Top-level function & lambda prototypes
        for decl in self.ast.declarations:
            if isinstance(decl, FuncDecl) and decl.name != "main":
                p_sig = [f"{self.c_type(pt)} {pn}" for pt, pn in decl.params]
                self.emit(f"{self.c_type(decl.return_type)} {decl.name}({', '.join(p_sig)});")
        for expr in self.lifted_lambdas:
            ret_t, _ = self.get_lambda_signature(expr)
            c_ret = self.c_type(ret_t)
            params = [self.c_type(pt) for pt, _ in expr.params]
            if not params:
                params = ["void"]
            self.emit(f"static {c_ret} __lambda_{expr._lambda_id}({', '.join(params)});")
        self.emit("")

        # 6. VTable struct layouts
        for cls in sorted_classes:
            methods_order, methods_info, _ = self.get_hierarchy_methods(cls.name)
            self.emit(f"struct {cls.name}_VTable {{")
            self.indent_level += 1
            if not methods_order:
                self.emit("void* __dummy;")
            else:
                for m_name in methods_order:
                    ret_t, params, intro_c = methods_info[m_name]
                    p_sig = [f"{intro_c}* this"] + [f"{self.c_type(pt)} {pn}" for pt, pn in params]
                    self.emit(f"{self.c_type(ret_t)} (*{m_name})({', '.join(p_sig)});")
            self.indent_level -= 1
            self.emit("};\n")

        # 7. Class struct layouts
        for cls in sorted_classes:
            self.gen_struct_def(cls)

        # 8. Static VTable singletons
        for cls in sorted_classes:
            methods_order, methods_info, overrides = self.get_hierarchy_methods(cls.name)
            self.emit(f"static const {cls.name}_VTable __vtable_{cls.name} = {{")
            self.indent_level += 1
            if not methods_order:
                self.emit(".__dummy = NULL")
            else:
                for m_name in methods_order:
                    impl_c = overrides[m_name]
                    ret_t, params, intro_c = methods_info[m_name]
                    p_cast = [f"{intro_c}*"] + [self.c_type(pt) for pt, _ in params]
                    cast_str = f"({self.c_type(ret_t)} (*)({', '.join(p_cast)}))"
                    self.emit(f".{m_name} = {cast_str} {impl_c}_{m_name},")
            self.indent_level -= 1
            self.emit("};\n")

        # Runtime Safety Helpers
        self.emit("static void* __check_null(const void* ptr, const char* msg) {")
        self.indent_level += 1
        self.emit("if (!ptr) {")
        self.indent_level += 1
        self.emit('fprintf(stderr, "NullPointerException: %s\\n", msg);')
        self.emit("exit(1);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("return (void*) ptr;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static void __bounds_check(int index, int length) {")
        self.indent_level += 1
        self.emit("if (index < 0 || index >= length) {")
        self.indent_level += 1
        self.emit('fprintf(stderr, "Error: Array index %d out of bounds (length %d)\\n", index, length);')
        self.emit("exit(1);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}\n")

        # Runtime Exception Handling
        self.emit("typedef struct __ExceptionFrame {")
        self.indent_level += 1
        self.emit("jmp_buf env;")
        self.emit("struct __ExceptionFrame* prev;")
        self.indent_level -= 1
        self.emit("} __ExceptionFrame;\n")
        self.emit("static __ExceptionFrame* __top_frame = NULL;")
        self.emit("static const char* __current_exception = NULL;\n")
        self.emit("static void __push_frame(__ExceptionFrame* f) {")
        self.indent_level += 1
        self.emit("f->prev = __top_frame;")
        self.emit("__top_frame = f;")
        self.indent_level -= 1
        self.emit("}\n")
        self.emit("static void __pop_frame(void) {")
        self.indent_level += 1
        self.emit("if (__top_frame) __top_frame = __top_frame->prev;")
        self.indent_level -= 1
        self.emit("}\n")
        self.emit("static void __throw(const char* msg) {")
        self.indent_level += 1
        self.emit("if (!__top_frame) {")
        self.indent_level += 1
        self.emit('fprintf(stderr, "Unhandled Exception: %s\\n", msg ? msg : "null");')
        self.emit("exit(1);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("__current_exception = msg;")
        self.emit("longjmp(__top_frame->env, 1);")
        self.indent_level -= 1
        self.emit("}\n")

        # Built-in GC Introspection
        self.emit("static void gc_collect(void) { GC_gcollect(); }")
        self.emit("static int gc_heap_size(void) { return (int) GC_get_heap_size(); }")
        self.emit("static int gc_free_bytes(void) { return (int) GC_get_free_bytes(); }")
        self.emit("")

        # Standard Library: File I/O
        self.emit("static const char* read_file(const char* path) {")
        self.indent_level += 1
        self.emit("if (!path) return \"\";")
        self.emit("FILE* f = fopen(path, \"rb\");")
        self.emit("if (!f) return \"\";")
        self.emit("fseek(f, 0, SEEK_END);")
        self.emit("long sz = ftell(f);")
        self.emit("fseek(f, 0, SEEK_SET);")
        self.emit("if (sz < 0) { fclose(f); return \"\"; }")
        self.emit("char* buf = (char*) GC_MALLOC_ATOMIC(sz + 1);")
        self.emit("size_t read_bytes = fread(buf, 1, sz, f);")
        self.emit("buf[read_bytes] = '\\0';")
        self.emit("fclose(f);")
        self.emit("return buf;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static int write_file(const char* path, const char* content) {")
        self.indent_level += 1
        self.emit("if (!path || !content) return 0;")
        self.emit("FILE* f = fopen(path, \"wb\");")
        self.emit("if (!f) return 0;")
        self.emit("size_t len = strlen(content);")
        self.emit("size_t written = fwrite(content, 1, len, f);")
        self.emit("fclose(f);")
        self.emit("return (written == len) ? 1 : 0;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static int file_exists(const char* path) {")
        self.indent_level += 1
        self.emit("if (!path) return 0;")
        self.emit("FILE* f = fopen(path, \"rb\");")
        self.emit("if (f) { fclose(f); return 1; }")
        self.emit("return 0;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static int remove_file(const char* path) {")
        self.indent_level += 1
        self.emit("if (!path) return 0;")
        self.emit("return (remove(path) == 0) ? 1 : 0;")
        self.indent_level -= 1
        self.emit("}\n")

        # Standard Library: String Utilities
        self.emit("static int str_len(const char* s) {")
        self.indent_level += 1
        self.emit("if (!s) return 0;")
        self.emit("return (int) strlen(s);")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static const char* str_sub(const char* s, int start, int len) {")
        self.indent_level += 1
        self.emit("if (!s || len <= 0 || start < 0) return \"\";")
        self.emit("int total_len = (int) strlen(s);")
        self.emit("if (start >= total_len) return \"\";")
        self.emit("if (start + len > total_len) len = total_len - start;")
        self.emit("char* res = (char*) GC_MALLOC_ATOMIC(len + 1);")
        self.emit("memcpy(res, s + start, len);")
        self.emit("res[len] = '\\0';")
        self.emit("return res;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static int str_to_int(const char* s) {")
        self.indent_level += 1
        self.emit("if (!s) return 0;")
        self.emit("return atoi(s);")
        self.indent_level -= 1
        self.emit("}\n")

        # String runtime helpers
        self.emit("static const char* __str_concat(const char* a, const char* b) {")
        self.indent_level += 1
        self.emit("size_t la = strlen(a);")
        self.emit("size_t lb = strlen(b);")
        self.emit("char* res = (char*) GC_MALLOC_ATOMIC(la + lb + 1);")
        self.emit("memcpy(res, a, la);")
        self.emit("memcpy(res + la, b, lb);")
        self.emit("res[la + lb] = '\\0';")
        self.emit("return res;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static const char* __str_concat_int(const char* a, int b) {")
        self.indent_level += 1
        self.emit("char buf[32];")
        self.emit("int len = snprintf(buf, sizeof(buf), \"%d\", b);")
        self.emit("size_t la = strlen(a);")
        self.emit("char* res = (char*) GC_MALLOC_ATOMIC(la + len + 1);")
        self.emit("memcpy(res, a, la);")
        self.emit("memcpy(res + la, buf, len);")
        self.emit("res[la + len] = '\\0';")
        self.emit("return res;")
        self.indent_level -= 1
        self.emit("}\n")

        self.emit("static const char* __int_concat_str(int a, const char* b) {")
        self.indent_level += 1
        self.emit("char buf[32];")
        self.emit("int len = snprintf(buf, sizeof(buf), \"%d\", a);")
        self.emit("size_t lb = strlen(b);")
        self.emit("char* res = (char*) GC_MALLOC_ATOMIC(len + lb + 1);")
        self.emit("memcpy(res, buf, len);")
        self.emit("memcpy(res + len, b, lb);")
        self.emit("res[len + lb] = '\\0';")
        self.emit("return res;")
        self.indent_level -= 1
        self.emit("}\n")

        # Array constructors
        for elem in array_elem_types:
            c_elem = self.c_elem_type(elem)
            arr_type = f"Array_{elem}"
            self.emit(f"static {arr_type}* __new_{arr_type}(int len) {{")
            self.indent_level += 1
            self.emit(f"{arr_type}* a = ({arr_type}*) GC_MALLOC(sizeof({arr_type}) + len * sizeof({c_elem}));")
            self.emit("a->length = len;")
            self.emit("return a;")
            self.indent_level -= 1
            self.emit("}\n")

        # Class constructors & helpers
        for cls in sorted_classes:
            if cls.constructors:
                for ctor in cls.constructors:
                    self.gen_constructor(cls.name, ctor)
            else:
                self.gen_default_constructor(cls.name)
            self.gen_new_helper(cls)

        for cls in sorted_classes:
            for method in cls.methods:
                self.gen_method(cls.name, method)

        # Lifted Lambda Functions
        for expr in self.lifted_lambdas:
            self.gen_lifted_lambda(expr)

        # Top-level functions
        for decl in self.ast.declarations:
            if isinstance(decl, FuncDecl):
                self.gen_function(decl)

        return "\n".join(self.lines)

    def gen_struct_def(self, cls: ClassDecl):
        self.emit(f"struct {cls.name} {{")
        self.indent_level += 1
        if cls.parent:
            self.emit(f"{cls.parent} base;")
        else:
            self.emit(f"const {cls.name}_VTable* vptr;")
        for field in cls.fields:
            self.emit(f"{self.c_type(field.type_name)} {field.name};")
        self.indent_level -= 1
        self.emit("};\n")

    def gen_constructor(self, class_name: str, ctor: ConstructorDecl):
        old_scope = self.scope.copy()
        self.scope = {"this": class_name}
        self.current_func_ret_type = 'void'
        self.active_try_frames = []
        self.loop_try_frames = []

        params = [f"{class_name}* this"]
        for p_type, p_name in ctor.params:
            params.append(f"{self.c_type(p_type)} {p_name}")
            self.scope[p_name] = p_type

        sig = f"void {class_name}_init({', '.join(params)})"
        self.emit(f"{sig} {{")
        self.indent_level += 1
        root_cls = self.get_root_class(class_name)
        self.emit(f"(({root_cls}*) this)->vptr = (const {root_cls}_VTable*) &__vtable_{class_name};")
        for stmt in ctor.body:
            self.gen_statement(stmt)
        self.indent_level -= 1
        self.emit("}\n")

        self.scope = old_scope

    def gen_default_constructor(self, class_name: str):
        root_cls = self.get_root_class(class_name)
        self.emit(f"void {class_name}_init({class_name}* this) {{")
        self.indent_level += 1
        self.emit(f"(({root_cls}*) this)->vptr = (const {root_cls}_VTable*) &__vtable_{class_name};")
        self.indent_level -= 1
        self.emit("}\n")

    def gen_new_helper(self, cls: ClassDecl):
        if cls.constructors:
            for ctor in cls.constructors:
                params_decl = [f"{self.c_type(pt)} {pn}" for pt, pn in ctor.params]
                params_call = [pn for _, pn in ctor.params]
                self.emit(f"static {cls.name}* __new_{cls.name}({', '.join(params_decl)}) {{")
                self.indent_level += 1
                self.emit(f"{cls.name}* this = ({cls.name}*) GC_MALLOC(sizeof({cls.name}));")
                init_args = ["this"] + params_call
                self.emit(f"{cls.name}_init({', '.join(init_args)});")
                self.emit("return this;")
                self.indent_level -= 1
                self.emit("}\n")
        else:
            self.emit(f"static {cls.name}* __new_{cls.name}() {{")
            self.indent_level += 1
            self.emit(f"{cls.name}* this = ({cls.name}*) GC_MALLOC(sizeof({cls.name}));")
            self.emit(f"{cls.name}_init(this);")
            self.emit("return this;")
            self.indent_level -= 1
            self.emit("}\n")

    def gen_method(self, class_name: str, method: MethodDecl):
        old_scope = self.scope.copy()
        self.scope = {"this": class_name}
        self.current_func_ret_type = method.return_type
        self.active_try_frames = []
        self.loop_try_frames = []

        params = [f"{class_name}* this"]
        for p_type, p_name in method.params:
            params.append(f"{self.c_type(p_type)} {p_name}")
            self.scope[p_name] = p_type

        sig = f"{self.c_type(method.return_type)} {class_name}_{method.name}({', '.join(params)})"
        self.emit(f"{sig} {{")
        self.indent_level += 1
        for stmt in method.body:
            self.gen_statement(stmt)
        self.indent_level -= 1
        self.emit("}\n")

        self.scope = old_scope

    def gen_function(self, func: FuncDecl):
        old_scope = self.scope.copy()
        self.scope = {}
        self.current_func_ret_type = func.return_type
        self.active_try_frames = []
        self.loop_try_frames = []

        if func.name == "main":
            if func.params:
                p_type, p_name = func.params[0]
                self.scope[p_name] = p_type
                self.emit("int main(int argc, char** argv) {")
                self.indent_level += 1
                self.emit("GC_INIT();")
                self.emit(f"Array_string* {p_name} = __new_Array_string(argc);")
                self.emit("for (int __i = 0; __i < argc; __i++) {")
                self.indent_level += 1
                self.emit(f"{p_name}->data[__i] = argv[__i];")
                self.indent_level -= 1
                self.emit("}")
            else:
                self.emit("int main(void) {")
                self.indent_level += 1
                self.emit("GC_INIT();")
        else:
            params = []
            for p_type, p_name in func.params:
                params.append(f"{self.c_type(p_type)} {p_name}")
                self.scope[p_name] = p_type

            sig = f"{self.c_type(func.return_type)} {func.name}({', '.join(params)})"
            self.emit(f"{sig} {{")
            self.indent_level += 1

        for stmt in func.body:
            self.gen_statement(stmt)

        self.indent_level -= 1
        self.emit("}\n")

        self.scope = old_scope

    def gen_lifted_lambda(self, expr: LambdaExpr):
        ret_t, _ = self.get_lambda_signature(expr)
        c_ret = self.c_type(ret_t)
        self.current_func_ret_type = ret_t
        self.active_try_frames = []
        self.loop_try_frames = []
        params = []
        old_scope = self.scope.copy()
        self.scope = {}
        for pt, pn in expr.params:
            params.append(f"{self.c_type(pt)} {pn}")
            self.scope[pn] = pt
        if not params:
            params = ["void"]
        self.emit(f"static {c_ret} __lambda_{expr._lambda_id}({', '.join(params)}) {{")
        self.indent_level += 1
        if isinstance(expr.body, list):
            for s in expr.body:
                self.gen_statement(s)
        else:
            body_code = self.gen_expression(expr.body)
            if ret_t == 'void':
                self.emit(f"{body_code};")
                self.emit("return;")
            else:
                self.emit(f"return {body_code};")
        self.indent_level -= 1
        self.emit("}\n")
        self.scope = old_scope

    def gen_statement(self, stmt):
        if isinstance(stmt, VarDecl):
            c_t = self.c_type(stmt.type_name)
            self.scope[stmt.name] = stmt.type_name
            if stmt.init_expr:
                expr_code = self.gen_expression(stmt.init_expr)
                val_type = self.infer_type(stmt.init_expr)
                if val_type != stmt.type_name and val_type in self.classes and stmt.type_name in self.classes:
                    expr_code = f"({c_t}) {expr_code}"
                self.emit(f"{c_t} {stmt.name} = {expr_code};")
            else:
                self.emit(f"{c_t} {stmt.name};")

        elif isinstance(stmt, Assignment):
            if isinstance(stmt.target, IndexAccess):
                target_obj_type = self.infer_type(stmt.target.obj)
                c_arr_t = self.c_type(target_obj_type)
                idx = self.gen_expression(stmt.target.index)
                val = self.gen_expression(stmt.value)
                target_type = self.infer_type(stmt.target)
                val_type = self.infer_type(stmt.value)
                if target_type != val_type and target_type in self.classes and val_type in self.classes:
                    val = f"({self.c_type(target_type)}) {val}"

                if isinstance(stmt.target.obj, Variable):
                    var_name = stmt.target.obj.name
                    self.emit(f"__bounds_check({idx}, (({c_arr_t}) __check_null({var_name}, \"Cannot index null array\"))->length);")
                    self.emit(f"{var_name}->data[{idx}] = {val};")
                else:
                    obj_raw = self.gen_expression(stmt.target.obj)
                    self.emit(f"{c_arr_t} __arr = ({c_arr_t}) __check_null({obj_raw}, \"Cannot index null array\");")
                    self.emit(f"int __i = {idx};")
                    self.emit(f"__bounds_check(__i, __arr->length);")
                    self.emit(f"__arr->data[__i] = {val};")
            else:
                target = self.gen_expression(stmt.target)
                val = self.gen_expression(stmt.value)
                target_type = self.infer_type(stmt.target)
                val_type = self.infer_type(stmt.value)
                if target_type != val_type and target_type in self.classes and val_type in self.classes:
                    val = f"({self.c_type(target_type)}) {val}"
                self.emit(f"{target} = {val};")

        elif isinstance(stmt, IfStmt):
            cond = self.gen_expression(stmt.condition)
            self.emit(f"if ({cond}) {{")
            self.indent_level += 1
            for s in stmt.then_body:
                self.gen_statement(s)
            self.indent_level -= 1
            if stmt.else_body:
                self.emit("} else {")
                self.indent_level += 1
                for s in stmt.else_body:
                    self.gen_statement(s)
                self.indent_level -= 1
            self.emit("}")

        elif isinstance(stmt, WhileStmt):
            cond = self.gen_expression(stmt.condition)
            self.emit(f"while ({cond}) {{")
            self.indent_level += 1
            self.loop_try_frames.append([])
            for s in stmt.body:
                self.gen_statement(s)
            self.loop_try_frames.pop()
            self.indent_level -= 1
            self.emit("}")

        elif isinstance(stmt, ForStmt):
            old_scope = self.scope.copy()
            init_str = ""
            if stmt.init:
                if isinstance(stmt.init, VarDecl):
                    c_t = self.c_type(stmt.init.type_name)
                    self.scope[stmt.init.name] = stmt.init.type_name
                    if stmt.init.init_expr:
                        init_str = f"{c_t} {stmt.init.name} = {self.gen_expression(stmt.init.init_expr)}"
                    else:
                        init_str = f"{c_t} {stmt.init.name}"
                elif isinstance(stmt.init, Assignment):
                    init_str = f"{self.gen_expression(stmt.init.target)} = {self.gen_expression(stmt.init.value)}"
                elif isinstance(stmt.init, ExprStmt):
                    init_str = self.gen_expression(stmt.init.expr)

            cond_str = self.gen_expression(stmt.condition) if stmt.condition else ""

            step_str = ""
            if stmt.step:
                if isinstance(stmt.step, Assignment):
                    step_str = f"{self.gen_expression(stmt.step.target)} = {self.gen_expression(stmt.step.value)}"
                elif isinstance(stmt.step, ExprStmt):
                    step_str = self.gen_expression(stmt.step.expr)

            self.emit(f"for ({init_str}; {cond_str}; {step_str}) {{")
            self.indent_level += 1
            self.loop_try_frames.append([])
            for s in stmt.body:
                self.gen_statement(s)
            self.loop_try_frames.pop()
            self.indent_level -= 1
            self.emit("}")
            self.scope = old_scope

        elif isinstance(stmt, BreakStmt):
            if self.loop_try_frames and self.loop_try_frames[-1]:
                for _ in reversed(self.loop_try_frames[-1]):
                    self.emit("__pop_frame();")
            self.emit("break;")

        elif isinstance(stmt, ContinueStmt):
            if self.loop_try_frames and self.loop_try_frames[-1]:
                for _ in reversed(self.loop_try_frames[-1]):
                    self.emit("__pop_frame();")
            self.emit("continue;")

        elif isinstance(stmt, ReturnStmt):
            if self.active_try_frames:
                if stmt.value:
                    val = self.gen_expression(stmt.value)
                    ret_type = self.c_type(self.current_func_ret_type)
                    self.emit(f"{ret_type} __ret_val = {val};")
                    for _ in reversed(self.active_try_frames):
                        self.emit("__pop_frame();")
                    self.emit("return __ret_val;")
                else:
                    for _ in reversed(self.active_try_frames):
                        self.emit("__pop_frame();")
                    self.emit("return;")
            else:
                if stmt.value:
                    val = self.gen_expression(stmt.value)
                    self.emit(f"return {val};")
                else:
                    self.emit("return;")

        elif isinstance(stmt, ThrowStmt):
            val = self.gen_expression(stmt.expr)
            self.emit(f"__throw({val});")

        elif isinstance(stmt, TryCatchStmt):
            fid = self.try_frame_counter
            self.try_frame_counter += 1
            frame_var = f"__frame_{fid}"

            self.emit("{")
            self.indent_level += 1
            self.emit(f"__ExceptionFrame {frame_var};")
            self.emit(f"__push_frame(&{frame_var});")
            self.emit(f"if (setjmp({frame_var}.env) == 0) {{")
            self.indent_level += 1

            self.active_try_frames.append(frame_var)
            if self.loop_try_frames:
                self.loop_try_frames[-1].append(frame_var)

            for s in stmt.try_body:
                self.gen_statement(s)

            self.emit("__pop_frame();")

            self.active_try_frames.pop()
            if self.loop_try_frames and self.loop_try_frames[-1]:
                self.loop_try_frames[-1].pop()

            self.indent_level -= 1
            self.emit("} else {")
            self.indent_level += 1
            self.emit("__pop_frame();")
            c_param_t = self.c_type(stmt.catch_param_type)
            self.emit(f"{c_param_t} {stmt.catch_param_name} = __current_exception;")
            old_scope = self.scope.copy()
            self.scope[stmt.catch_param_name] = stmt.catch_param_type

            for s in stmt.catch_body:
                self.gen_statement(s)

            self.scope = old_scope
            self.indent_level -= 1
            self.emit("}")
            self.indent_level -= 1
            self.emit("}")

        elif isinstance(stmt, PrintStmt):
            val = self.gen_expression(stmt.expr)
            t = self.infer_type(stmt.expr)
            if t == 'string':
                self.emit(f'printf("%s\\n", {val});')
            else:
                self.emit(f'printf("%d\\n", {val});')

        elif isinstance(stmt, ExprStmt):
            expr_code = self.gen_expression(stmt.expr)
            self.emit(f"{expr_code};")

    def gen_expression(self, expr) -> str:
        if isinstance(expr, Number):
            return str(expr.value)

        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, BoolLiteral):
            return '1' if expr.value else '0'

        if isinstance(expr, NullLiteral):
            return 'NULL'

        if isinstance(expr, Variable):
            return expr.name

        if isinstance(expr, LambdaExpr):
            return f"__lambda_{expr._lambda_id}"

        if isinstance(expr, UnaryExpr):
            operand = self.gen_expression(expr.operand)
            return f"({expr.op}{operand})"

        if isinstance(expr, BinaryExpr):
            left = self.gen_expression(expr.left)
            right = self.gen_expression(expr.right)
            lt = self.infer_type(expr.left)
            rt = self.infer_type(expr.right)

            if expr.op == '+':
                if lt == 'string' and rt == 'string':
                    return f"__str_concat({left}, {right})"
                if lt == 'string' and rt == 'int':
                    return f"__str_concat_int({left}, {right})"
                if lt == 'int' and rt == 'string':
                    return f"__int_concat_str({left}, {right})"

            if lt == 'string' and rt == 'string':
                if expr.op == '==':
                    return f"(strcmp({left}, {right}) == 0)"
                elif expr.op == '!=':
                    return f"(strcmp({left}, {right}) != 0)"

            return f"({left} {expr.op} {right})"

        if isinstance(expr, FuncCall):
            args_strs = [self.gen_expression(a) for a in expr.args]
            # Call through function pointer variable with null-guard
            if expr.name in self.scope and self.is_function_type(self.scope[expr.name]):
                fn_t = self.fn_typedef_name(self.scope[expr.name])
                checked = f"(({fn_t}) __check_null({expr.name}, \"Cannot invoke null function pointer\"))"
                return f"{checked}({', '.join(args_strs)})"
            return f"{expr.name}({', '.join(args_strs)})"

        if isinstance(expr, NewExpr):
            arg_strs = [self.gen_expression(arg) for arg in expr.args]
            return f"__new_{expr.class_name}({', '.join(arg_strs)})"

        if isinstance(expr, NewArrayExpr):
            size = self.gen_expression(expr.size)
            return f"__new_Array_{expr.element_type}({size})"

        if isinstance(expr, IndexAccess):
            obj_type = self.infer_type(expr.obj)
            c_arr_t = self.c_type(obj_type)
            idx = self.gen_expression(expr.index)
            if isinstance(expr.obj, Variable):
                var_name = expr.obj.name
                obj_checked = f"(({c_arr_t}) __check_null({var_name}, \"Cannot index null array\"))"
                return f"(__bounds_check({idx}, {obj_checked}->length), {var_name}->data[{idx}])"
            else:
                obj_raw = self.gen_expression(expr.obj)
                return (
                    f"(__extension__({{"
                    f"{c_arr_t} __arr = ({c_arr_t}) __check_null({obj_raw}, \"Cannot index null array\"); "
                    f"int __i = {idx}; "
                    f"__bounds_check(__i, __arr->length); "
                    f"__arr->data[__i]; "
                    f"}}))"
                )

        if isinstance(expr, MemberAccess):
            obj_type = self.infer_type(expr.obj)

            if obj_type.endswith('[]'):
                if expr.member == 'length':
                    if isinstance(expr.obj, Variable) and expr.obj.name == 'this':
                        obj_checked = "this"
                    else:
                        obj_checked = f"(({self.c_type(obj_type)}) __check_null({self.gen_expression(expr.obj)}, \"Cannot read length of null array\"))"
                    return f"{obj_checked}->length"

            defining_class = self.find_field_class(obj_type, expr.member)
            if isinstance(expr.obj, Variable) and expr.obj.name == 'this':
                obj_checked = "this"
            else:
                obj_checked = f"(({self.c_type(obj_type)}) __check_null({self.gen_expression(expr.obj)}, \"Cannot access field '{expr.member}' on null reference\"))"

            if defining_class and defining_class != obj_type:
                return f"(({defining_class}*) {obj_checked})->{expr.member}"

            return f"{obj_checked}->{expr.member}"

        if isinstance(expr, MethodCall):
            obj_type = self.infer_type(expr.obj)

            # Check if invoking a function pointer field
            defining_field_class = self.find_field_class(obj_type, expr.method)
            if defining_field_class:
                cls = self.classes[defining_field_class]
                field_obj = next((f for f in cls.fields if f.name == expr.method), None)
                if field_obj and self.is_function_type(field_obj.type_name):
                    fn_t = self.fn_typedef_name(field_obj.type_name)
                    obj = self.gen_expression(expr.obj)
                    args_exprs = [self.gen_expression(arg) for arg in expr.args]
                    c_obj_t = self.c_type(obj_type)
                    if isinstance(expr.obj, Variable) and expr.obj.name == 'this':
                        field_access = f"this->{expr.method}"
                    else:
                        obj_checked = f"(({c_obj_t}) __check_null({obj}, \"Cannot access field on null reference\"))"
                        if defining_field_class != obj_type:
                            field_access = f"(({defining_field_class}*) {obj_checked})->{expr.method}"
                        else:
                            field_access = f"{obj_checked}->{expr.method}"
                    checked_fn = f"(({fn_t}) __check_null({field_access}, \"Cannot invoke null function pointer\"))"
                    return f"{checked_fn}({', '.join(args_exprs)})"

            # Regular dynamic vtable dispatch
            root_cls = self.get_root_class(obj_type)
            intro_class = self.find_method_intro_class(obj_type, expr.method)
            args_exprs = [self.gen_expression(arg) for arg in expr.args]

            if isinstance(expr.obj, Variable) and expr.obj.name == 'this':
                all_args = [f"({intro_class}*) this"] + args_exprs
                return f"((const {intro_class}_VTable*) (({root_cls}*) this)->vptr)->{expr.method}({', '.join(all_args)})"
            elif isinstance(expr.obj, Variable):
                var_name = expr.obj.name
                vptr_target = f"(({root_cls}*) __check_null({var_name}, \"Cannot invoke method '{expr.method}' on null reference\"))"
                all_args = [f"({intro_class}*) {var_name}"] + args_exprs
                return f"((const {intro_class}_VTable*) {vptr_target}->vptr)->{expr.method}({', '.join(all_args)})"
            else:
                c_t = self.c_type(obj_type)
                obj_raw = self.gen_expression(expr.obj)
                all_args = [f"({intro_class}*) __rcv"] + args_exprs
                return (
                    f"(__extension__({{"
                    f"{c_t} __rcv = ({c_t}) __check_null({obj_raw}, \"Cannot invoke method '{expr.method}' on null reference\"); "
                    f"((const {intro_class}_VTable*) (({root_cls}*) __rcv)->vptr)->{expr.method}({', '.join(all_args)}); "
                    f"}}))"
                )

        raise NotImplementedError(f"Unsupported expression: {expr}")
