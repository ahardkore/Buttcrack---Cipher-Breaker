#!/usr/bin/env python3
"""Rebuild the PK9 wheel vocabularies correctly.

The normalized plaintexts contain no spaces, so word tokenization must run on
the original punctuated source texts (see verify_pk_constructions.py), not on
the normalized streams.  This builder produces:

  pk9_vocab_story{5,6,7,8}.txt  story word tokens + word-aligned spans
  pk9_vocab_broad{5,6,7}.txt    story vocab + the repo's curated craft lists
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
import importlib.util

spec = importlib.util.spec_from_file_location("vpc", ROOT / "verify_pk_constructions.py")
vpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpc)  # noqa: S307  (module runs no code on import guard)

SOURCE_TEXTS = [spec_["plaintext"] for spec_ in vpc.CONSTRUCTIONS.values()]
STORY_WORDS: list[list[str]] = []
for text in SOURCE_TEXTS:
    for sent in re.split(r"[.;:]", text):
        ws = [w.upper() for w in re.findall(r"[A-Za-z]+", sent)]
        if ws:
            STORY_WORDS.append(ws)

spans: dict[int, set[str]] = {5: set(), 6: set(), 7: set(), 8: set()}
for ws in STORY_WORDS:
    for i in range(len(ws)):
        L = len(ws[i])
        if 5 <= L <= 8:
            spans[L].add(ws[i])
        for j in range(i + 1, min(i + 4, len(ws))):
            span = "".join(ws[i : j + 1])
            L = len(span)
            if 5 <= L <= 8:
                spans[L].add(span)
            elif L > 8:
                break

EXTRA = {}
for w in """
PROVENANCE MARGINS ORDINATE PENTIMENTO UNDERLAY OCHRE VERDIGRIS TWOYEARS
HANDIWORK SMITHWORK PORTAL ANNEAL ALCHEMIST METE METER METIER MASTERY KRYPTOS
PARADIGM SHADOW SHADOWS BERLIN CLOCK CLOCKS LANGLEY NORTHEA EASTNOR NORTHEAST
ABSCISSA PALIMPSEST SUBTLE SHADING ABSENCE NUANCE IQLUSION TOTALLY INVISIBLE
POSSIBLE EARTHS MAGNETIC FIELD INFORMATION GATHERED TRANSMITTED SLOWLY
DECRYPTABLY BETWEEN DIGETAL REGIONS UNDERNEATH RIVER FINEST STEEL WIRES SILVER
COPPER GOLDEN IRON WORK ANVIL TONGS FORGE HAMMERS CHISEL BELLOWS CRUCIBLE
FURNACE GRINDSTONES POLISH POLISHED ENGRAVING ENGRAVED CASTING MOLDING TEMPER
TEMPERED QUENCH QUENCHED ANNEALED ANNEALING SOLDER SOLDERED SMELT SMELTED INGOT
INGOTS BRASS BRONZE METAL METALS NEEDLE NEEDLES KNOT KNOTS ARCHIVE ARCHIVES
TEACHER STUDENT MASTER MASTERS GUTTER GUTTERS LETTER LETTERS WORKSHOP BARN
BARNS STRAW STRAWS BALE BALES FODDER LATTICE EMBER EMBERS AZURE UMBER INDIGO
VERDANT PATINA GILDING GILDED ALLOY ALLOYS DRAWN DRAWING DREW FILE FILES FILING
GRIND GRINDER LATH LATHE MOULD PRICK PRICKED BLOOD FINGER FINGERS DAWN SUNRISE
NOON MIDNIGHT GRATEFUL DEPART FAREWELL GOODBYE JOURNEY ROAD ROADS ALPINE VENNA
BERNE VIENNA ANATOMIST SURGEON SURGICAL PELLEGRIN ACCESSION MARGINALIA
TREATISE TEXTILES TIGHTLY WOUND UNRAVEL UNRAVELED REVEALED ROUTE TWELVE FAILED
CORRESPONDENTS COUNTRIES SEEKING LEGENDS INSTRUMENT DEMONSTRATION ADDRESS
ANSWER MANNER ARCHIVIST EXAMINING EXQUISITE RESIDUE PRACTICE STUDY YEARS PEACE
CALLING AWAIT AWAITING WHITESMITH SOTTILE LEGGERE TANTO QUALUNQUE
""".split():
    if 5 <= len(w) <= 8:
        EXTRA.setdefault(len(w), set()).add(w)
for L, ws in EXTRA.items():
    spans[L] |= ws


def dump(path: Path, words: set[str]) -> int:
    lst = sorted(words)
    path.write_text("\n".join(lst) + "\n")
    return len(lst)


for L in (5, 6, 7, 8):
    print(f"story vocab len {L}: {dump(ROOT / f'pk9_vocab_story{L}.txt', spans[L])}")

for L in (5, 6, 7):
    curated = ROOT / f"curated_w{L}.txt"
    words = set(spans[L])
    if curated.exists():
        words |= {w.strip().upper() for w in curated.read_text().split() if len(w.strip()) == L}
    print(f"broad vocab len {L}: {dump(ROOT / f'pk9_vocab_broad{L}.txt', words)}")

# sanity: the precedent keys must now be present
for probe in ("TWOYEARS", "TENYEARS", "OCHRE", "VERDIGRIS", "UNDERLAY", "ANNEALED"):
    L = len(probe)
    if L <= 8:
        got = (ROOT / f"pk9_vocab_story{L}.txt").read_text().split()
        print(probe, "present:", probe in got)
    else:
        print(probe, "present: not a wheel length")
