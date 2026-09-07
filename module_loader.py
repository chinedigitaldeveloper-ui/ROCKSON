import os
from lexer import tokenize
from parser import Parser, Program, ImportDecl

class ModuleError(Exception):
    pass

class ModuleLoader:
    def __init__(self):
        self.loaded_files = set()
        self.loading_stack = []
        self.declarations = []

    def load(self, entry_file: str) -> Program:
        if not os.path.exists(entry_file):
            raise ModuleError(f"Source file '{entry_file}' not found.")
        canonical_path = os.path.realpath(entry_file)
        self._load_file(canonical_path)
        return Program(self.declarations)

    def _load_file(self, file_path: str):
        if file_path in self.loaded_files:
            return

        if file_path in self.loading_stack:
            cycle = " -> ".join([os.path.basename(p) for p in self.loading_stack] + [os.path.basename(file_path)])
            raise ModuleError(f"Circular import detected: {cycle}")

        self.loading_stack.append(file_path)

        with open(file_path, "r") as f:
            src = f.read()

        try:
            tokens = tokenize(src)
            parser = Parser(tokens)
            ast = parser.parse()
        except SyntaxError as e:
            rel = os.path.relpath(file_path)
            raise SyntaxError(f"[{rel}] {e}")

        dir_name = os.path.dirname(file_path)

        # Process imports in dependency order
        for decl in ast.declarations:
            if isinstance(decl, ImportDecl):
                dep_path = os.path.normpath(os.path.join(dir_name, decl.path))
                if not os.path.exists(dep_path):
                    raise ModuleError(f"Cannot import '{decl.path}': File not found")
                self._load_file(os.path.realpath(dep_path))
            else:
                self.declarations.append(decl)

        self.loading_stack.pop()
        self.loaded_files.add(file_path)
