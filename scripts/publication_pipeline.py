"""Production-oriented, dependency-free publication preflight and EPUB builder."""

import datetime
import hashlib
import json
import re
from html import escape
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "kryptos"
MD = K / "KRYPTOS_SCHOLARLY_MANUSCRIPT.md"


def image_size(path):
    data = path.read_bytes()
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            n = int.from_bytes(data[i + 2 : i + 4], "big")
            if 0xC0 <= marker <= 0xC3:
                return int.from_bytes(data[i + 5 : i + 7], "big"), int.from_bytes(data[i + 7 : i + 9], "big")
            i += 2 + n
    return (0, 0)


def main():
    text = MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = [(i + 1, x[2:].strip()) for i, x in enumerate(lines) if x.startswith("#")]
    footnotes = dict(re.findall(r"^\[\^([^]]+)\]:\s*(.+)$", text, re.M))
    figures = [(i + 1, x[2:].strip()) for i, x in enumerate(lines) if re.match(r"^#{1,3}\s*(Figure|Fig\.)", x, re.I)]
    tables = [(i + 1, x[2:].strip()) for i, x in enumerate(lines) if re.match(r"^#{1,3}\s*Table", x, re.I)]
    (K / "generated-index.md").write_text(
        "# Generated page-aware index\n\n" + "\n".join(f"- {h} — source line {n}" for n, h in headings),
        encoding="utf-8",
    )
    (K / "figure-list.md").write_text(
        "# Figure list\n\n" + "\n".join(f"- {h} — source line {n}" for n, h in figures), encoding="utf-8"
    )
    (K / "table-list.md").write_text(
        "# Table list\n\n" + "\n".join(f"- {h} — source line {n}" for n, h in tables), encoding="utf-8"
    )
    cover = K / "book-cover.jpg"
    w, h = image_size(cover)
    rights = K / "image-rights.json"
    if not rights.exists():
        rights.write_text(
            json.dumps(
                {
                    "images": [
                        {
                            "file": cover.name,
                            "rights_status": "verify-before-publication",
                            "source": "repository asset",
                            "sha256": hashlib.sha256(cover.read_bytes()).hexdigest(),
                        }
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    def inline_md(s):
        # Minimal, dependency-free Markdown inline styling for the EPUB body.
        # Must run after escape() (asterisks/backticks aren't touched by it),
        # and bold before italics so "**x**" isn't read as italic "*" pairs.
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
        return s

    xhtml = []
    foot = []
    for line in lines:
        if line.startswith("# "):
            xhtml.append("<h1>" + inline_md(escape(line[2:])) + "</h1>")
        elif line.startswith("## "):
            xhtml.append("<h2>" + inline_md(escape(line[3:])) + "</h2>")
        elif line.startswith("### "):
            xhtml.append("<h3>" + inline_md(escape(line[4:])) + "</h3>")
        elif line.startswith("[^") and "]:" in line:
            continue
        else:
            line = re.sub(
                r"\[\^([^]]+)\]",
                lambda m: f'<a epub:type="noteref" href="#fn-{m.group(1)}">[{m.group(1)}]</a>',
                escape(line),
            )
            line = inline_md(line)
            xhtml.append("<p>" + line + "</p>")
    for key, val in footnotes.items():
        foot.append(f'<li id="fn-{escape(key)}">{escape(val)} <a href="#fnref-{escape(key)}">return</a></li>')
    body = "\n".join(xhtml) + '<section epub:type="footnotes"><h2>Notes</h2><ol>' + "".join(foot) + "</ol></section>"
    toc = "".join(f'<li><a href="content.xhtml">{escape(h)}</a></li>' for _, h in headings[:100])
    epub = K / "KRYPTOS_SCHOLARLY_MANUSCRIPT.epub"
    with ZipFile(epub, "w") as z:
        z.writestr("mimetype", "application/epub+zip", ZIP_STORED)
        z.writestr(
            "META-INF/container.xml",
            '<container version="1.0"><rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        z.writestr(
            "OEBPS/content.xhtml",
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Kryptos Scholarly Manuscript</title></head><body>'
            + body
            + "</body></html>",
        )
        z.writestr("OEBPS/nav.xhtml", '<nav epub:type="toc"><h1>Contents</h1><ol>' + toc + "</ol></nav>")
        z.writestr(
            "OEBPS/package.opf",
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid"><metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Kryptos Scholarly Manuscript</dc:title><dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en</dc:language><dc:identifier id="bookid">kryptos-scholarly-manuscript</dc:identifier><meta property="dcterms:modified">'
            + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            + '</meta></metadata><manifest><item id="content" href="content.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="content"/></spine></package>',
        )
    manifest = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "word_count": len(re.findall(r"\b\w+\b", text)),
        "footnotes": len(footnotes),
        "figures": len(figures),
        "tables": len(tables),
        "epub_navigation": True,
        "cover": {"width": w, "height": h, "dpi_required": 300, "status": "review"},
        "kdp_preflight": {
            "trim": "6x9",
            "bleed": "review-required",
            "margins": "review-required",
            "fonts": "review-required",
            "images": "review-required",
        },
        "rights_ledger": str(rights.name),
        "revision_history": [
            {
                "revision": "1.1",
                "date": datetime.date.today().isoformat(),
                "change": "production EPUB and preflight metadata",
            }
        ],
    }
    (K / "publication-preflight.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
