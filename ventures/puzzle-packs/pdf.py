"""A minimal PDF writer — standard library only, no dependencies.

Enough of the PDF 1.4 spec to typeset a puzzle book: pages, the base-14 fonts
(which every reader has built in, so nothing needs embedding), text runs,
and lines. That is all a cryptogram book needs, and it means a sellable PDF
can be produced in CI without a browser or a print dialogue.

Coordinates are in points (72 per inch) with the origin at the bottom-left,
which is the PDF convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Base-14 fonts are guaranteed present in every conforming reader.
HELV = "Helvetica"
HELV_B = "Helvetica-Bold"
HELV_O = "Helvetica-Oblique"
TIMES = "Times-Roman"
TIMES_B = "Times-Bold"
TIMES_I = "Times-Italic"
COURIER = "Courier"
COURIER_B = "Courier-Bold"

FONTS = [HELV, HELV_B, HELV_O, TIMES, TIMES_B, TIMES_I, COURIER, COURIER_B]

# Average glyph widths (per 1000 units) for rough text measurement. Courier is
# monospaced at exactly 600; the proportional fonts use per-character tables
# for the ASCII range, which is all we typeset.
_HELV_W = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667,
    "'": 191, '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333,
    '.': 278, '/': 278, '0': 556, '1': 556, '2': 556, '3': 556, '4': 556,
    '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ':': 278, ';': 278,
    '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015, 'A': 667, 'B': 667,
    'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
    'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667,
    'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469,
    '_': 556, '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556,
    'f': 278, 'g': 556, 'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222,
    'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500,
    't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500,
    '{': 334, '|': 260, '}': 334, '~': 584,
}
# Times is narrower than Helvetica by roughly this ratio on mixed-case text.
_TIMES_SCALE = 0.92


def text_width(s: str, font: str, size: float) -> float:
    """Width of `s` in points. Approximate for Times, exact for Courier."""
    if font.startswith("Courier"):
        return len(s) * 600 / 1000 * size
    total = sum(_HELV_W.get(ch, 500 if ch in WINANSI else 556) for ch in s)
    if font.startswith("Times"):
        total *= _TIMES_SCALE
    if font.endswith("-Bold"):
        total *= 1.03
    return total / 1000 * size


# Typographic characters that are not Latin-1 but do exist in WinAnsiEncoding,
# which is the encoding declared on the fonts.
WINANSI = {
    "\u2013": 0x96, "\u2014": 0x97, "\u2018": 0x91, "\u2019": 0x92,
    "\u201c": 0x93, "\u201d": 0x94, "\u2022": 0x95, "\u2026": 0x85,
    "\u2020": 0x86, "\u2021": 0x87, "\u2030": 0x89, "\u20ac": 0x80,
    "\u2039": 0x8b, "\u203a": 0x9b, "\u0192": 0x83, "\u02c6": 0x88,
}
# Last-resort transliteration for anything with no WinAnsi slot at all.
ASCII_FALLBACK = {"\u2212": "-", "\u00a0": " ", "\u2032": "'", "\u2033": '"'}


def escape(s: str) -> str:
    """PDF string escaping with WinAnsi mapping for typographic characters."""
    out = []
    for ch in s:
        if ch in "()\\":
            out.append("\\" + ch)
        elif " " <= ch <= "~":
            out.append(ch)
        elif ch in WINANSI:
            out.append(f"\\{WINANSI[ch]:03o}")
        elif ch in ASCII_FALLBACK:
            out.append(ASCII_FALLBACK[ch])
        else:
            try:
                out.append(f"\\{ord(ch.encode('latin-1').decode('latin-1')):03o}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                out.append("?")
    return "".join(out)


@dataclass
class Page:
    width: float
    height: float
    ops: list[str] = field(default_factory=list)

    def text(self, x: float, y: float, s: str, font: str = HELV, size: float = 11,
             gray: float = 0.0) -> None:
        self.ops.append(
            f"BT {gray:.2f} g /{font.replace('-', '')} {size:.2f} Tf "
            f"1 0 0 1 {x:.2f} {y:.2f} Tm ({escape(s)}) Tj ET"
        )

    def text_centred(self, y: float, s: str, font: str = HELV, size: float = 11,
                     gray: float = 0.0) -> None:
        self.text((self.width - text_width(s, font, size)) / 2, y, s, font, size, gray)

    def text_right(self, x_right: float, y: float, s: str, font: str = HELV,
                   size: float = 11, gray: float = 0.0) -> None:
        self.text(x_right - text_width(s, font, size), y, s, font, size, gray)

    def line(self, x1: float, y1: float, x2: float, y2: float,
             width: float = 0.5, gray: float = 0.0) -> None:
        self.ops.append(
            f"{gray:.2f} G {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def content(self) -> bytes:
        return "\n".join(self.ops).encode("latin-1", "replace")


class Document:
    """Collects pages and serialises them into a valid PDF file."""

    def __init__(self, width: float = 612, height: float = 792,
                 title: str = "", author: str = "") -> None:
        self.width, self.height = width, height
        self.title, self.author = title, author
        self.pages: list[Page] = []

    def new_page(self) -> Page:
        page = Page(self.width, self.height)
        self.pages.append(page)
        return page

    def save(self, path) -> None:
        objects: list[bytes] = []

        def add(body: bytes) -> int:
            objects.append(body)
            return len(objects)          # object numbers are 1-based

        font_objs = {f: add(
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{f} "
            f"/Encoding /WinAnsiEncoding >>".encode()
        ) for f in FONTS}
        resources = "<< /Font << " + " ".join(
            f"/{f.replace('-', '')} {n} 0 R" for f, n in font_objs.items()
        ) + " >> >>"

        pages_obj = add(b"")             # reserved, patched once kids are known
        kids = []
        for page in self.pages:
            stream = page.content()
            content_obj = add(
                b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
                + stream + b"\nendstream"
            )
            page_obj = add(
                f"<< /Type /Page /Parent {pages_obj} 0 R "
                f"/MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Resources {resources} /Contents {content_obj} 0 R >>".encode()
            )
            kids.append(page_obj)

        objects[pages_obj - 1] = (
            "<< /Type /Pages /Count " + str(len(kids)) + " /Kids ["
            + " ".join(f"{k} 0 R" for k in kids) + "] >>"
        ).encode()

        info_obj = add(
            f"<< /Title ({escape(self.title)}) /Author ({escape(self.author)}) "
            f"/Producer (buttcrack puzzle-packs) >>".encode()
        )
        catalog_obj = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())

        buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, body in enumerate(objects, start=1):
            offsets.append(len(buf))
            buf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

        xref_pos = len(buf)
        buf += f"xref\n0 {len(objects) + 1}\n".encode()
        buf += b"0000000000 65535 f \n"
        for off in offsets[1:]:
            buf += f"{off:010d} 00000 n \n".encode()
        buf += (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R "
            f"/Info {info_obj} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
        ).encode()

        with open(path, "wb") as fh:
            fh.write(bytes(buf))


def wrap(text: str, font: str, size: float, max_width: float) -> list[str]:
    """Greedy word wrap to a pixel width."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_width(trial, font, size) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
