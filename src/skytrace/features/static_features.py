"""Static source-code feature extractor for the Random Forest baseline.

All features are computed purely from the function source code — no
historical / future-derived features are used (those are NULL in this
phase per the dataset card).

Features:
    length_chars, n_lines, n_blank_lines, n_code_lines
    n_braces_open, n_braces_close, n_parens_open, n_parens_close
    n_branches_if, n_branches_else, n_switch, n_case
    n_loops_for, n_loops_while, n_loops_do
    n_returns
    n_function_calls (heuristic)
    n_pointers, n_arrays
    n_comments, n_preprocessor
    n_keywords_static, n_keywords_const, n_keywords_struct,
    n_keywords_typedef, n_keywords_sizeof
    n_macros (uppercase identifiers >= 4 chars)
    avg_line_length, max_line_length
    n_distinct_tokens, n_unique_identifiers
    has_assert, has_malloc, has_free, has_memcpy, has_strcpy,
    has_sprintf, has_gets, has_cast

The feature set is intentionally lightweight — Random Forest is a baseline
to demonstrate "what you can do with shallow features", so we don't need
expensive AST features here.
"""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np
import pandas as pd

# Regex patterns (precompiled for speed)
_RE_COMMENT_LINE = re.compile(r"^\s*(//|/\*|\*)")
_RE_PREPROC = re.compile(r"^\s*#")
_RE_BLANK = re.compile(r"^\s*$")
_RE_IF = re.compile(r"\bif\b\s*\(")
_RE_ELSE = re.compile(r"\belse\b")
_RE_SWITCH = re.compile(r"\bswitch\b\s*\(")
_RE_CASE = re.compile(r"\bcase\b\s+")
_RE_FOR = re.compile(r"\bfor\b\s*\(")
_RE_WHILE = re.compile(r"\bwhile\b\s*\(")
_RE_DO = re.compile(r"\bdo\b\s*\{?")
_RE_RETURN = re.compile(r"\breturn\b")
_RE_FUNC_CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_RE_MACRO = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
_RE_IDENTIFIER = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_RE_KEYWORDS = {
    "static": re.compile(r"\bstatic\b"),
    "const": re.compile(r"\bconst\b"),
    "struct": re.compile(r"\bstruct\b"),
    "typedef": re.compile(r"\btypedef\b"),
    "sizeof": re.compile(r"\bsizeof\b"),
}
_RE_CAST = re.compile(r"\(\s*(?:int|char|float|double|long|short|unsigned|void|size_t|bool)\s*\*?\s*\)")
_RE_ASSERT = re.compile(r"\bassert\s*\(")
_RE_MALLOC = re.compile(r"\bmalloc\s*\(")
_RE_FREE = re.compile(r"\bfree\s*\(")
_RE_MEMCPY = re.compile(r"\bmemcpy\s*\(")
_RE_STRCPY = re.compile(r"\bstrcpy\s*\(")
_RE_SPRINTF = re.compile(r"\bsprintf\s*\(")
_RE_GETS = re.compile(r"\bgets\s*\(")

# C keywords we should NOT count as identifiers
_C_KEYWORDS = {
    "if", "else", "switch", "case", "default", "for", "while", "do",
    "return", "break", "continue", "goto", "sizeof", "typedef",
    "static", "const", "struct", "union", "enum", "extern", "register",
    "volatile", "auto", "inline", "restrict",
    "void", "char", "short", "int", "long", "float", "double",
    "signed", "unsigned", "bool", "_Bool", "size_t", "ssize_t",
    "NULL", "true", "false",
    "void", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
}


