"""Typeset a cryptogram book straight to PDF — no browser, no dependencies.

    python3 ventures/puzzle-packs/build_pdf.py --puzzles 60 --seed 1

Produces a print-ready US Letter PDF: cover, instructions, graded puzzles with
answer blanks, and a solutions section. Upload it to Gumroad, attach it to a
Stripe payment link, or send it to Amazon KDP.

Reuses the puzzle generation in generate.py so the HTML and PDF editions of a
given seed contain exactly the same puzzles.
"""

from __future__ import annotations

import argparse
import random
from datetime import date
from pathlib import Path

from generate import QUOTES, caesar, difficulty_for, encrypt, hint_for, random_key
from pdf import COURIER, HELV, HELV_B, HELV_O, TIMES, TIMES_I, Document, text_width, wrap

PAGE_W, PAGE_H = 612.0, 792.0  # US Letter in points
MARGIN = 54.0  # 0.75 inch
CONTENT_W = PAGE_W - 2 * MARGIN
CELL_W = 15.0  # width of one answer blank
CELL_GAP = 1.5
WORD_GAP = 9.0


class Book:
    """Tracks the cursor and starts new pages when content runs off the bottom."""

    def __init__(self, doc: Document, title: str) -> None:
        self.doc = doc
        self.title = title
        self.page = None
        self.y = 0.0
        self.page_no = 0

    def new_page(self, numbered: bool = True) -> None:
        self.page = self.doc.new_page()
        self.page_no += 1
        self.y = PAGE_H - MARGIN
        if numbered and self.page_no > 1:
            self.page.text_centred(MARGIN - 26, str(self.page_no), HELV, 9, 0.55)
            self.page.text(MARGIN, PAGE_H - MARGIN + 14, self.title, HELV, 8, 0.65)

    def space(self, amount: float) -> None:
        self.y -= amount

    def need(self, amount: float) -> None:
        if self.y - amount < MARGIN + 18:
            self.new_page()

    def heading(self, s: str, size: float = 16) -> None:
        self.need(size + 14)
        self.page.text(MARGIN, self.y - size, s, HELV_B, size)
        self.y -= size + 12

    def para(self, s: str, font: str = TIMES, size: float = 10.5, leading: float = 15.0, gray: float = 0.15) -> None:
        for line in wrap(s, font, size, CONTENT_W):
            self.need(leading)
            self.page.text(MARGIN, self.y - size, line, font, size, gray)
            self.y -= leading
        self.y -= 4


def puzzle_height(ct: str) -> float:
    """Measure a puzzle block so it can be kept on one page."""
    rows = layout_rows(ct)
    return 20 + len(rows) * 30 + 26


def layout_rows(ct: str) -> list[list[str]]:
    """Break the ciphertext into rows of words that fit the content width."""
    rows, cur, cur_w = [], [], 0.0
    for word in ct.split(" "):
        w = len(word) * (CELL_W + CELL_GAP) + WORD_GAP
        if cur and cur_w + w > CONTENT_W:
            rows.append(cur)
            cur, cur_w = [], 0.0
        cur.append(word)
        cur_w += w
    if cur:
        rows.append(cur)
    return rows


def draw_puzzle(book: Book, num: int, ct: str, ct_author: str, kind: str, label: str, hint: str) -> None:
    book.need(puzzle_height(ct) + (14 if hint else 0))
    page = book.page

    page.text(MARGIN, book.y - 11, f"Puzzle {num}", HELV_B, 11)
    page.text_right(PAGE_W - MARGIN, book.y - 10, f"{kind} · {label}".upper(), HELV, 7.5, 0.5)
    book.y -= 26

    for row in layout_rows(ct):
        x = MARGIN
        for word in row:
            for ch in word:
                if ch.isalpha():
                    # The letter sits above a blank the solver writes in.
                    page.text(x + (CELL_W - text_width(ch, COURIER, 10)) / 2, book.y - 9, ch, COURIER, 10, 0.1)
                    page.line(x, book.y - 21, x + CELL_W, book.y - 21, 0.6, 0.55)
                else:
                    page.text(x + 3, book.y - 9, ch, COURIER, 10, 0.4)
                x += CELL_W + CELL_GAP
            x += WORD_GAP
        book.y -= 30

    page.text_right(PAGE_W - MARGIN, book.y - 2, f"- {ct_author}", COURIER, 9, 0.45)
    book.y -= 14
    if hint:
        page.text(MARGIN, book.y - 8, hint, HELV_O, 8.5, 0.4)
        book.y -= 14
    book.y -= 8
    page.line(MARGIN, book.y, PAGE_W - MARGIN, book.y, 0.4, 0.85)
    book.y -= 16


