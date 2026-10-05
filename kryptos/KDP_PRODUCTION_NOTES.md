# Amazon KDP production specification

## Edition

**Working title:** *Kryptos: The Copper Cipher*  
**Subtitle:** History, Hand Methods, and the Search for Meaning in Codes  
**Author:** Aaron Hard  
**Copyright:** © 2026 Aaron Hard. All rights reserved.  
**Format:** paperback, black and white interior  
**Trim:** 6 × 9 inches  
**Technical content status:** PK1–PK10 independently verified; cryptanalytic content frozen
**Interior:** white paper, black ink, no bleed  
**Margins:** inside 0.75 inch, outside 0.55 inch, top 0.65 inch, bottom 0.65 inch  
**Target length:** 350–400 pages after expansion, citations, images, notes, and appendices  

## Editorial and rights policy

The manuscript uses original prose and repository-generated diagrams wherever possible. Any historical image added to the final edition must be public domain or used under a license compatible with print distribution. Each image receives a caption, creator, source URL or archive identifier, license, and access date. CIA seals, government photographs, and historical documents require source-by-source rights review; government origin alone is not a universal guarantee of unrestricted use.

No image will be represented as an official CIA endorsement. AI-generated illustrations will be labeled in the production record and used only for explanatory diagrams or clearly fictional reconstructions, never as documentary evidence.

## Required finalization checklist

- [ ] Complete 350–400-page text expansion.
- [ ] Verify every K1–K4 transcription against a cited source.
- [ ] Mark the K4 candidate PROVISIONAL until independently round-trip verified.
- [x] Synchronize PK9/PK10 status: PK9 is independently verified by `verify_pk9_solution.py` as `Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)`; PK10 is independently verified by `verify_pk10_solution.py`. See `PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md` for provenance.
- [ ] Add Chicago-style notes and bibliography.
- [ ] Add image captions and rights ledger.
- [ ] Run preflight: embedded fonts, page count, trim size, margins, no clipped text.
- [ ] Proof a physical copy before publication.
- [x] Generate EPUB edition from the same canonical Markdown source with `scripts/publication_pipeline.py`; Kindle conversion remains a separate distributor-format step.
- [x] Run automated repository preflight: manuscript evidence audit, PDF/EPUB validity checks, canonical PK1–PK10 audit, and assembled-site audit.

The Markdown file is the canonical editable source. The PDF is a generated proof, not the only editable artifact.

## Typesetting pipeline (revision 1.2, 2026-10-05)

The PDF and EPUB editions are both generated from the canonical Markdown through one shared, dependency-free book engine, `scripts/book_typeset.py`:

- **Real paragraphs.** Hard-wrapped source lines are merged into single flowing paragraphs, so re-wrapped lines no longer produce ragged single-word lines. Two-space and `<br>` hard breaks are preserved.
- **Real emphasis.** `*italic*`, `**bold**`, `***both***` and `` `code` `` are rendered in genuine Times italic/bold faces in the PDF and as `<em>`/`<strong>`/`<code>` in the EPUB — no literal asterisks anywhere outside code blocks. Code fences are fence-aware: a `# comment` or `*star*` inside a fence is never treated as a heading or emphasis.
- **Book blocks.** Headings with a visual hierarchy, thematic rules, block quotes, nested bullet and numbered lists (with hanging indents and bullets), pipe tables with alignment and ruled headers, and shaded code blocks.
- **Book apparatus.** The PDF is typeset at the 6 × 9 trim with justified paragraphs, widow/orphan and runt control, running heads, page numbers, and a printed table of contents with dot leaders and page numbers (generated two-pass, so the numbers are exact). The EPUB is split into one XHTML chapter per `# Part`, with a nested navigational TOC, a cover page, a book stylesheet (serif, justified, hyphenation hints), endnotes support, and repository-relative links retargeted to the public GitHub source.
- **Validation.** `scripts/publication_pipeline.py` validates the EPUB after every build (well-formed XML, resolvable manifest and link targets, presence of real emphasis, no empty paragraphs) and fails the build otherwise. `kryptos/audit_manuscript.py` continues to check the PDF header and manuscript word count.

Rebuild commands:

```bash
python3 kryptos/build_manuscript_pdf.py      # KDP 6x9 PDF proof (kryptos/KRYPTOS_SCHOLARLY_MANUSCRIPT.pdf)
python3 scripts/publication_pipeline.py      # EPUB edition + preflight manifest
python3 scripts/build_manuscript_pdf.py      # letter-size PDF of THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md (transfer/)
```

## Editorial reference policy (revision 1.3, 2026-10-05)

The narrative chapters describe methods and verification processes in prose — what was done, what it proved — without pointing at individual repository files, which are meaningless to a general reader. File-level references (scripts, machine-readable records, archived report filenames) appear only in:

- the appendices (Part VII) and the appendix intro's single canonical pointer to the public GitHub repository,
- the explicitly labelled ARCHIVED REPORT / OPEN-WORK ARCHIVE / TECHNICAL REFERENCE / SUPPLEMENT sections, which are verbatim provenance material,
- the embedded manuscript's verification-manifest chapters (Chapter 6, Chapter 7, and the epilogue),
- Part XXI's reference notes (cipher table, how-it-works, language model, installer, CLI, examples), which are software documentation by design.

External source citations (news articles, Paradigm's puzzle pages, the public TTFH/KRYPTOS solver commit) are bibliographic references and remain in the narrative.
