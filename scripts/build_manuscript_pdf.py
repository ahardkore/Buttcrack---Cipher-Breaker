#!/usr/bin/env python3
"""Typeset the Kryptos decryption manuscript as a PDF.

Uses the repository's shared, dependency-free book engine
(``scripts/book_typeset.py``) — real paragraphs merged from hard-wrapped
Markdown, genuine italic/bold faces, lists, quotes, tables, code blocks and a
page-numbered table of contents — on top of the in-repo PDF writer
(``ventures/puzzle-packs/pdf.py``).

    python3 scripts/build_manuscript_pdf.py
    python3 scripts/build_manuscript_pdf.py --source FILE --out FILE.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from book_typeset import render_book_pdf  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "kryptos" / "THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md"))
    parser.add_argument("--out", default=str(ROOT / "transfer" / "THE_KRYPTOS_DECRYPTION_MANUSCRIPT.pdf"))
    parser.add_argument("--title", default="The Kryptos Decryption Manuscript")
    parser.add_argument("--author", default="")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    text = source.read_text(encoding="utf-8")

    # This manuscript's sections are its chapters; list them all.
    result = render_book_pdf(
        text,
        Path(args.out).resolve(),
        title=args.title,
        author=args.author,
        toc_filter=lambda level, title: level <= 2,
        geometry=dict(
            page_w=612.0,
            page_h=792.0,
            margin_l=72.0,
            margin_r=72.0,
            margin_t=72.0,
            margin_b=64.0,
        ),
        compress=True,
    )
    result["source"] = str(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
