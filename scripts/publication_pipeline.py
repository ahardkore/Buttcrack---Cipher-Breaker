"""Production-oriented, dependency-free publication preflight and EPUB builder.

Builds the EPUB edition of ``kryptos/KRYPTOS_SCHOLARLY_MANUSCRIPT.md`` from the
same canonical Markdown as the print proof (``kryptos/build_manuscript_pdf.py``),
through the shared book engine in ``scripts/book_typeset.py``:

* hard-wrapped source lines merge into real paragraphs (no more single-word
  lines where a paragraph was arbitrarily cut);
* ``*emphasis*`` becomes genuine ``<em>``/``<strong>`` (no literal asterisks);
* each ``# Part`` becomes its own chapter file with a working table of
  contents, anchors, cover page, endnotes and a book stylesheet;
* the package is validated (well-formed XML, resolvable manifest and links)
  before the build reports success.
"""

import datetime
import hashlib
import json
import re
import sys
import zipfile
from html import escape
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from book_typeset import (  # noqa: E402
    CodeBlock,
    FootnoteDef,
    Heading,
    Hr,
    ListBlock,
    Para,
    Quote,
    Table,
    parse_inline,
    parse_markdown,
    runs_plain_text,
)

K = ROOT / "kryptos"
MD = K / "KRYPTOS_SCHOLARLY_MANUSCRIPT.md"
BOOK_TITLE = "Kryptos: The Copper Cipher"
BOOK_AUTHOR = "Aaron Hard"
BOOK_DESCRIPTION = (
    "History, hand methods, and the search for meaning in codes — a scholarly, "
    "editorially honest study of Jim Sanborn's Kryptos sculpture, the people who "
    "built and broke it, and the Paradigm Kryptos suite (PK1–PK10)."
)

STYLE_CSS = """\
/* Kryptos: The Copper Cipher — book stylesheet */
body {
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.45;
  margin: 0 4%;
  text-align: justify;
  -webkit-hyphens: auto;
  -epub-hyphens: auto;
  adobe-hyphenate: auto;
}
h1 {
  font-size: 1.55em;
  font-weight: bold;
  line-height: 1.25;
  text-align: center;
  margin: 2.2em 0 1em;
  text-indent: 0;
}
h2 { font-size: 1.22em; text-align: left; margin: 1.7em 0 0.7em; text-indent: 0; }
h3 { font-size: 1.08em; text-align: left; margin: 1.4em 0 0.55em; text-indent: 0; }
h4, h5, h6 { font-size: 1em; text-align: left; margin: 1.2em 0 0.5em; text-indent: 0; }
h2, h3, h4, h5, h6 { page-break-after: avoid; }
/* the subtitle directly under the book title reads as a subtitle */
h1 + h2 {
  text-align: center;
  font-style: italic;
  font-weight: normal;
  font-size: 1.12em;
  margin-top: -0.5em;
}
p { margin: 0; text-indent: 1.2em; }
p.first, h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p, hr + p,
blockquote p, li p, td p, th p { text-indent: 0; }
blockquote {
  margin: 1em 1.3em;
  padding-left: 0.85em;
  border-left: 2px solid #98a0a8;
  font-style: italic;
  color: #333333;
}
blockquote p { margin: 0.35em 0; }
pre {
  font-family: "Courier New", Courier, monospace;
  font-size: 0.82em;
  line-height: 1.32;
  text-align: left;
  white-space: pre-wrap;
  background-color: #f4f5f6;
  border: 1px solid #d8dbde;
  border-left: 3px solid #b7bdc4;
  padding: 0.55em 0.7em;
  margin: 0.9em 0;
  page-break-inside: avoid;
}
code { font-family: "Courier New", Courier, monospace; font-size: 0.88em; }
p code, li code, td code, th code, dd code, dt code { background-color: #f0f1f2; padding: 0 0.12em; }
ul, ol { margin: 0.7em 0 0.7em 1.5em; padding: 0; text-align: left; }
li { margin: 0.22em 0; text-indent: 0; }
li > p { margin: 0.15em 0; }
table {
  border-collapse: collapse;
  margin: 1em auto;
  font-size: 0.85em;
  line-height: 1.3;
  text-align: left;
}
th, td { border: 1px solid #b9bfc6; padding: 0.3em 0.5em; vertical-align: top; }
th { background-color: #eef0f2; font-weight: bold; }
.ta-l { text-align: left; }
.ta-c { text-align: center; }
.ta-r { text-align: right; }
hr { border: 0; border-top: 1px solid #9aa1a8; margin: 1.6em 22%; }
a { color: inherit; text-decoration: underline; }
sup { font-size: 0.72em; line-height: 0; }
.notes-list { margin-left: 1.6em; }
.notes-list li { margin-bottom: 0.5em; }
.cover-page { margin: 0; padding: 0; text-align: center; }
.cover { margin: 0; padding: 0; }
.cover img { max-width: 100%; max-height: 100%; }
"""


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


