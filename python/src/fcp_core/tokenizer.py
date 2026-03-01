"""Quote-aware tokenizer for FCP op strings.

Splits on whitespace but respects quoted strings (single and double quotes).
Provides helpers for key:value token detection and parsing.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


@dataclass
class TokenMeta:
    """A token with metadata about how it was originally written."""

    text: str
    was_quoted: bool


def tokenize_with_meta(op_string: str) -> list[TokenMeta]:
    """Split *op_string* on whitespace, respecting quoted substrings.

    Returns structured tokens that preserve whether each token was
    originally quoted.  This allows downstream code (e.g. ``parse_op``)
    to skip key:value classification for quoted tokens like ``"LTV:CAC"``.

    Examples
    --------
    >>> tokenize_with_meta('set A1 "LTV:CAC"')
    [TokenMeta(text='set', was_quoted=False),
     TokenMeta(text='A1', was_quoted=False),
     TokenMeta(text='LTV:CAC', was_quoted=True)]
    """
    lexer = shlex.shlex(op_string, posix=False)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\n\r"
    lexer.commenters = ""  # disable # as comment char

    result: list[TokenMeta] = []
    for raw_token in lexer:
        # Detect if the token was quoted (shlex posix=False preserves quotes)
        if (raw_token.startswith('"') and raw_token.endswith('"') and len(raw_token) >= 2) or \
           (raw_token.startswith("'") and raw_token.endswith("'") and len(raw_token) >= 2):
            result.append(TokenMeta(text=raw_token[1:-1], was_quoted=True))
        else:
            result.append(TokenMeta(text=raw_token, was_quoted=False))

    return result


def tokenize(op_string: str) -> list[str]:
    """Split *op_string* on whitespace, respecting quoted substrings.

    Examples
    --------
    >>> tokenize('add svc "My Service" theme:blue')
    ['add', 'svc', 'My Service', 'theme:blue']
    >>> tokenize("add svc 'My Service' theme:blue")
    ['add', 'svc', 'My Service', 'theme:blue']
    """
    return [t.text for t in tokenize_with_meta(op_string)]


# Patterns for cell range detection (spreadsheet A1 notation).
# Cell ref: 1-3 letters followed by digits (e.g. A1, BB23, XFD1048576)
_CELL_REF_RE = re.compile(r"^[A-Za-z]{1,3}\d+$")
# Row ref: digits only (e.g. 1, 23)
_ROW_REF_RE = re.compile(r"^[0-9]+$")

# Note: Pure column ranges (A:E, B:B) are intentionally NOT detected here
# because they are ambiguous with key:value pairs like "theme:blue" or
# "vel:mf". Column-only ranges should use hyphen syntax (A-E) or be
# handled at the domain level.


def _is_cell_range(token: str) -> bool:
    """Return True if *token* looks like a spreadsheet cell range.

    Recognized patterns (with optional ``Sheet!`` prefix):
      A1:F1     — cell range (letters+digits : letters+digits)
      3:3       — row range (digits : digits)
      1:5       — row range
      Sheet2!A1:B10 — cross-sheet cell range

    NOT recognized (ambiguous with key:value):
      A:E       — column range (use A-E instead, or handle at domain level)
    """
    ref = token
    # Strip optional sheet prefix (Sheet2!A1:B10 → A1:B10)
    if "!" in ref:
        ref = ref.split("!", 1)[1]

    if ":" not in ref:
        return False

    left, right = ref.split(":", 1)
    if not left or not right:
        return False

    # Cell range: A1:F1 (most common spreadsheet range pattern)
    if _CELL_REF_RE.match(left) and _CELL_REF_RE.match(right):
        return True
    # Row range: 1:5 or 3:3 (no FCP key is ever a pure number)
    if _ROW_REF_RE.match(left) and _ROW_REF_RE.match(right):
        return True

    return False


def is_key_value(token: str) -> bool:
    """Return True if *token* is a ``key:value`` pair.

    A key:value token contains ``:``, does NOT start with ``@``
    (that is a selector), is not an arrow (``->``), is not a
    formula (starts with ``=``), and is not a spreadsheet cell
    range (e.g. ``A1:F1``, ``B:B``, ``3:3``).
    """
    if token.startswith("@"):
        return False
    if "->" in token:
        return False
    # Formulas (=SUM(A1:B2)) are values, not key:value pairs
    if token.startswith("="):
        return False
    # Spreadsheet cell ranges (A1:F1, B:B, 3:3) are positional args
    if _is_cell_range(token):
        return False
    return ":" in token


def parse_key_value(token: str) -> tuple[str, str]:
    """Split *token* on the first ``:`` and return ``(key, value)``."""
    key, _, value = token.partition(":")
    return key, value


def is_selector(token: str) -> bool:
    """Return True if *token* is a selector (starts with ``@``)."""
    return token.startswith("@")


def is_arrow(token: str) -> bool:
    """Return True if *token* is an arrow (``->``, ``<->``, or ``--``)."""
    return token in ("->", "<->", "--")