def build(puzzles: int, seed: int, title: str, out: Path) -> None:
    rng = random.Random(seed)
    pool = QUOTES[:]
    rng.shuffle(pool)
    if puzzles > len(pool):
        raise SystemExit(f"only {len(pool)} quotations available; ask for fewer puzzles")
    chosen = pool[:puzzles]

    doc = Document(PAGE_W, PAGE_H, title=title, author="buttcrack puzzle-packs")

    # ---- cover -------------------------------------------------------------
    cover = doc.new_page()
    cover.text_centred(PAGE_H - 250, title, HELV_B, 30)
    cover.line(MARGIN + 80, PAGE_H - 272, PAGE_W - MARGIN - 80, PAGE_H - 272, 1.2, 0.3)
    cover.text_centred(PAGE_H - 305, f"{puzzles} classic cryptograms", HELV, 14, 0.3)
    cover.text_centred(PAGE_H - 326, "graded easy to hard, with full solutions", HELV, 14, 0.3)
    cover.text_centred(150, f"Volume {seed}  ·  {date.today().strftime('%B %Y')}", HELV, 9, 0.55)

    book = Book(doc, title)

    # ---- instructions ------------------------------------------------------
    book.new_page(numbered=False)  # first real page; the cover is unnumbered
    book.heading("How to solve a cryptogram", 18)
    book.para(
        "Every puzzle in this book is a quotation in which each letter has been replaced "
        "by a different letter, used consistently throughout. If A becomes Q, it becomes Q "
        "everywhere. Your job is to work back to the original words. Spaces and word "
        "lengths are preserved, and those are your best clues."
    )
    steps = [
        ("Start with one-letter words.", "In English they are almost always A or I."),
        (
            "Attack the three-letter words.",
            "The most common by far is THE. If one "
            "three-letter pattern repeats, try it — that single guess often hands you the "
            "three most useful letters in the puzzle at once.",
        ),
        ("Look for doubled letters.", "Doubles at the end of a word are usually LL, SS, EE or OO."),
        (
            "Use word endings.",
            "ING, ED, TION and LY are everywhere, and each one you spot confirms several letters at a stroke.",
        ),
        (
            "Count frequencies.",
            "Across English the order runs roughly E T A O I N S H R D "
            "L U. The most repeated symbol in a long puzzle is very likely E.",
        ),
        ("Use pencil.", "Guesses that collapse three words later are part of the process."),
    ]
    for i, (bold, rest) in enumerate(steps, start=1):
        book.need(34)
        book.page.text(MARGIN, book.y - 10, f"{i}.", HELV_B, 10.5, 0.1)
        book.page.text(MARGIN + 16, book.y - 10, bold, HELV_B, 10.5, 0.1)
        x = MARGIN + 16 + text_width(bold, HELV_B, 10.5) + 4
        first_w = PAGE_W - MARGIN - x
        words, first_line = rest.split(), ""
        for w in words:
            if text_width(f"{first_line} {w}".strip(), TIMES, 10.5) <= first_w:
                first_line = f"{first_line} {w}".strip()
            else:
                break
        book.page.text(x, book.y - 10, first_line, TIMES, 10.5, 0.15)
        book.y -= 15
        remainder = rest[len(first_line) :].strip()
        if remainder:
            for line in wrap(remainder, TIMES, 10.5, CONTENT_W - 16):
                book.need(15)
                book.page.text(MARGIN + 16, book.y - 10, line, TIMES, 10.5, 0.15)
                book.y -= 15
        book.y -= 5

    book.space(6)
    book.para(
        "Puzzles marked EASY come with a few letters given. MEDIUM gives you one. HARD "
        "gives you nothing but the text. Every fifth puzzle is a rotation cipher, where the "
        "whole alphabet has been shifted by the same amount — crack one letter of those and "
        "you have cracked them all."
    )
    book.para("Solutions begin after the final puzzle. Good luck.", TIMES_I, 10.5)

    # ---- puzzles -----------------------------------------------------------
    book.new_page()
    solutions = []
    for i, (quote, author) in enumerate(chosen, start=1):
        label, hints = difficulty_for(i - 1, puzzles)
        if i % 5 == 0:
            shift = rng.randint(1, 25)
            ct, ct_author = caesar(quote, shift), caesar(author, shift)
            kind, answer_key = "Caesar shift", f"shift of {shift}"
            hint = "Hint: this one is a simple letter rotation." if hints else ""
        else:
            key = random_key(rng)
            ct, ct_author = encrypt(quote, key), encrypt(author, key)
            kind, answer_key = "Cryptogram", "substitution alphabet"
            pairs = hint_for(quote, ct, hints, rng)
            hint = f"Hint: {pairs}" if pairs and hints else ""

        draw_puzzle(book, i, ct, ct_author, kind, label, hint)
        solutions.append((i, quote, author, answer_key))

    # ---- solutions ---------------------------------------------------------
    book.new_page()
    book.heading("Solutions", 18)
    for i, quote, author, answer_key in solutions:
        text = f"{i}.  {quote.capitalize()} — {author}  ({answer_key})"
        lines = wrap(text, TIMES, 9.5, CONTENT_W)
        book.need(len(lines) * 13 + 4)
        for j, line in enumerate(lines):
            book.page.text(MARGIN + (0 if j == 0 else 14), book.y - 9, line, TIMES, 9.5, 0.15)
            book.y -= 13
        book.y -= 3

    # ---- back matter -------------------------------------------------------
    book.new_page()
    book.heading("About this book", 14)
    book.para(
        "These puzzles were generated with buttcrack, a free and open-source automatic "
        "cipher breaker — the same program that can solve them in under a second if you "
        "ever get truly stuck. Quotations are short fragments attributed to historical "
        "figures."
    )
    book.para(
        "If you enjoyed these, the generator that produced this book is free: you can make "
        "endless further volumes of it yourself at "
        "github.com/ahardkore/Buttcrack---Cipher-Breaker"
    )

    doc.save(out)
    print(f"wrote {out}  ({puzzles} puzzles, seed {seed}, {len(doc.pages)} pages, {out.stat().st_size // 1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--puzzles", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--title", default="The Cryptogram Collection")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or Path(__file__).with_name(f"cryptogram-pack-seed{args.seed}.pdf")
    build(args.puzzles, args.seed, args.title, out)


if __name__ == "__main__":
    main()
