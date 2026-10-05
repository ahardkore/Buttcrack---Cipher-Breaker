"""Shared, dependency-free Markdown book typesetting for the repository's manuscripts.

The canonical sources (``kryptos/KRYPTOS_SCHOLARLY_MANUSCRIPT.md`` and
``kryptos/THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md``) are hard-wrapped, richly
marked-up Markdown.  The earlier generators translated them far too literally:

* every *source* line became its own paragraph, so re-wrapped lines produced
  ragged single-word lines and broken sentences;
* emphasis markers were either dropped (PDF) or left as literal asterisks;
* lists, tables, quotes and code were typeset as raw text.

This module provides one parser shared by every book builder:

* :func:`parse_markdown` — a fence-aware block parser that merges hard-wrapped
  lines into real paragraphs and understands headings, thematic breaks, block
  quotes, nested lists, pipe tables, footnote definitions and fenced code.
  Code blocks are protected: a ``# comment`` inside a fence is never a heading.
* :func:`parse_inline` — a CommonMark-flavoured inline scanner producing styled
  runs: ``*italic*``, ``**bold**``, ``***both***``, ``_underscore_``,
  `` `code` ``, ``[links](…)`` and ``[^footnotes]``.

…plus a small book typesetter on top of the in-repo base-14 PDF writer
(``ventures/puzzle-packs/pdf.py``): justified paragraphs in Times with genuine
italic/bold faces, widow and orphan control, a table of contents with dot
leaders and page numbers, running heads, and real lists, quotes, tables and
code blocks.  See :func:`render_book_pdf`.

Everything here is standard library only, deterministic, and offline.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_VENTURES = _ROOT / "ventures" / "puzzle-packs"
if str(_VENTURES) not in sys.path:
    sys.path.insert(0, str(_VENTURES))

from pdf import (  # noqa: E402  (in-repo, dependency-free PDF writer)
    COURIER,
    COURIER_B,
    HELV_B,
    TIMES,
    TIMES_B,
    TIMES_BI,
    TIMES_I,
    Document,
    text_width,
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Run:
    """A styled span of inline text.  ``text == "\\n"`` encodes a hard break."""

    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None  # URL for [text](url) / ![alt](url)
    fn: str | None = None  # footnote key for [^key]


@dataclass
class Heading:
    level: int
    runs: list


@dataclass
class Para:
    runs: list


@dataclass
class Hr:
    pass


@dataclass
class Quote:
    blocks: list


@dataclass
class ListBlock:
    ordered: bool
    start: int
    items: list  # each item: list of blocks (first is usually a Para)


@dataclass
class CodeBlock:
    lines: list


@dataclass
class Table:
    rows: list  # rows[0] is the header row
    aligns: list  # per column: "l" | "c" | "r"


@dataclass
class FootnoteDef:
    key: str
    runs: list


# ---------------------------------------------------------------------------
# Block parsing
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})[\t ]*([^`]*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_HR = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")
_LIST = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+)(.*)$")
_QUOTE = re.compile(r"^ {0,3}> ?(.*)$")
_FOOTDEF = re.compile(r"^ {0,3}\[\^([^\]\s]+)\]:\s*(.*)$")


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _list_marker(line: str):
    m = _LIST.match(line)
    if m and m.group(4).strip():
        return m
    return None


def _is_block_start(line: str) -> bool:
    """True when `line` interrupts a paragraph (any construct that starts a block)."""
    if _FENCE.match(line) or _HEADING.match(line) or _HR.match(line):
        return True
    if _QUOTE.match(line) or _FOOTDEF.match(line):
        return True
    if line.lstrip(" ").startswith("|"):
        return True
    return _list_marker(line) is not None


def _split_table_row(row: str) -> list:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def _separator_aligns(cells: list):
    aligns = []
    for c in cells:
        if not re.fullmatch(r":?(-+):?", c):
            return None
        left, right = c.startswith(":"), c.endswith(":")
        aligns.append("c" if left and right else "r" if right else "l")
    return aligns


def _parse_list(lines: list, i: int, n: int):
    """Parse a list starting at lines[i]; returns (ListBlock, next_index).

    Nested list lines stay raw (indented, marker intact) inside the parent
    item's text, so the recursive ``parse_blocks`` call re-detects them with
    their own base indentation.  Item continuations work indented *and* lazy
    (unindented), matching how GitHub renders these manuscripts.
    """
    first = _LIST.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2) not in "-*+"
    start = int(re.match(r"\d+", first.group(2)).group()) if ordered else 1
    items: list[list[str]] = []
    cur: list[str] | None = None
    while i < n:
        line = lines[i]
        if not line.strip():
            # A blank line ends the list unless what follows still belongs to
            # it (another marker, or content indented past the list base).
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if (
                j < n
                and _indent_of(lines[j]) > base
                and not _HEADING.match(lines[j])
                and not _FENCE.match(lines[j])
                and not _HR.match(lines[j])
            ):
                if cur is not None:
                    cur.append("")
                i = j
                continue
            break
        m = _LIST.match(line)
        if m:
            ind = len(m.group(1))
            if ind > base:
                if cur is None:
                    cur = []
                cur.append(line)  # raw: nested list, re-parsed recursively
                i += 1
                continue
            if ind < base or (m.group(2) in "-*+") == ordered:
                break  # dedent, or bullet/ordered switch ends this list
            if not m.group(4).strip() and not (ind == base and cur is None):
                # empty item: keep it as an (empty) item to stay faithful
                if cur is not None:
                    items.append(cur)
                cur = [""]
                i += 1
                continue
            if cur is not None:
                items.append(cur)
            cur = [m.group(4).rstrip()]
            i += 1
            continue
        ind = _indent_of(line)
        if cur is not None and ind >= base:
            cur.append(line.strip())
            i += 1
            continue
        if cur is not None and not _is_block_start(line):
            cur.append(line.strip())  # lazy continuation
            i += 1
            continue
        break
    if cur is not None:
        items.append(cur)
    item_blocks = [parse_blocks("\n".join(item)) for item in items if any(x.strip() for x in item)]
    return ListBlock(ordered, start, item_blocks), i


def parse_blocks(text: str) -> list:
    """Parse Markdown text (already stripped of any container prefix) into blocks."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        m = _FENCE.match(line)
        if m:
            fence_char, fence_len = m.group(2)[0], len(m.group(2))
            i += 1
            body = []
            while i < n:
                close = _FENCE.match(lines[i])
                if close and close.group(2)[0] == fence_char and len(close.group(2)) >= fence_len:
                    break
                body.append(lines[i].rstrip())
                i += 1
            i += 1  # skip the closing fence (or run off the end)
            blocks.append(CodeBlock(body))
            continue

        m = _HEADING.match(line)
        if m:
            blocks.append(Heading(len(m.group(1)), parse_inline(m.group(2))))
            i += 1
            continue

        if _HR.match(line):
            blocks.append(Hr())
            i += 1
            continue

        m = _FOOTDEF.match(line)
        if m:
            key, body = m.group(1), m.group(2)
            i += 1
            while i < n and lines[i].strip() and _indent_of(lines[i]) >= 4:
                body += " " + lines[i].strip()
                i += 1
            blocks.append(FootnoteDef(key, parse_inline(body)))
            continue

        m = _QUOTE.match(line)
        if m:
            inner = [m.group(1)]
            i += 1
            while i < n:
                qm = _QUOTE.match(lines[i])
                if qm is None:
                    break
                inner.append(qm.group(1))
                i += 1
            blocks.append(Quote(parse_blocks("\n".join(inner))))
            continue

        if line.lstrip(" ").startswith("|"):
            raw = []
            while i < n and lines[i].strip() and lines[i].lstrip(" ").startswith("|"):
                raw.append(lines[i].strip())
                i += 1
            rows = [_split_table_row(r) for r in raw]
            aligns = None
            if len(rows) > 1:
                maybe = _separator_aligns(rows[1])
                if maybe is not None and len(maybe) == len(rows[0]):
                    aligns = maybe
                    del rows[1]
            if rows:
                ncols = max(len(r) for r in rows)
                rows = [r + [""] * (ncols - len(r)) for r in rows]
                blocks.append(Table(rows, aligns or ["l"] * ncols))
            continue

        if _list_marker(line):
            block, i = _parse_list(lines, i, n)
            blocks.append(block)
            continue

        # Paragraph: merge hard-wrapped source lines into one paragraph,
        # preserving two-space/backslash hard breaks as explicit markers.
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            buf.append(lines[i])
            i += 1
        parts: list[str] = []
        prev_hard = False
        for k, raw in enumerate(buf):
            esc_break = raw.endswith("\\")
            hard = raw.endswith("  ") or raw.endswith("\t") or esc_break
            body_text = raw[:-1].rstrip() if esc_break else raw.rstrip(" \t")
            if k:
                parts.append("\n" if prev_hard else " ")
            parts.append(body_text)
            prev_hard = hard
        blocks.append(Para(parse_inline("".join(parts))))
    return blocks


