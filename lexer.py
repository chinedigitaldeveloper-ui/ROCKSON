import re
from dataclasses import dataclass

@dataclass
class Token:
    type: str
    value: str
    line: int

TOKEN_SPECIFICATION = [
    # Comments and Whitespace
    ('COMMENT',      r'//[^\n]*'),
    ('WHITESPACE',   r'[ \t]+'),
    ('NEWLINE',      r'\n'),

    # Keywords
    ('CLASS',        r'\bclass\b'),
    ('EXTENDS',      r'\bextends\b'),
    ('NEW',          r'\bnew\b'),
    ('THIS',         r'\bthis\b'),
    ('NULL',         r'\bnull\b'),
    ('IMPORT',       r'\bimport\b'),
    ('IF',           r'\bif\b'),
    ('ELSE',         r'\belse\b'),
    ('WHILE',        r'\bwhile\b'),
    ('FOR',          r'\bfor\b'),
    ('BREAK',        r'\bbreak\b'),
    ('CONTINUE',     r'\bcontinue\b'),
    ('RETURN',       r'\breturn\b'),
    ('TRY',          r'\btry\b'),
    ('CATCH',        r'\bcatch\b'),
    ('THROW',        r'\bthrow\b'),
    ('PRINT',        r'\bprint\b'),
    ('TRUE',         r'\btrue\b'),
    ('FALSE',        r'\bfalse\b'),
    ('INT_TYPE',     r'\bint\b'),
    ('STRING_TYPE',  r'\bstring\b'),
    ('VOID_TYPE',    r'\bvoid\b'),

    # String literals
    ('STRING',       r'"(?:\\.|[^"\\\n])*"'),

    # Literals & Identifiers
    ('NUMBER',       r'\b\d+\b'),
    ('IDENTIFIER',   r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),

    # Two-character Comparison/Logical Operators
    ('EQ',           r'=='),
    ('NEQ',          r'!='),
    ('LTE',          r'<='),
    ('GTE',          r'>='),
    ('ARROW',        r'=>'),
    ('AND',          r'&&'),
    ('OR',           r'\|\|'),

    # Arithmetic, Single Operators & Punctuation
    ('ASSIGN',       r'='),
    ('PLUS',         r'\+'),
    ('MINUS',        r'-'),
    ('TIMES',        r'\*'),
    ('DIV',          r'/'),
    ('NOT',          r'!'),
    ('LT',           r'<'),
    ('GT',           r'>'),
    ('LPAREN',       r'\('),
    ('RPAREN',       r'\)'),
    ('LBRACE',       r'\{'),
    ('RBRACE',       r'\}'),
    ('LBRACKET',     r'\['),
    ('RBRACKET',     r'\]'),
    ('DOT',          r'\.'),
    ('COMMA',        r','),
    ('SEMICOLON',    r';'),

    # Mismatches
    ('MISMATCH',     r'.'),
]

TOKEN_REGEX = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPECIFICATION)

def tokenize(source_code: str):
    tokens = []
    line_num = 1
    for match in re.finditer(TOKEN_REGEX, source_code):
        kind = match.lastgroup
        value = match.group()

        if kind == 'NEWLINE':
            line_num += 1
            continue
        elif kind in ('WHITESPACE', 'COMMENT'):
            continue
        elif kind == 'MISMATCH':
            raise SyntaxError(f"Unexpected character {value!r} on line {line_num}")

        tokens.append(Token(kind, value, line_num))

    tokens.append(Token('EOF', '', line_num))
    return tokens
