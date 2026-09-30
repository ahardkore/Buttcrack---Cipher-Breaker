#!/usr/bin/env python3
"""Typeset the Kryptos manuscript as a PDF.

Uses the repository's own dependency-free PDF writer (``ventures/puzzle-packs/
pdf.py``) rather than pulling in reportlab, because this sandbox has no network
and the writer is already here and already used to produce the puzzle books.

It renders a practical subset of Markdown -- headings, paragraphs, bullet and
numbered lists, block quotes, fenced code, tables and horizontal rules -- which
is everything the manuscript actually uses.

    python3 scripts/build_manuscript_pdf.py
    python3 scripts/build_manuscript_pdf.py --source FILE --out FILE.pdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ventures" / "puzzle-packs"))

from pdf import (  # noqa: E402
    COURIER,
    HELV_B,
    TIMES,
    TIMES_B,
    TIMES_I,
    Document,
    wrap,
)

PAGE_W, PAGE_H = 612.0, 792.0
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 72.0, 72.0, 64.0
BODY = PAGE_W - 2 * MARGIN_X

#: Characters the base-14 fonts cannot encode, and readable stand-ins. The
#: manuscript uses proper typography; a PDF that silently dropped an em dash
#: would change sentences.
REPLACEMENTS = {
    "—": "--", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
    "…": "...", "×": "x", "≈": "~", "≥": ">=", "≤": "<=", "−": "-",
    "≡": "==", "⟶": "->", "→": "->", "·": "-", "½": "1/2", "²": "2",
    "³": "3", "⁴": "4", "𝑘": "k", "Z/26": "Z/26",
}


def clean(text: str) -> str:
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    # Markdown emphasis and inline code markers carry no meaning once typeset.
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # links -> their text
    return "".join(c if ord(c) < 256 else "?" for c in text)


class Book:
    """A running page with a cursor, so content can flow across pages."""

    def __init__(self, title: str) -> None:
        self.doc = Document(PAGE_W, PAGE_H)
        self.title = title
        self.page = None
        self.y = 0.0
        self.number = 0
        self.new_page(first=True)

    def new_page(self, first: bool = False) -> None:
        if self.page is not None or first:
            self.number += 1
        self.page = self.doc.new_page()
        self.y = PAGE_H - MARGIN_TOP
        if self.number > 1:
            self.page.text_centred(36, str(self.number), TIMES, 9)
            self.page.text(MARGIN_X, PAGE_H - 52, self.title, TIMES_I, 8.5)
            self.page.line(MARGIN_X, PAGE_H - 58, PAGE_W - MARGIN_X, PAGE_H - 58, 0.4)

    def need(self, amount: float) -> None:
        if self.y - amount < MARGIN_BOTTOM:
            self.new_page()

    def space(self, amount: float) -> None:
        self.y -= amount

    def para(self, text: str, font: str = TIMES, size: float = 10.5,
             indent: float = 0.0, leading: float = 14.0) -> None:
        if not text.strip():
            return
        for line in wrap(text, font, size, BODY - indent):
            self.need(leading)
            self.page.text(MARGIN_X + indent, self.y, line, font, size)
            self.y -= leading

    def heading(self, text: str, level: int) -> None:
        size = {1: 19.0, 2: 14.5, 3: 11.5}.get(level, 10.5)
        self.space(12 if level > 1 else 18)
        self.need(size + 14)
        if level == 1 and self.y < PAGE_H - MARGIN_TOP - 1:
            self.new_page()
        self.page.text(MARGIN_X, self.y, text, HELV_B if level < 3 else TIMES_B, size)
        self.y -= size + 4
        if level <= 2:
            self.page.line(MARGIN_X, self.y + 2, PAGE_W - MARGIN_X, self.y + 2, 0.6)
            self.y -= 6

    def code(self, lines: list[str]) -> None:
        size = 8.2
        self.space(4)
        for raw in lines:
            self.need(10.5)
            self.page.text(MARGIN_X + 10, self.y, raw[:96], COURIER, size)
            self.y -= 10.5
        self.space(4)

    def rule(self) -> None:
        self.space(8)
        self.need(10)
        self.page.line(MARGIN_X + 140, self.y, PAGE_W - MARGIN_X - 140, self.y, 0.5)
        self.space(10)

    def table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        cols = max(len(r) for r in rows)
        width = BODY / cols
        size = 8.6
        self.space(4)
        for index, row in enumerate(rows):
            wrapped = [wrap(cell, TIMES, size, width - 8) or [""] for cell in row]
            height = max(len(w) for w in wrapped) * 10.5
            self.need(height + 4)
            top = self.y
            for c, cell_lines in enumerate(wrapped):
                yy = top
                for line in cell_lines:
                    self.page.text(MARGIN_X + c * width + 3, yy, line,
                                   TIMES_B if index == 0 else TIMES, size)
                    yy -= 10.5
            self.y = top - height - 2
            if index == 0:
                self.page.line(MARGIN_X, self.y + 6, PAGE_W - MARGIN_X, self.y + 6, 0.5)
        self.space(6)


def render(markdown: str, title: str) -> Book:
    book = Book(title)
    lines = markdown.split("\n")
    i = 0
    pending_table: list[list[str]] = []

    def flush_table() -> None:
        nonlocal pending_table
        if pending_table:
            book.table(pending_table)
            pending_table = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        if line.startswith("```"):
            flush_table()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(clean(lines[i]))
                i += 1
            book.code(block)
            i += 1
            continue

        if line.startswith("|"):
            cells = [clean(c.strip()) for c in line.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):   # skip separator rows
                pending_table.append(cells)
            i += 1
            continue
        flush_table()

        if re.match(r"^\s*(---|\*\*\*)\s*$", line):
            book.rule()
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            book.heading(clean(line.lstrip("# ").strip()), level)
        elif line.startswith(">"):
            book.para(clean(line.lstrip("> ")), TIMES_I, 10.0, indent=24)
        elif re.match(r"^\s*[-*]\s+", line):
            book.para("- " + clean(re.sub(r"^\s*[-*]\s+", "", line)), TIMES, 10.5, indent=16)
        elif re.match(r"^\s*\d+\.\s+", line):
            book.para(clean(line.strip()), TIMES, 10.5, indent=16)
        elif not line.strip():
            book.space(5)
        else:
            book.para(clean(line))
        i += 1

    flush_table()
    return book


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "kryptos" / "THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md"))
    parser.add_argument("--out", default=str(ROOT / "transfer" / "THE_KRYPTOS_DECRYPTION_MANUSCRIPT.pdf"))
    parser.add_argument("--title", default="The Kryptos Decryption Manuscript")
    args = parser.parse_args()

    text = Path(args.source).read_text()
    book = render(text, args.title)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    book.doc.save(out)
    size = out.stat().st_size
    print(f"wrote {out.relative_to(ROOT)} — {book.number} pages, {size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
