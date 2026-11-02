"""Bounded, spacing-preserving column counts for rotated text strips."""

from __future__ import annotations

MAX_TEXT = 100_000
MAX_ROWS = 2_000
MAX_COLUMN = 100_000


def analyze(text: object, column: object) -> dict:
    """Count ASCII letters by physical source column, without interpreting them.

    The one-based guide is supplied by the user. Blank lines are ignored but
    retained in the line numbering. Only literal spaces are accepted so tabs
    and variable-width characters cannot silently corrupt the geometry.
    """
    if not isinstance(text, str) or not text:
        raise ValueError("Paste the strip rows first.")
    if len(text) > MAX_TEXT:
        raise ValueError(f"Input exceeds {MAX_TEXT} characters.")
    if isinstance(column, bool) or not isinstance(column, int) or not 1 <= column <= MAX_COLUMN:
        raise ValueError(f"Guide column must be a whole number from 1 to {MAX_COLUMN}.")
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) > MAX_ROWS:
        raise ValueError(f"Input exceeds {MAX_ROWS} lines.")
    rows = []
    for number, line in enumerate(lines, 1):
        if any(not (c == " " or "A" <= c <= "Z" or "a" <= c <= "z") for c in line):
            raise ValueError(f"Line {number}: use ASCII letters and literal spaces only; tabs are not supported.")
        positions = [i + 1 for i, c in enumerate(line) if c != " "]
        if not positions:
            continue
        rows.append({
            "line": number,
            "letters": len(positions),
            "before": sum(i < column for i in positions),
            "on": sum(i == column for i in positions),
            "after": sum(i > column for i in positions),
        })
    if not rows:
        raise ValueError("Input must contain at least one ASCII letter.")
    return {"guide_column": column, "rows": rows}
