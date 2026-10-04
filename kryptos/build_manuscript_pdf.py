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
# Front matter makes the proof recognizable as a book and leaves room for a
# later ISBN/copyright page without changing the source structure.
front = [
    "KRYPTOS",
    "History, Method, and the Limits of a Break",
    "A scholarly cryptanalytic study of Jim Sanborn's Kryptos,",
    "the CIA context, and the Paradigm Kryptos challenges",
    "",
    "Working manuscript — KDP paperback proof",
    "October 2026",
    "",
    "Copyright and rights notice",
    "This working edition contains original analysis and clearly marked",
    "provisional claims. Historical images require source and license review.",
    "K4 is not labeled solved without independent exact verification.",
    "",
    "[Reserved for ISBN, edition, and publisher imprint]",
    "",
]
lines = front + raw
pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)]

def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def clean(line):
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
