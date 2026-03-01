"""Generic op-string parser — tokenize, classify, and structure an op string.

Produces a :class:`ParsedOp` on success or a :class:`ParseError` on failure.
Domain-agnostic: does NOT interpret what positionals mean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from fcp_core.tokenizer import is_key_value, is_selector, parse_key_value, tokenize_with_meta


@dataclass
class ParsedOp:
    """Successfully parsed operation."""

    verb: str
    positionals: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)
    selectors: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class ParseError:
    """Parsing failure."""

    success: bool = field(default=False, init=False)
    error: str = ""
    raw: str = ""


def parse_op(
    op_string: str,
    is_positional: Callable[[str], bool] | None = None,
) -> ParsedOp | ParseError:
    """Parse an op string into a structured :class:`ParsedOp`.

    First token becomes the verb. Remaining tokens are classified:
    - ``@``-prefixed tokens -> selectors
    - ``key:value`` tokens -> params (unless quoted or domain override)
    - Everything else -> positionals (in order)

    Parameters
    ----------
    op_string : str
        The raw op string, e.g. ``'add svc AuthService theme:blue'``.
    is_positional : callable, optional
        Domain-level callback: ``is_positional(token) -> bool``.
        If provided, called BEFORE ``is_key_value()`` — returns True
        to force the token as a positional (e.g. column ranges ``B:G``).

    Returns
    -------
    ParsedOp | ParseError
    """
    raw = op_string.strip()
    if not raw:
        return ParseError(error="Empty op string", raw=raw)

    try:
        tokens = tokenize_with_meta(raw)
    except ValueError as exc:
        return ParseError(error=f"Tokenization failed: {exc}", raw=raw)

    if not tokens:
        return ParseError(error="No tokens after tokenization", raw=raw)

    verb = tokens[0].text.lower()
    rest = tokens[1:]

    selectors: list[str] = []
    params: dict[str, str] = {}
    positionals: list[str] = []

    for token in rest:
        text = token.text
        if is_selector(text):
            selectors.append(text)
        elif token.was_quoted:
            # Quoted tokens are always positional — skip key:value check
            positionals.append(text)
        elif is_positional is not None and is_positional(text):
            # Domain extension: force as positional (e.g. column ranges)
            positionals.append(text)
        elif is_key_value(text):
            k, v = parse_key_value(text)
            params[k] = v
        else:
            positionals.append(text)

    return ParsedOp(
        verb=verb,
        positionals=positionals,
        params=params,
        selectors=selectors,
        raw=raw,
    )