# ---------------------------------------------------------------------------
# XHTML rendering
# ---------------------------------------------------------------------------


def esc(s):
    return escape(s, quote=True)


REPO_URL = "https://github.com/ahardkore/Buttcrack---Cipher-Breaker"


def resolve_link(href):
    """Repository-relative links point outside the EPUB; retarget them at the
    public GitHub source so every link in the book stays clickable."""
    if href.startswith(("http://", "https://", "mailto:", "#")):
        return href
    path = href.split("#")[0].lstrip("/")
    norm = str(Path("kryptos") / Path(path)) if not path.startswith("..") else str(Path(path))
    norm = norm.replace("\\", "/")
    if norm.startswith("../"):
        norm = norm[3:]
    return f"{REPO_URL}/blob/main/{norm}"


def runs_to_html(runs):
    parts = []
    for r in runs:
        if r.text == "\n":
            parts.append("<br/>")
            continue
        t = esc(r.text)
        if r.code:
            t = f"<code>{t}</code>"
        if r.fn:
            t = (
                f'<a epub:type="noteref" id="fnref-{esc(r.fn)}" '
                f'href="notes.xhtml#fn-{esc(r.fn)}"><sup>{t}</sup></a>'
            )
        elif r.link:
            t = f'<a href="{esc(resolve_link(r.link))}">{t}</a>'
        if r.italic:
            t = f"<em>{t}</em>"
        if r.bold:
            t = f"<strong>{t}</strong>"
        parts.append(t)
    return "".join(parts)


def _table_to_html(tbl):
    aligns = tbl.aligns + ["l"] * (len(tbl.rows[0]) - len(tbl.aligns))
    head = "".join(
        f'<th class="ta-{aligns[c]}">{runs_to_html(parse_inline(cell))}</th>'
        for c, cell in enumerate(tbl.rows[0])
    )
    body_rows = []
    for row in tbl.rows[1:]:
        body_rows.append(
            "<tr>"
            + "".join(
                f'<td class="ta-{aligns[c]}">{runs_to_html(parse_inline(cell))}</td>'
                for c, cell in enumerate(row)
            )
            + "</tr>"
        )
    return (
        '<table class="data">\n<thead>\n<tr>' + head + "</tr>\n</thead>\n<tbody>\n"
        + "\n".join(body_rows)
        + "\n</tbody>\n</table>"
    )


def blocks_to_html(blocks, ctx):
    out = []
    prev_kind = None
    for b in blocks:
        if isinstance(b, Heading):
            lvl = min(b.level, 6)
            ctx["h"] += 1
            out.append(f'<h{lvl} id="sec-{ctx["h"]}">{runs_to_html(b.runs)}</h{lvl}>')
            prev_kind = "heading"
            continue
        if isinstance(b, Para):
            cls = ' class="first"' if prev_kind in (None, "heading", "hr") else ""
            out.append(f"<p{cls}>{runs_to_html(b.runs)}</p>")
            prev_kind = "para"
            continue
        if isinstance(b, Hr):
            out.append("<hr/>")
            prev_kind = "hr"
            continue
        if isinstance(b, Quote):
            out.append(f"<blockquote>\n{blocks_to_html(b.blocks, ctx)}\n</blockquote>")
            prev_kind = "quote"
            continue
        if isinstance(b, ListBlock):
            tag = "ol" if b.ordered else "ul"
            start_attr = f' start="{b.start}"' if b.ordered and b.start != 1 else ""
            items = "".join(f"<li>{blocks_to_html(item, ctx)}</li>" for item in b.items)
            out.append(f"<{tag}{start_attr}>\n{items}\n</{tag}>")
            prev_kind = "list"
            continue
        if isinstance(b, CodeBlock):
            out.append(f"<pre><code>{esc(chr(10).join(b.lines))}</code></pre>")
            prev_kind = "pre"
            continue
        if isinstance(b, Table):
            out.append(_table_to_html(b))
            prev_kind = "table"
            continue
        if isinstance(b, FootnoteDef):
            ctx["footnotes"].append((b.key, b.runs, ctx["file"]))
            prev_kind = "footnote"
            continue
        prev_kind = None
    return "\n".join(out)


