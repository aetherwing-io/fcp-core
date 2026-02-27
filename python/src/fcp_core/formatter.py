"""Compact response formatting for FCP tool outputs.

Provides standard result formatting with prefix conventions
and fuzzy matching for suggestions.
"""

from __future__ import annotations

import difflib


def format_result(
    success: bool,
    message: str,
    prefix: str = "",
) -> str:
    """Format a mutation result line.

    Parameters
    ----------
    success : bool
        Whether the operation succeeded.
    message : str
        The result message.
    prefix : str, optional
        Override prefix character. If empty, defaults to ``+`` for success
        and ``!`` for failure.

    Returns
    -------
    str
        Formatted result string.
    """
    if prefix:
        return f"{prefix} {message}"
    if success:
        return f"+ {message}"
    return f"! {message}"


def suggest(input_str: str, candidates: list[str]) -> str | None:
    """Find the closest match for *input_str* among *candidates*.

    Uses difflib's SequenceMatcher for fuzzy matching. Returns the best
    match if the similarity ratio is above 0.6, otherwise None.

    Parameters
    ----------
    input_str : str
        The input to match.
    candidates : list[str]
        Valid candidates to match against.

    Returns
    -------
    str | None
        The best match, or None if no good match found.
    """
    if not candidates:
        return None
    matches = difflib.get_close_matches(input_str, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None
