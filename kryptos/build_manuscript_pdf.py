"""Build a KDP 6x9, searchable PDF proof from the canonical Markdown source.
The Markdown remains the canonical editable manuscript; this generator is
intentionally dependency-free and deterministic.
"""
from pathlib import Path

SRC = Path(__file__).with_name("KRYPTOS_SCHOLARLY_MANUSCRIPT.md")
OUT = SRC.with_suffix(".pdf")
raw = SRC.read_text(encoding="utf-8").splitlines()
# KDP paperback trim: 6 x 9 inches, 72 points/inch.
W, H = 432, 648
margin, leading = 43, 15
usable = H - 2 * margin - 18
per_page = int(usable // leading)
# The canonical Markdown source now carries its own title page, copyright
# page, and foreword as real front matter (see the top of
# KRYPTOS_SCHOLARLY_MANUSCRIPT.md), so this generator no longer prepends a
# second, separate mini title block ahead of it — that previously produced
# two different-looking title pages in a row with inconsistent subtitles.
lines = raw
pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)]

# The base-14 Helvetica font used below is only declared with the PDF
# viewer's default (Standard) text encoding, and the content streams are
# written as raw encoded bytes — not through any font-specific glyph
# mapping. Writing multi-byte UTF-8 sequences straight into those strings
# (the previous behavior here) produces visibly garbled punctuation in
# real PDF viewers (em dashes, curly quotes, the (c) symbol, etc. render
# as mojibake, not as the intended character) even though the canonical
# Markdown source is correctly encoded. Rather than embed a Unicode font
# (which would break this generator's dependency-free, deterministic
# design), this proof build transliterates to the closest plain-ASCII
# equivalent for the PDF text stream only; the Markdown source and the
# EPUB (built separately, over UTF-8 XHTML) keep the real Unicode text.
_ASCII_MAP = {
    "\u2014": "--", "\u2013": "-", "\u2212": "-",
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u2026": "...", "\u00b7": " - ",
    "\u00b0": "deg", "\u2032": "'", "\u2033": '"',
    "\u00d7": "x", "\u2248": "~", "\u2265": ">=", "\u2264": "<=",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u2218": " o ",
    "\u00a7": "Sec. ", "\u00a9": "(c)",
    "\u00b2": "^2", "\u00b3": "^3", "\u2074": "^4", "\u2075": "^5",
    "\u2500": "-", "\u2502": "|", "\u251c": "+", "\u2514": "+",
    "\u00e8": "e", "\u00e9": "e", "\u00f6": "oe", "\u00df": "ss",
    "\u2705": "[OK]", "\u26a0": "[!]",
}


def ascii_safe(s):
    out = []
    for ch in s:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in _ASCII_MAP:
            out.append(_ASCII_MAP[ch])
        else:
            # Unmapped (rare emoji, foreign scripts, etc.): drop rather than
            # let it fall through as raw bytes a Standard-encoded Type1
            # font cannot represent.
            out.append("")
    return "".join(out)


def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def clean(line):
    line = ascii_safe(line)
    return line.replace("**", "").replace("`", "").replace("### ", "").replace("## ", "").replace("# ", "")

streams = []
for number, page_lines in enumerate(pages, 1):
    content = ["BT", "/F1 10.5 Tf", f"{margin} {H-margin-12} Td"]
    for line in page_lines:
        import textwrap
        text = clean(line)
        chunks = textwrap.wrap(text, width=62) or [""]
        for chunk in chunks:
            content += [f"({esc(chunk)}) Tj", f"0 -{leading} Td"]
    content += ["ET", "BT", "/F1 7 Tf", f"{W/2-12:.1f} 22 Td", f"({number}) Tj", "ET"]
    streams.append("\n".join(content).encode())

# PDF objects: catalog, pages, font, streams, page dictionaries.
first_stream, first_page = 4, 4 + len(streams)
objs = [None] * (first_page + len(streams))
objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
refs = " ".join(f"{first_page+i} 0 R" for i in range(len(streams)))
objs[2] = f"<< /Type /Pages /Kids [{refs}] /Count {len(streams)} >>".encode()
objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
for i, data in enumerate(streams):
    objs[first_stream+i] = f"<< /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"
    objs[first_page+i] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R >> >> /Contents {first_stream+i} 0 R >>".encode()

out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
offsets = [0] * len(objs)
for n in range(1, len(objs)):
    offsets[n] = len(out)
    out += f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n"
xref = len(out)
out += f"xref\n0 {len(objs)}\n0000000000 65535 f \n".encode()
for n in range(1, len(objs)):
    out += f"{offsets[n]:010d} 00000 n \n".encode()
out += f"trailer\n<< /Size {len(objs)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
OUT.write_bytes(out)
print(f"wrote {OUT} ({len(streams)} KDP 6x9 pages, {len(out)} bytes)")