def xhtml_document(title, body_html, body_class=None):
    cls = f' class="{body_class}"' if body_class else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en" lang="en">\n'
        "<head>\n"
        f"<title>{esc(title)}</title>\n"
        '<link rel="stylesheet" type="text/css" href="style.css"/>\n'
        "</head>\n"
        f"<body{cls}>\n{body_html}\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# EPUB assembly
# ---------------------------------------------------------------------------


def split_chapters(blocks):
    """Split at level-1 headings; each becomes its own spine document."""
    chapters = []
    current = {"title": BOOK_TITLE, "blocks": []}
    for b in blocks:
        if isinstance(b, Heading) and b.level == 1:
            if current["blocks"]:
                chapters.append(current)
            current = {"title": runs_plain_text(b.runs), "blocks": [b]}
        else:
            current["blocks"].append(b)
    if current["blocks"]:
        chapters.append(current)
    return chapters


def build_epub(text, epub_path):
    blocks = parse_markdown(text)
    chapters = split_chapters(blocks)
    files = {"style.css": STYLE_CSS}
    nav_entries = []  # (level, title, href)
    ctx = {"h": 0, "footnotes": []}

    for idx, chapter in enumerate(chapters, 1):
        name = f"chapter-{idx:03d}.xhtml"
        ctx["file"] = name
        ctx["nav"] = []
        body = blocks_to_html(chapter["blocks"], ctx)
        files[name] = xhtml_document(chapter["title"], body)
        # sec-N ids were assigned in document order by blocks_to_html; walk the
        # chapter again to build navigation links for its level-2 sections.
        counter = ctx["h"]
        for b in reversed(chapter["blocks"]):
            if isinstance(b, Heading):
                counter -= 1
        nav_entries.append((1, chapter["title"], name))
        for b in chapter["blocks"]:
            if isinstance(b, Heading):
                counter += 1
                if b.level == 2:
                    nav_entries.append((2, runs_plain_text(b.runs), f"{name}#sec-{counter}"))
    stats = {"chapters": len(chapters)}

    # Endnotes, if the manuscript defines any.
    notes_html = ""
    if ctx["footnotes"]:
        items = []
        for key, runs, src_file in ctx["footnotes"]:
            back = f' <a href="{src_file}#fnref-{esc(key)}">&#8617;</a>'
            items.append(f'<li id="fn-{esc(key)}">{runs_to_html(runs)}{back}</li>')
        notes_html = xhtml_document(
            "Notes",
            '<section epub:type="endnotes">\n<h1 id="notes">Notes</h1>\n'
            f'<ol class="notes-list">\n{"".join(items)}\n</ol>\n</section>',
        )
        files["notes.xhtml"] = notes_html
        stats["endnotes"] = len(ctx["footnotes"])
    else:
        stats["endnotes"] = 0

    # Cover page.
    cover_jpg = (K / "book-cover.jpg").read_bytes()
    files["images/cover.jpg"] = cover_jpg
    files["cover.xhtml"] = xhtml_document(
        "Cover",
        '<figure class="cover" epub:type="cover"><img src="images/cover.jpg" '
        f'alt="{esc(BOOK_TITLE)} — cover"/></figure>',
        body_class="cover-page",
    )

    # Navigation document: one nested <ol> of sections per chapter.
    toc_items = []
    subs = []
    for lvl, title, href in nav_entries:
        if lvl == 1:
            if toc_items:
                if subs:
                    toc_items.append("<ol>" + "".join(subs) + "</ol>")
                    subs = []
                toc_items.append("</li>")
            toc_items.append(f'<li><a href="{href}">{esc(title)}</a>')
        else:
            subs.append(f'<li><a href="{href}">{esc(title)}</a></li>')
    if subs:
        toc_items.append("<ol>" + "".join(subs) + "</ol>")
    if toc_items:
        toc_items.append("</li>")
    files["nav.xhtml"] = xhtml_document(
        "Contents",
        '<nav epub:type="toc" id="toc">\n<h1>Contents</h1>\n<ol>\n'
        + "\n".join(toc_items)
        + "\n</ol>\n</nav>\n"
        + '<nav epub:type="landmarks" hidden="hidden">\n<h2>Guide</h2>\n<ol>\n'
        + '<li><a epub:type="cover" href="cover.xhtml">Cover</a></li>\n'
        + '<li><a epub:type="toc" href="nav.xhtml">Table of Contents</a></li>\n'
        + f'<li><a epub:type="bodymatter" href="chapter-001.xhtml">Start of {esc(BOOK_TITLE)}</a></li>\n'
        + "</ol>\n</nav>",
    )

    # Package document.
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    manifest.append('<item id="css" href="style.css" media-type="text/css"/>')
    manifest.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
    manifest.append(
        '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>'
    )
    spine = ['<itemref idref="cover"/>']
    if "notes.xhtml" in files:
        manifest.append('<item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/>')
    for idx in range(1, len(chapters) + 1):
        manifest.append(f'<item id="ch{idx:03d}" href="chapter-{idx:03d}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="ch{idx:03d}"/>')
    if "notes.xhtml" in files:
        spine.append('<itemref idref="notes"/>')
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files["package.opf"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="bookid" xml:lang="en">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '<dc:identifier id="bookid">kryptos-scholarly-manuscript</dc:identifier>\n'
        f"<dc:title>{esc(BOOK_TITLE)}</dc:title>\n"
        f'<dc:creator id="creator">{esc(BOOK_AUTHOR)}</dc:creator>\n'
        '<meta refines="#creator" property="role" scheme="marc:relators">aut</meta>\n'
        "<dc:language>en</dc:language>\n"
        f"<dc:description>{esc(BOOK_DESCRIPTION)}</dc:description>\n"
        f'<meta property="dcterms:modified">{modified}</meta>\n'
        '<meta name="cover" content="cover-image"/>\n'
        "</metadata>\n"
        f"<manifest>\n{chr(10).join(manifest)}\n</manifest>\n"
        f"<spine>\n{chr(10).join(spine)}\n</spine>\n"
        "</package>\n"
    )
    files["META-INF/container.xml"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0">\n<rootfiles>\n'
        '<rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>\n'
        "</rootfiles>\n</container>\n"
    )

    stats["nav_entries"] = len(nav_entries)
    with zipfile.ZipFile(epub_path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", files.pop("META-INF/container.xml"))
        for name in sorted(files):
            data = files[name]
            if isinstance(data, str):
                data = data.encode("utf-8")
            z.writestr(f"OEBPS/{name}", data)
    stats["nav_entries"] = len(nav_entries)
    return stats


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_epub(path):
    errors = []
    stats = {"files": 0}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        stats["files"] = len(names)
        if names[0] != "mimetype" or z.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            errors.append("mimetype must be the first entry, stored uncompressed")
        if "META-INF/container.xml" not in names:
            errors.append("missing META-INF/container.xml")
        # every XML document must be well-formed
        parsed = {}
        for name in names:
            if name.endswith((".xhtml", ".opf", ".xml")):
                try:
                    parsed[name] = ElementTree.fromstring(z.read(name))
                except ElementTree.ParseError as e:
                    errors.append(f"{name}: not well-formed XML ({e})")
        # manifest hrefs must exist
        opf = parsed.get("OEBPS/package.opf")
        manifest_files = []
        if opf is not None:
            ns = {"opf": "http://www.idpf.org/2007/opf"}
            for item in opf.findall(".//opf:manifest/opf:item", ns):
                href = item.get("href")
                if f"OEBPS/{href}" not in names:
                    errors.append(f"manifest href missing from package: {href}")
                manifest_files.append(href)
        # internal links must resolve
        ids_by_file = {}
        for name, root in parsed.items():
            if not name.endswith(".xhtml"):
                continue
            ids = {el.get("id") for el in root.iter() if el.get("id")}
            ids_by_file[name] = ids
            for el in root.iter():
                for attr in ("href",):
                    href = el.get(attr)
                    if not href or href.startswith(("http://", "https://", "mailto:")):
                        continue
                    target, _, frag = href.partition("#")
                    if target:
                        target_name = f"OEBPS/{target}"
                        if target_name not in names:
                            errors.append(f"{name}: broken link target {href}")
                            continue
                        if frag and target_name.endswith(".xhtml") and frag not in ids_by_file.get(target_name, set()):
                            errors.append(f"{name}: broken fragment {href}")
                    elif frag and frag not in ids:
                        errors.append(f"{name}: broken same-file fragment #{frag}")
        # typography invariants
        first_chapter = z.read("OEBPS/chapter-001.xhtml").decode("utf-8")
        if "<em>" not in first_chapter:
            errors.append("chapter 1 contains no <em> — italics are not being rendered")
        if re.search(r">\s*<p>\s*</p>", first_chapter):
            errors.append("empty paragraphs present")
        if re.search(r">\s*<p>[^<]*\*</p>", first_chapter):
            errors.append("literal asterisk paragraph found")
        stats["chapters_with_em"] = sum(
            1 for n in names if n.startswith("OEBPS/chapter-") and b"<em>" in z.read(n)
        )
    stats["valid"] = not errors
    stats["errors"] = errors
    return stats


# ---------------------------------------------------------------------------
# Preflight + main
# ---------------------------------------------------------------------------


def main():
    text = MD.read_text(encoding="utf-8")

    # Fence-aware scans for the preflight indexes (a "# comment" inside a code
    # fence is not a heading).
    lines = text.splitlines()
    infence = False
    headings = []
    figures = []
    tables = []
    for i, line in enumerate(lines):
        if line.lstrip(" ").startswith("```"):
            infence = not infence
            continue
        if infence:
            continue
        if line.startswith("#"):
            headings.append((i + 1, line.lstrip("# ").strip()))
            if re.match(r"^#{1,3}\s*(Figure|Fig\.)", line, re.I):
                figures.append((i + 1, line.lstrip("# ").strip()))
            elif re.match(r"^#{1,3}\s*Table", line, re.I):
                tables.append((i + 1, line.lstrip("# ").strip()))

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

    epub = K / "KRYPTOS_SCHOLARLY_MANUSCRIPT.epub"
    epub_stats = build_epub(text, epub)
    validation = validate_epub(epub)
    if not validation["valid"]:
        for error in validation["errors"]:
            print("EPUB VALIDATION ERROR:", error)
        raise SystemExit(1)

    manifest = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "word_count": len(re.findall(r"\b\w+\b", text)),
        "footnotes": epub_stats["endnotes"],
        "figures": len(figures),
        "tables": len(tables),
        "epub": {
            "file": epub.name,
            "chapters": epub_stats["chapters"],
            "nav_entries": epub_stats["nav_entries"],
            "endnotes": epub_stats["endnotes"],
            "stylesheet": "style.css",
            "cover": {"width": w, "height": h, "dpi_required": 300, "status": "review"},
            "validation": validation,
        },
        "epub_navigation": True,
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
                "date": "2026-10-03",
                "change": "production EPUB and preflight metadata",
            },
            {
                "revision": "1.2",
                "date": datetime.date.today().isoformat(),
                "change": (
                    "typographic overhaul: paragraphs merged from hard-wrapped source "
                    "lines, real emphasis (em/strong) and code spans, per-part chapter "
                    "files with anchored navigation, book stylesheet, cover page, "
                    "endnotes and built-in package validation; PDF and EPUB now share "
                    "the scripts/book_typeset.py engine"
                ),
            },
        ],
    }
    (K / "publication-preflight.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(
        f"EPUB OK: {epub_stats['chapters']} chapters, {epub_stats['nav_entries']} nav entries, "
        f"{validation['files']} files, {epub.stat().st_size / 1024:.0f} KB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
