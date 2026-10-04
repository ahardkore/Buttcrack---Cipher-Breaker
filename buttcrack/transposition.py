"""Small, inspectable columnar-transposition laboratory."""

from __future__ import annotations


def keyword_order(keyword: str) -> list[int]:
    return sorted(range(len(keyword)), key=lambda i: (keyword[i].upper(), i))


def encrypt(text: str, keyword: str) -> str:
    if not keyword or len(text) % len(keyword):
        raise ValueError("length must fill the grid")
    cols = len(keyword)
    rows = len(text) // cols
    grid = [text[r * cols : (r + 1) * cols] for r in range(rows)]
    return "".join(grid[r][c] for c in keyword_order(keyword) for r in range(rows))


def double_encrypt(text: str, first: str, second: str) -> str:
    return encrypt(encrypt(text, first), second)


def double_decrypt(text: str, first: str, second: str) -> str:
    return decrypt(decrypt(text, second), first)


def decrypt(text: str, keyword: str) -> str:
    if not keyword or len(text) % len(keyword):
        raise ValueError("length must fill the grid")
    cols = len(keyword)
    rows = len(text) // cols
    grid = [[""] * cols for _ in range(rows)]
    q = 0
    for c in keyword_order(keyword):
        for r in range(rows):
            grid[r][c] = text[q]
            q += 1
    return "".join("".join(row) for row in grid)
