"""Build a KDP 6x9, searchable PDF proof from the canonical Markdown source.

The Markdown remains the canonical editable manuscript; this generator is
intentionally dependency-free and deterministic.  It typesets through the
repository's shared book engine (``scripts/book_typeset.py``), which merges
hard-wrapped source lines into real paragraphs, sets emphasis in genuine
italic/bold faces, and renders lists, quotes, tables, code blocks and a
page-numbered table of contents — see KDP_PRODUCTION_NOTES.md, revision 1.2.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from book_typeset import render_book_pdf  # noqa: E402

SRC = ROOT / "kryptos" / "KRYPTOS_SCHOLARLY_MANUSCRIPT.md"
OUT = SRC.with_suffix(".pdf")


def toc_filter(level: int, title: str) -> bool:
    """Parts, numbered chapters and appendices appear in the printed TOC."""
    if level == 1:
        return True
    return level == 2 and bool(re.match(r"^(\d+\.|Appendix)", title))


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    result = render_book_pdf(
        text,
        OUT,
        title="Kryptos: The Copper Cipher",
        author="Aaron Hard",
        toc_filter=toc_filter,
        # KDP paperback trim: 6 x 9 inches (72 pt/inch), no-bleed margins
        # per KDP_PRODUCTION_NOTES.md (inside 0.75", outside 0.55", 0.65"
        # top/bottom; the single-sided proof uses the inside measure both
        # sides so nothing can fall into the gutter).
        geometry=dict(
            page_w=432.0,
            page_h=648.0,
            margin_l=54.0,
            margin_r=40.0,
            margin_t=47.0,
            margin_b=50.0,
        ),
    )
    result["trim"] = "6x9"
    print(f"source: {SRC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
