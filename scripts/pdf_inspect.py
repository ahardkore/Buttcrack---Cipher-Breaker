#!/usr/bin/env python3
"""Inspect a PDF built by ventures/puzzle-packs/pdf.py: dump pages as text lines
with fonts/positions, and run layout sanity checks (margins, single-word lines,
stray emphasis markers, fonts used).  Development/QA tool for the book builds.

    python3 scripts/pdf_inspect.py FILE.pdf [page numbers...] [--w W --ml L --mr R --mt T --mb B]
"""

import re
import sys
import zlib

sys.path.insert(0, "ventures/puzzle-packs")
from pdf import text_width  # noqa: E402

FONT_BY_ALIAS = {
    "TimesRoman": "Times-Roman",
    "TimesBold": "Times-Bold",
    "TimesItalic": "Times-Italic",
    "TimesBoldItalic": "Times-BoldItalic",
    "Helvetica": "Helvetica",
    "HelveticaBold": "Helvetica-Bold",
    "HelveticaOblique": "Helvetica-Oblique",
    "Courier": "Courier",
    "CourierBold": "Courier-Bold",
}

WINANSI_HI = {
    0x80: "€", 0x82: "‚", 0x83: "ƒ", 0x84: "„", 0x85: "…", 0x86: "†", 0x87: "‡",
    0x88: "ˆ", 0x89: "‰", 0x8A: "Š", 0x8B: "‹", 0x8C: "Œ", 0x8E: "Ž", 0x91: "‘",
    0x92: "’", 0x93: "“", 0x94: "”", 0x95: "•", 0x96: "–", 0x97: "—", 0x98: "˜",
    0x99: "™", 0x9A: "š", 0x9B: "›", 0x9C: "œ", 0x9E: "ž", 0x9F: "Ÿ",
}


def parse_pages(path):
    data = open(path, "rb").read()
    streams = []
    for m in re.finditer(rb"/Length (\d+)( /Filter /FlateDecode)? >>\nstream\n", data):
        start = m.end()
        length = int(m.group(1))
        raw = data[start : start + length]
        streams.append(zlib.decompress(raw) if m.group(2) else raw)
    pages = []
    for s in streams:
        ops = []
        font, size, x, y = "?", 0.0, 0.0, 0.0
        text = s.decode("latin-1")
        for tok in re.finditer(r"/(\w+) ([\d.]+) Tf|1 0 0 1 ([\d.-]+) ([\d.-]+) Tm|\((.*?)(?<!\\)\) Tj", text):
            if tok.group(1):
                font, size = tok.group(1), float(tok.group(2))
            elif tok.group(3) is not None:
                x, y = float(tok.group(3)), float(tok.group(4))
            else:
                ops.append((x, y, font, size, tok.group(5)))
        pages.append(ops)
    return pages, data


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "01234567":
                code = int(s[i + 1 : i + 4], 8)
                out.append(WINANSI_HI.get(code, chr(code)) if code > 127 else chr(code))
                i += 4
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def page_lines(ops):
    """Group Tj ops into visual lines by y coordinate."""
    lines = {}
    for x, y, font, size, text in ops:
        lines.setdefault(round(y, 1), []).append((x, font, size, unescape(text)))
    return [(y, sorted(lines[y])) for y in sorted(lines, reverse=True)]


def main(argv):
    args = list(argv)
    show_pages = set()
    geo = dict(w=432.0, ml=54.0, mr=54.0, mt=50.0, mb=56.0)
    path = args.pop(0)
    while args:
        a = args.pop(0)
        if a == "--w":
            geo["w"] = float(args.pop(0))
        elif a == "--ml":
            geo["ml"] = float(args.pop(0))
        elif a == "--mr":
            geo["mr"] = float(args.pop(0))
        elif a == "--mt":
            geo["mt"] = float(args.pop(0))
        elif a == "--mb":
            geo["mb"] = float(args.pop(0))
        else:
            show_pages.add(int(a))

    pages, data = parse_pages(path)
    print(f"{path}: {len(pages)} pages, {len(data)/1024:.0f} KB")
    fonts = set()
    bad = []
    single_word_lines = []
    for pno, ops in enumerate(pages, 1):
        for y, segs in page_lines(ops):
            line_text = " ".join(t for _, _, _, t in segs)
            fonts.update(f for _, f, _, _ in segs)
            x_last = max(
                x + text_width(t, FONT_BY_ALIAS.get(f, "Times-Roman"), s) for x, f, s, t in segs
            )
            in_body = geo["mb"] + 15 < y < 700
            if in_body and x_last > geo["w"] - geo["mr"] + 1.5:
                bad.append((pno, y, f"exceeds right margin ({x_last:.1f}): {line_text[:60]!r}"))
            n_words = len(line_text.split())
            if in_body and n_words == 1 and not re.fullmatch(r"\d+", line_text.strip()) and not line_text.startswith("•"):
                single_word_lines.append((pno, y, line_text))
        if show_pages and pno in show_pages:
            print(f"\n===== page {pno} =====")
            for y, segs in page_lines(ops):
                print(f"y={y:6.1f} " + " | ".join(f"[{f}@{x:.0f}] {t}" for x, f, s, t in segs))

    print("\nfonts used:", sorted(fonts))
    print("TimesItalic present:", "TimesItalic" in fonts)
    print("TimesBoldItalic present:", "TimesBoldItalic" in fonts)
    print(f"single-word body lines: {len(single_word_lines)}", single_word_lines[:8])
    stray = []
    for pno, ops in enumerate(pages, 1):
        for y, segs in page_lines(ops):
            for x, f, s, t in segs:
                if re.search(r"\w\*|\*\w", t) and f not in ("Courier", "CourierBold"):
                    stray.append((pno, t[:70]))
    print("stray emphasis asterisks outside code:", len(stray), stray[:5])
    if bad:
        print(f"MARGIN VIOLATIONS: {len(bad)}")
        for b in bad[:10]:
            print("  ", b)
    else:
        print("no margin violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