def extract_features(code: str) -> Dict[str, float]:
    """Extract a feature dict from a single function source string."""
    if not isinstance(code, str) or not code:
        code = ""

    lines = code.splitlines()
    n_lines = len(lines)
    n_blank = sum(1 for l in lines if _RE_BLANK.match(l))
    n_comment = sum(1 for l in lines if _RE_COMMENT_LINE.match(l))
    n_preproc = sum(1 for l in lines if _RE_PREPROC.match(l))
    n_code = n_lines - n_blank - n_comment

    line_lens = [len(l) for l in lines]
    avg_line = float(np.mean(line_lens)) if line_lens else 0.0
    max_line = float(max(line_lens)) if line_lens else 0

    n_braces_open = code.count("{")
    n_braces_close = code.count("}")
    n_parens_open = code.count("(")
    n_parens_close = code.count(")")
    n_arrays = code.count("[")
    n_pointers = code.count("*")

    n_if = len(_RE_IF.findall(code))
    n_else = len(_RE_ELSE.findall(code))
    n_switch = len(_RE_SWITCH.findall(code))
    n_case = len(_RE_CASE.findall(code))
    n_for = len(_RE_FOR.findall(code))
    n_while = len(_RE_WHILE.findall(code))
    n_do = len(_RE_DO.findall(code))
    n_return = len(_RE_RETURN.findall(code))

    # Function calls — heuristic: identifier immediately followed by '('
    # Minus the control-flow keywords we already counted.
    calls = _RE_FUNC_CALL.findall(code)
    control_kw = {"if", "for", "while", "switch", "sizeof", "return"}
    n_func_calls = sum(1 for c in calls if c not in control_kw)

    n_macros = len(_RE_MACRO.findall(code))

    # Keyword counts
    kw_counts = {f"n_keywords_{k}": len(p.findall(code)) for k, p in _RE_KEYWORDS.items()}

    # Identifiers
    all_idents = _RE_IDENTIFIER.findall(code)
    user_idents = [i for i in all_idents if i not in _C_KEYWORDS]
    n_distinct_tokens = len(set(all_idents))
    n_unique_idents = len(set(user_idents))

    return {
        "length_chars": float(len(code)),
        "n_lines": float(n_lines),
        "n_blank_lines": float(n_blank),
        "n_code_lines": float(n_code),
        "n_braces_open": float(n_braces_open),
        "n_braces_close": float(n_braces_close),
        "n_parens_open": float(n_parens_open),
        "n_parens_close": float(n_parens_close),
        "n_branches_if": float(n_if),
        "n_branches_else": float(n_else),
        "n_switch": float(n_switch),
        "n_case": float(n_case),
        "n_loops_for": float(n_for),
        "n_loops_while": float(n_while),
        "n_loops_do": float(n_do),
        "n_returns": float(n_return),
        "n_function_calls": float(n_func_calls),
        "n_pointers": float(n_pointers),
        "n_arrays": float(n_arrays),
        "n_comments": float(n_comment),
        "n_preprocessor": float(n_preproc),
        "n_macros": float(n_macros),
        "avg_line_length": avg_line,
        "max_line_length": max_line,
        "n_distinct_tokens": float(n_distinct_tokens),
        "n_unique_identifiers": float(n_unique_idents),
        "has_assert": float(bool(_RE_ASSERT.search(code))),
        "has_malloc": float(bool(_RE_MALLOC.search(code))),
        "has_free": float(bool(_RE_FREE.search(code))),
        "has_memcpy": float(bool(_RE_MEMCPY.search(code))),
        "has_strcpy": float(bool(_RE_STRCPY.search(code))),
        "has_sprintf": float(bool(_RE_SPRINTF.search(code))),
        "has_gets": float(bool(_RE_GETS.search(code))),
        "has_cast": float(bool(_RE_CAST.search(code))),
        **kw_counts,
    }


FEATURE_NAMES: List[str] = list(extract_features("").keys())


def extract_features_batch(codes: pd.Series) -> pd.DataFrame:
    """Extract features for a whole series of function codes.

    Returns a DataFrame with one row per input code, columns = FEATURE_NAMES.
    """
    rows = [extract_features(c if isinstance(c, str) else "") for c in codes]
    return pd.DataFrame(rows, columns=FEATURE_NAMES)