def parse_markdown(text: str) -> list:
    return parse_blocks(text)


# ---------------------------------------------------------------------------
# Inline parsing
# ---------------------------------------------------------------------------


def _can_open(s: str, i: int, length: int, underscore: bool) -> bool:
    nxt = s[i + length] if i + length < len(s) else ""
    if not nxt or nxt.isspace():
        return False
    if underscore:
        prev = s[i - 1] if i > 0 else ""
        if prev.isalnum():  # intraword underscores are literal (file_name.py)
            return False
    return True


def _can_close(s: str, j: int, length: int, underscore: bool) -> bool:
    prev = s[j - 1] if j > 0 else ""
    if not prev or prev.isspace():
        return False
    if underscore:
        nxt = s[j + length] if j + length < len(s) else ""
        if nxt.isalnum():
            return False
    return True


def _find_close(s: str, ch: str, start: int, length: int, underscore: bool) -> int:
    j = start
    while True:
        j = s.find(ch * length, j)
        if j == -1:
            return -1
        if _can_close(s, j, length, underscore):
            return j
        j += length


def _inline_scan(s: str, bold: bool = False, italic: bool = False, link: str | None = None) -> list:
    runs: list = []
    buf: list[str] = []

    def take_plain() -> None:
        if buf:
            runs.append(Run("".join(buf), bold, italic, link=link))
            buf.clear()

    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] in "*_`[]()!\\":
            buf.append(s[i + 1])
            i += 2
            continue
        if ch == "<":
            br = re.match(r"<br\s*/?>", s[i:], re.I)
            if br:  # raw HTML line break -> hard break
                take_plain()
                runs.append(Run("\n"))
                i += br.end()
                continue
        if ch == "`":
            j = s.find("`", i + 1)
            if j != -1:
                take_plain()
                runs.append(Run(s[i + 1 : j].strip() or " ", code=True, link=link))
                i = j + 1
                continue
        if ch == "[":
            fm = re.match(r"\[\^([^\]\s]+)\]", s[i:])
            if fm:  # footnote reference
                take_plain()
                key = fm.group(1)
                runs.append(Run(f"[{key}]", bold, italic, link=link, fn=key))
                i += fm.end()
                continue
            lm = re.match(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", s[i:])
            if lm:  # link, or image degraded to its alt text
                take_plain()
                runs.extend(_inline_scan(lm.group(1), bold, italic, lm.group(2)))
                i += lm.end()
                continue
        if ch == "*" and s.startswith("***", i):
            j = _find_close(s, "*", i + 3, 3, False)
            if j != -1 and _can_open(s, i, 3, False):
                take_plain()
                runs.extend(_inline_scan(s[i + 3 : j], True, True, link))
                i = j + 3
                continue
        if s.startswith("**", i) and ch in "*_":
            j = _find_close(s, ch, i + 2, 2, ch == "_")
            if j != -1 and _can_open(s, i, 2, ch == "_"):
                take_plain()
                runs.extend(_inline_scan(s[i + 2 : j], True, italic, link))
                i = j + 2
                continue
        if ch in "*_":
            j = _find_close(s, ch, i + 1, 1, ch == "_")
            if j != -1 and j > i + 1 and _can_open(s, i, 1, ch == "_"):
                take_plain()
                runs.extend(_inline_scan(s[i + 1 : j], bold, True, link))
                i = j + 1
                continue
        buf.append(ch)
        i += 1
    take_plain()
    return runs


def parse_inline(text: str) -> list:
    """Parse inline Markdown into styled runs; "\\n" runs mark hard line breaks."""
    runs: list = []
    for k, segment in enumerate(text.split("\n")):
        if k:
            runs.append(Run("\n"))
        runs.extend(_inline_scan(segment))
    return [r for r in runs if r.text]


def runs_plain_text(runs: list) -> str:
    return "".join(r.text for r in runs if r.text != "\n")


# ---------------------------------------------------------------------------
# PDF typesetting
# ---------------------------------------------------------------------------

# Characters the base-14 WinAnsi fonts cannot encode, with readable stand-ins
# (an em dash silently dropped by a PDF would change the meaning of a sentence).
PDF_TRANSLITERATE = {
    "→": "->",
    "←": "<-",
    "↔": "<->",
    "⟶": "->",
    "⇒": "=>",
    "−": "-",
    "≈": "~",
    "≥": ">=",
    "≤": "<=",
    "≠": "!=",
    "≡": "==",
    "×": "x",
    "⁴": "^4",
    "⁵": "^5",
    "³": "^3",
    "²": "^2",
    "½": "1/2",
    "′": "'",
    "″": '"',
    "∘": " o ",
    "✅": "[OK]",
    "☑": "[x]",
    "✓": "[ok]",
    "⚠": "[!]",
    "❗": "[!]",
    "𝑘": "k",
    "𝑁": "N",
    "\ufe0f": "",  # emoji variation selector
    "─": "-",
    "│": "|",
    "┌": "+",
    "┐": "+",
    "└": "+",
    "┘": "+",
    "├": "+",
    "┤": "+",
    "┬": "+",
    "┴": "+",
    "┼": "+",
    "░": ".",
    "▒": ".",
    "▓": "#",
    "█": "#",
}


def pdf_sanitize(text: str) -> str:
    """Map characters the PDF writer cannot encode onto readable stand-ins."""
    out = []
    for ch in text:
        if ch in PDF_TRANSLITERATE:
            out.append(PDF_TRANSLITERATE[ch])
        elif ch == "\t":
            out.append("    ")
        elif ch == "\n":
            out.append(ch)  # hard line break (from <br> or two-space endings)
        elif ord(ch) < 32:
            out.append("")
        elif ord(ch) <= 0xFF or ch in "–—‘’“”…•†‡€‰‹›":
            out.append(ch)  # latin-1 / WinAnsi: real typography survives
        else:
            out.append("")  # unmapped (rare emoji, foreign scripts): drop
    return "".join(out)


@dataclass
class _Word:
    text: str
    font: str
    size: float
    width: float
    glued: bool = False  # continuation of a hard-split word: no space before it


class BookPDF:
    """A flowing, professionally typeset book built on the in-repo PDF writer."""

    def __init__(
        self,
        page_w: float = 432.0,
        page_h: float = 648.0,
        margin_l: float = 54.0,
        margin_r: float = 54.0,
        margin_t: float = 50.0,
        margin_b: float = 56.0,
        title: str = "",
        author: str = "",
        body_size: float = 10.5,
        leading: float | None = None,
        para_indent: float = 14.0,
        para_space: float = 3.2,
        justify: bool = True,
        running_head: bool = True,
        sanitize=pdf_sanitize,
    ) -> None:
        self.doc = Document(page_w, page_h, title, author)
        self.page_w, self.page_h = page_w, page_h
        self.margin_l, self.margin_r = margin_l, margin_r
        self.margin_t, self.margin_b = margin_t, margin_b
        self.title, self.author = title, author
        self.body_size = body_size
        self.leading = leading or body_size * 1.38
        self.para_indent = para_indent
        self.para_space = para_space
        self.justify = justify
        self.running_head = running_head
        self.sanitize = sanitize
        self._space_w = text_width(" ", TIMES, body_size)
        self.page = None
        self.y = 0.0
        self.number = 0
        self.page_has_content = False
        self.toc_entries: list[tuple[int, str, int]] = []  # (level, title, page)
        self._suppress_indent = True
        self._new_page()

    # -- page machinery ----------------------------------------------------

    @property
    def body_width(self) -> float:
        return self.page_w - self.margin_l - self.margin_r

    def _new_page(self, chapter: bool = False) -> None:
        self.number += 1
        self.page = self.doc.new_page()
        self.y = self.page_h - self.margin_t
        self.page_has_content = False
        if self.number > 1:
            self.page.text_centred(26, str(self.number), TIMES, 8.5, 0.25)
            if self.running_head and not chapter and self.title:
                self.page.text(self.margin_l, self.page_h - 32, self.title, TIMES_I, 8.0, 0.35)
                self.page.line(
                    self.margin_l, self.page_h - 38, self.page_w - self.margin_r, self.page_h - 38, 0.4, 0.6
                )

    def _need(self, amount: float) -> None:
        if self.y - amount < self.margin_b:
            self._new_page()

    # -- inline machinery --------------------------------------------------

    def _font_for(self, run: Run, base_italic: bool = False) -> str:
        if run.code:
            return COURIER_B if run.bold else COURIER
        bold = run.bold
        italic = run.italic or base_italic
        return {
            (False, False): TIMES,
            (True, False): TIMES_B,
            (False, True): TIMES_I,
            (True, True): TIMES_BI,
        }[(bold, italic)]

    def _words(self, runs: list, size: float, base_italic: bool = False) -> list:
        """Convert runs to a word stream; ``None`` marks a hard line break."""
        words: list = []
        for run in runs:
            if run.text == "\n":
                words.append(None)
                continue
            text = self.sanitize(run.text)
            if (
                run.link
                and run.link != text
                and run.link.startswith(("http://", "https://"))
            ):
                # Print editions must show their sources: keep the link text,
                # then set the URL itself in parentheses, in smaller type.
                for w in text.split():
                    words.append(_Word(w, self._font_for(run, base_italic), size, 0.0))
                url_words = run.link.split()
                for k, w in enumerate(url_words):
                    prefix = "(" if k == 0 else ""
                    suffix = ")" if k == len(url_words) - 1 else ""
                    words.append(_Word(prefix + w + suffix, TIMES, size * 0.85, 0.0))
                continue
            font = self._font_for(run, base_italic)
            fsize = size * 0.95 if run.code else size
            for w in text.split():
                words.append(_Word(w, font, fsize, 0.0))
        for w in words:
            if w is not None and w.width == 0.0:
                w.width = text_width(w.text, w.font, w.size)
        return words

    def _fit_word(self, word: _Word, width: float) -> list:
        """Hard-split a word (a URL, a hash, a path) that exceeds a full line."""
        if word.width <= width:
            return [word]
        out, cur, cur_w = [], "", 0.0
        for ch in word.text:
            ch_w = text_width(ch, word.font, word.size)
            if cur and cur_w + ch_w > width:
                out.append(_Word(cur, word.font, word.size, cur_w))
                cur, cur_w = ch, ch_w
            else:
                cur, cur_w = cur + ch, cur_w + ch_w
        if cur:
            out.append(_Word(cur, word.font, word.size, text_width(cur, word.font, word.size)))
        for piece in out[1:]:
            piece.glued = True
        return out or [word]

    def _wrap(self, words: list, first_width: float, rest_width: float, space_w: float | None = None) -> list:
        space_w = self._space_w if space_w is None else space_w
        lines: list[list[_Word]] = []
        cur: list[_Word] = []
        cur_w = 0.0
        width = first_width
        for w in words:
            if w is None:  # hard break
                lines.append(cur)
                cur, cur_w, width = [], 0.0, rest_width
                continue
            for piece in self._fit_word(w, width):
                joined = piece.glued and cur  # glued to the previous piece
                add = piece.width if (not cur or joined) else space_w + piece.width
                if cur and cur_w + add > width:
                    lines.append(cur)
                    cur, cur_w, width = [piece], piece.width, rest_width
                else:
                    cur.append(piece)
                    cur_w += add
        lines.append(cur)
        return lines

    def _draw_words(
        self, x: float, y: float, words: list, max_w: float, justify: bool, last: bool, space_w: float | None = None
    ) -> None:
        if not words:
            return
        space_w = self._space_w if space_w is None else space_w
        widths = [w.width for w in words]
        joins = [i for i in range(1, len(words)) if not words[i].glued]
        natural = sum(widths) + space_w * len(joins)
        gap = space_w
        if justify and not last and joins and natural <= max_w:
            extra = max_w - natural
            # Only justify when the extra inter-word space stays reasonable;
            # very loose lines keep a ragged edge instead.
            if extra <= space_w * 0.85 * len(joins):
                gap = space_w + extra / len(joins)
        xx = x
        for k, (w, ww) in enumerate(zip(words, widths)):
            if k > 0 and not w.glued:
                xx += gap
            self.page.text(xx, y, w.text, w.font, w.size)
            xx += ww
        self.page_has_content = True

    # -- block renderers ---------------------------------------------------

    def _fix_runt(self, lines: list) -> list:
        """Avoid a lone short word on a paragraph's final line.

        Classic typesetter's runt control: pull the previous line's last word
        down so the paragraph ends with at least two words.
        """
        if len(lines) < 2:
            return lines
        last = lines[-1]
        if len(last) != 1 or not last or last[0].glued:
            return lines
        word = last[0]
        if word.width > 0.22 * self.body_width:  # a long final word stands fine
            return lines
        prev = lines[-2]
        if len(prev) < 3 or prev[-1].glued:
            return lines
        moved = prev.pop()
        lines[-1] = [moved, word]
        return lines

    def para(
        self,
        runs: list,
        size: float | None = None,
        leading: float | None = None,
        left: float = 0.0,
        first_indent: float | None = None,
        justify: bool | None = None,
        space_after: float | None = None,
        base_italic: bool = False,
        keep: bool = True,
    ) -> None:
        if not runs:
            return
        size = size or self.body_size
        leading = leading or self.leading
        max_w = self.body_width - left
        indent = self.para_indent
        if first_indent is not None:
            indent = first_indent
        elif self._suppress_indent:
            indent = 0.0
        words = self._words(runs, size, base_italic)
        lines = self._wrap(words, max_w - indent, max_w)
        lines = self._fix_runt(lines)
        justify = self.justify if justify is None else justify
        if keep and len(lines) >= 2 and self.margin_b <= self.y - leading < self.margin_b + leading:
            # Orphan control: never strand a single line at the foot of a page.
            self._new_page()
        for idx, ln in enumerate(lines):
            self._need(leading)
            if keep and idx >= 1 and idx + 2 == len(lines) and self.y - 2 * leading < self.margin_b:
                # Widow control: keep a paragraph's final two lines together.
                self._new_page()
            x0 = self.margin_l + left + (indent if idx == 0 else 0.0)
            line_max = max_w - (indent if idx == 0 else 0.0)
            self._draw_words(x0, self.y, ln, line_max, justify, last=(idx == len(lines) - 1))
            self.y -= leading
        self.y -= self.para_space if space_after is None else space_after
        self._suppress_indent = False

    def heading(self, level: int, runs: list, toc_filter=None) -> None:
        level = min(level, 6)
        text = self.sanitize(runs_plain_text(runs))
        size, font, before, after = {
            1: (19.0, HELV_B, 0.0, 20.0),
            2: (13.5, HELV_B, 14.0, 7.0),
            3: (11.8, TIMES_B, 11.0, 5.0),
            4: (10.6, TIMES_B, 9.0, 4.0),
            5: (10.2, TIMES_BI, 8.0, 4.0),
            6: (10.0, TIMES_B, 8.0, 3.5),
        }[level]
        if level == 1:
            if self.page_has_content:
                self._new_page(chapter=True)
            if toc_filter is not None and toc_filter(1, text):
                self.toc_entries.append((1, text, self.number))
            wrapped = self._wrap(
                [_Word(t, font, size, text_width(t, font, size)) for t in text.split()],
                self.body_width,
                self.body_width,
                text_width(" ", font, size),
            )
            wrapped = self._fix_runt(wrapped)
            self._need(len(wrapped) * (size * 1.25) + after + 2.2 * self.leading)
            for ln in wrapped:
                line = " ".join(w.text for w in ln)
                self.page.text_centred(self.y, line, font, size)
                self.page_has_content = True
                self.y -= size * 1.25
            self.y -= after
            self._suppress_indent = True
            return
        self.y -= before
        # Keep headings with the first lines of whatever follows.
        self._need(size + after + 2.5 * self.leading)
        wrapped = self._wrap(
            [_Word(t, font, size, text_width(t, font, size)) for t in text.split()],
            self.body_width,
            self.body_width,
            text_width(" ", font, size),
        )
        wrapped = self._fix_runt(wrapped)
        for ln in wrapped:
            self.page.text(self.margin_l, self.y, " ".join(w.text for w in ln), font, size)
            self.page_has_content = True
            self.y -= size * 1.22
        if toc_filter is not None and toc_filter(level, text):
            self.toc_entries.append((level, text, self.number))
        self.y -= size * 0.35 + after
        if level == 2:
            self.page.line(self.margin_l, self.y + 1, self.page_w - self.margin_r, self.y + 1, 0.5, 0.45)
        self.y -= after
        self._suppress_indent = True

    def hr(self) -> None:
        self._need(24)
        self.y -= 7
        x0 = self.margin_l + (self.body_width - 110) / 2
        self.page.line(x0, self.y, x0 + 110, self.y, 0.6, 0.5)
        self.page_has_content = True
        self.y -= 13
        self._suppress_indent = True

    def code(self, lines: list) -> None:
        size, lead, pad = 8.3, 11.0, 6.0
        max_w = self.body_width - 2 * pad
        space_w = text_width(" ", COURIER, size)
        out: list[str] = []
        for ln in lines:
            ln = self.sanitize(ln.replace("\t", "    "))
            if not ln.strip():
                out.append("")
                continue
            words = [_Word(t, COURIER, size, text_width(t, COURIER, size)) for t in ln.split(" ")]
            wrapped = self._wrap(words, max_w, max_w, space_w)
            out.extend(" ".join(w.text for w in wl) for wl in wrapped)
        n = len(out)
        self.y -= 3
        idx = 0
        while idx < n:
            avail = self.y - self.margin_b
            take = int(avail // lead)
            if take < 2 and n - idx >= 2:
                self._new_page()
                continue
            take = max(1, min(take, n - idx))
            chunk = out[idx : idx + take]
            top = self.y + size * 0.85
            h = (len(chunk) - 1) * lead + 2 * pad
            self.page.rect(self.margin_l, top - h, self.body_width, h, fill_gray=0.945)
            self.page.line(self.margin_l, top, self.margin_l, top - h, 1.1, 0.62)
            for ln in chunk:
                if ln:
                    self.page.text(self.margin_l + pad, self.y, ln, COURIER, size)
                self.y -= lead
            self.page_has_content = True
            self.y -= pad - 3
            idx += take
        self.y -= 3
        self._suppress_indent = True

    def quote(self, blocks: list) -> None:
        left = 20.0
        self._suppress_indent = True
        seg_top = self.y + 3
        self.y -= 3

        def rule(page, y0, y1) -> None:
            if page is not None and y1 < y0 - 2:
                page.line(self.margin_l + 5, y0, self.margin_l + 5, y1, 0.9, 0.55)

        for b in blocks:
            before_page = self.page
            if isinstance(b, Para):
                self.para(
                    b.runs,
                    size=self.body_size * 0.97,
                    leading=self.leading * 0.97,
                    left=left,
                    first_indent=0.0,
                    space_after=2.5,
                    base_italic=True,
                )
            elif isinstance(b, ListBlock):
                self.list_block(b, depth=0, left=left, italic=True)
            elif isinstance(b, Heading):
                self.heading(b.level, b.runs)
            else:
                self._render_block(b)
            if self.page is not before_page:
                rule(before_page, seg_top, self.margin_b + 12)
                seg_top = self.page_h - self.margin_t + 5
        rule(self.page, seg_top, max(self.margin_b + 12, self.y + 5))
        self.y -= 5
        self._suppress_indent = False

    def list_block(self, lst: ListBlock, depth: int = 0, left: float = 0.0, italic: bool = False) -> None:
        base_x = self.margin_l + left + depth * 15.0
        hang = 15.0
        for k, item in enumerate(lst.items):
            marker = f"{lst.start + k}." if lst.ordered else "•"
            mfont = TIMES if lst.ordered else TIMES_B
            first_para = item[0] if item and isinstance(item[0], Para) else None
            self._need(self.leading)
            if first_para is not None:
                self.page.text(base_x, self.y, marker, mfont, self.body_size)
                self.page_has_content = True
                self.para(
                    first_para.runs,
                    left=base_x - self.margin_l + hang,
                    first_indent=0.0,
                    space_after=1.2,
                    base_italic=italic,
                    keep=False,
                )
                rest = item[1:]
            else:
                rest = item
            for b in rest:
                if isinstance(b, ListBlock):
                    self.list_block(b, depth + 1, left=base_x - self.margin_l + 4.0, italic=italic)
                elif isinstance(b, Para):
                    self.para(
                        b.runs,
                        left=base_x - self.margin_l + hang,
                        first_indent=0.0,
                        space_after=1.2,
                        base_italic=italic,
                        keep=False,
                    )
                else:
                    self._render_block(b)
            self.y -= 1.5
        self._suppress_indent = True

    def table(self, tbl: Table) -> None:
        size, lead = 8.3, 10.6
        pad_x, pad_y = 4.0, 3.2
        avail = self.body_width
        ncols = len(tbl.rows[0])
        # Keep hard breaks (<br>) inside cells so they stack as cell lines.
        cells = [
            [self.sanitize("".join(r.text for r in parse_inline(c))) for c in row] for row in tbl.rows
        ]

        # Column widths: natural content widths, scaled to fill the measure,
        # never below each column's longest single word.
        nat = [
            max(text_width(cells[r][c], TIMES_B if r == 0 else TIMES, size) for r in range(len(cells)))
            for c in range(ncols)
        ]
        minw = [
            max(
                [
                    max(text_width(w, TIMES, size), text_width(w, TIMES_B, size))
                    for row_cells in cells
                    for w in row_cells[c].split()
                ]
                or [0.0]
            )
            + 2 * pad_x
            for c in range(ncols)
        ]
        budget = avail - ncols * 2 * pad_x
        total = sum(nat) or 1.0
        if total <= budget:
            scale = budget / total
            widths = [w * scale for w in nat]
        else:
            widths = [w * budget / total for w in nat]
            for _ in range(10):
                fixed = [c for c in range(ncols) if widths[c] <= minw[c]]
                free = [c for c in range(ncols) if c not in fixed]
                if not free or not fixed:
                    break
                surplus = sum(widths[c] - minw[c] for c in fixed)
                deficit = sum(max(0.0, minw[c] - widths[c]) for c in free)
                if surplus <= 0 or deficit <= 0:
                    break
                take = min(surplus, deficit)
                for c in fixed:
                    widths[c] -= take * (widths[c] - minw[c]) / surplus
                for c in free:
                    widths[c] += take / len(free)
        widths = [max(w, minw[c]) for c, w in enumerate(widths)]
        if sum(widths) + ncols * 2 * pad_x > avail:  # last resort: uniform squeeze
            widths = [(avail - ncols * 2 * pad_x) / max(1, ncols)] * ncols

        def row_height(cells_row: list) -> float:
            heights = []
            for c in range(ncols):
                segs = [
                    [_Word(t, TIMES, size, text_width(t, TIMES, size)) for t in part.split()]
                    for part in cells_row[c].split("\n")
                ]
                space_w = text_width(" ", TIMES, size)
                heights.append(
                    sum(len(self._wrap(words, widths[c], widths[c], space_w)) for words in segs)
                )
            return (max(heights) - 1) * lead + 2 * pad_y

        def draw_row(cells_row: list, header: bool) -> None:
            font = TIMES_B if header else TIMES
            space_w = text_width(" ", font, size)
            wrapped = []
            for c in range(ncols):
                segs = [
                    [_Word(t, font, size, text_width(t, font, size)) for t in part.split()]
                    for part in cells_row[c].split("\n")
                ]
                lines_c: list = []
                for words in segs:
                    lines_c.extend(self._wrap(words, widths[c], widths[c], space_w))
                wrapped.append(lines_c)
            nlines = max(len(w) for w in wrapped)
            top = self.y
            xx = self.margin_l
            for c in range(ncols):
                for k, ln in enumerate(wrapped[c]):
                    joins = [i for i in range(1, len(ln)) if not ln[i].glued]
                    lw = sum(w.width for w in ln) + space_w * len(joins)
                    inner = widths[c]
                    if tbl.aligns[c] == "r":
                        x = xx + pad_x + (inner - lw)
                    elif tbl.aligns[c] == "c":
                        x = xx + pad_x + (inner - lw) / 2
                    else:
                        x = xx + pad_x
                    self._draw_words(
                        x, top - k * lead, ln, inner + 2 * pad_x, justify=False, last=True, space_w=space_w
                    )
                xx += widths[c] + 2 * pad_x
            bottom = top - (nlines - 1) * lead - pad_y
            if header:
                self.page.line(self.margin_l, top + pad_y, self.margin_l + avail, top + pad_y, 0.7, 0.2)
                self.page.line(self.margin_l, bottom - 2, self.margin_l + avail, bottom - 2, 0.5, 0.35)
            else:
                self.page.line(self.margin_l, bottom - 2, self.margin_l + avail, bottom - 2, 0.35, 0.72)
            self.page_has_content = True
            self.y = bottom - pad_y - 2

        self.y -= 2
        # Keep the header row with at least the first body row.
        self._need(row_height(cells[0]) + row_height(cells[1] if len(cells) > 1 else cells[0]) + 3 * pad_y)
        draw_row(cells[0], header=True)
        for row in cells[1:]:
            self._need(row_height(row) + pad_y)
            draw_row(row, header=False)
        self.y -= 4
        self._suppress_indent = True

    # -- dispatch ----------------------------------------------------------

    def _render_block(self, b, toc_filter=None) -> None:
        if isinstance(b, Para):
            self.para(b.runs)
        elif isinstance(b, Heading):
            self.heading(b.level, b.runs, toc_filter=toc_filter)
        elif isinstance(b, Hr):
            self.hr()
        elif isinstance(b, Quote):
            self.quote(b.blocks)
        elif isinstance(b, ListBlock):
            self.list_block(b)
        elif isinstance(b, CodeBlock):
            self.code(b.lines)
        elif isinstance(b, Table):
            self.table(b)
        elif isinstance(b, FootnoteDef):
            self.para(b.runs, left=14, first_indent=0)

    def render(self, blocks: list, toc_filter=None) -> None:
        for b in blocks:
            self._render_block(b, toc_filter=toc_filter)

    # -- table of contents -------------------------------------------------

    def toc(self, entries: list, heading_text: str = "Contents") -> None:
        if self.page_has_content:
            self._new_page(chapter=True)
        self.page.text(self.margin_l, self.y, heading_text, HELV_B, 16)
        self.page_has_content = True
        self.y -= 24
        level1_seen = False
        lead = 14.8
        for level, title, page in entries:
            size = 10.3 if level == 1 else 9.6
            font = TIMES_B if level == 1 else TIMES
            indent = 0.0 if level == 1 else 16.0
            if level == 1 and level1_seen:
                self.y -= 5
            level1_seen = level1_seen or level == 1
            self._need(2 * lead)
            avail = self.body_width - indent - 34
            space_w = text_width(" ", font, size)
            words = [_Word(t, font, size, text_width(t, font, size)) for t in title.split()]
            lines = self._wrap(words, avail, avail, space_w)
            for k, ln in enumerate(lines):
                self._need(lead)
                x = self.margin_l + indent
                self._draw_words(x, self.y, ln, avail, justify=False, last=True, space_w=space_w)
                if k == len(lines) - 1:
                    joins = [i for i in range(1, len(ln)) if not ln[i].glued]
                    lw = sum(w.width for w in ln) + space_w * len(joins)
                    num = str(page)
                    num_w = text_width(num, TIMES, size)
                    dots_x0 = x + lw + 5
                    dots_x1 = self.margin_l + self.body_width - num_w - 6
                    if dots_x1 > dots_x0 + 6:
                        dot_w = text_width(".", TIMES, size)
                        count = int((dots_x1 - dots_x0) / dot_w)
                        self.page.text(dots_x0, self.y, "." * count, TIMES, size, 0.45)
                    self.page.text_right(self.margin_l + self.body_width, self.y, num, TIMES, size, 0.15)
                self.y -= lead
        self._suppress_indent = True


def _split_front_matter(blocks: list) -> tuple:
    """Front matter = title page through the end of the introductory material.

    With two or more H1s the second H1 (the first real part/chapter) starts the
    body.  With a single H1 the first H2 after it ends the title spread.
    """
    h1s = [k for k, b in enumerate(blocks) if isinstance(b, Heading) and b.level == 1]
    if len(h1s) >= 2:
        return blocks[: h1s[1]], blocks[h1s[1] :]
    if len(h1s) == 1:
        for k in range(h1s[0] + 1, len(blocks)):
            if isinstance(blocks[k], Heading) and blocks[k].level <= 2:
                return blocks[:k], blocks[k:]
    return blocks, []


def render_book_pdf(
    text: str,
    out_path,
    title: str,
    author: str = "",
    toc_filter=None,
    geometry: dict | None = None,
    compress: bool = True,
    verbose: bool = True,
) -> dict:
    """Typeset `text` (Markdown) as a book PDF with a page-numbered TOC.

    ``toc_filter(level, title) -> bool`` decides which headings appear in the
    table of contents.  Rendering is two-pass: page numbers are recorded on a
    first pass, then the final document inserts the TOC (whose own page count
    shifts every recorded number) and re-typesets the body identically.
    """
    blocks = parse_markdown(text)
    front, body = _split_front_matter(blocks)

    geo = {"page_w": 432.0, "page_h": 648.0, "margin_l": 54.0, "margin_r": 54.0, "margin_t": 50.0, "margin_b": 56.0}
    geo.update(geometry or {})

    # Pass 1: record the page each body heading lands on.
    probe = BookPDF(title=title, author=author, **geo)
    probe.render(front)
    probe.render(body, toc_filter=toc_filter)
    entries = probe.toc_entries
    result = {"pages": probe.number, "toc_entries": len(entries), "title": title, "author": author}

    if not entries:
        book = BookPDF(title=title, author=author, **geo)
        book.render(front + body, toc_filter=toc_filter)
        result["pages"] = book.number
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        book.doc.save(out_path, compress=compress)
        if verbose:
            print(f"wrote {out_path} — {book.number} pages, no TOC")
        return result

    # Count the pages the TOC itself needs (independent of the numbers shown).
    scratch = BookPDF(title=title, author=author, **geo)
    scratch.toc([(lvl, t, 999) for lvl, t, _ in entries])
    toc_pages = scratch.number

    # Pass 2: front matter, TOC with corrected page numbers, then the body
    # (re-rendered identically, so recorded pages shift by exactly toc_pages).
    book = BookPDF(title=title, author=author, **geo)
    book.render(front)
    book.toc([(lvl, t, p + toc_pages) for lvl, t, p in entries])
    book.render(body)
    result["pages"] = book.number
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    book.doc.save(out_path, compress=compress)
    if verbose:
        print(
            f"wrote {out} — {book.number} pages ({out.stat().st_size / 1024:.0f} KB), "
            f"TOC: {len(entries)} entries on {toc_pages} pages"
        )
    return result
