#!/usr/bin/env python3
"""Build staged PK9 wheel-word vocabularies from the verified story.

The author's keys are consistently thematic: PROVENANCE, MARGINS, ORDINATE,
PENTIMENTO, UNDERLAY, OCHRE, VERDIGRIS, TWOYEARS, HANDIWORK, SMITHWORK,
PORTAL, ANNEAL, ALCHEMIST, METE/METER/METIER/MASTERY.  PK9 needs 5-, 6- and
7-letter Q wheels plus an 8-letter T keyword.

Stages:
  pk9_vocab_story{5,6,7,8}.txt  - tight, high-prior (story tokens+spans,
                                  prior keys, Kryptos vocabulary, craft words)
  pk9_vocab_broad{5,6,7}.txt    - the same plus the repo's curated craft lists
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOL = json.loads((ROOT / "pk_verified_solutions.json").read_text())

STORY = " ".join(SOL[pk]["plaintext"] for pk in ("PK1", "PK2", "PK3", "PK4", "PK5", "PK6", "PK7", "PK8"))

# ---- 1. story tokens and word-aligned spans -----------------------------------
sentences = [s for s in re.split(r"[.]", STORY) if s.strip()]
tokens = [t for t in re.findall(r"[A-Z]+", STORY)]

spans: dict[int, set[str]] = {5: set(), 6: set(), 7: set(), 8: set()}
for sent in sentences:
    words = re.findall(r"[A-Z]+", sent)
    for i in range(len(words)):
        # single words
        L = len(words[i])
        if 5 <= L <= 8:
            spans[L].add(words[i])
        # 2-3 word aligned spans (author precedent: TWOYEARS = TWO YEARS)
        for j in range(i + 1, min(i + 4, len(words))):
            span = "".join(words[i:j + 1])
            L = len(span)
            if 5 <= L <= 8:
                spans[L].add(span)
            elif L > 8:
                break

# ---- 2. prior keys and Kryptos vocabulary -------------------------------------
EXTRA = """
PROVENANCE MARGINS ORDINATE PENTIMENTO UNDERLAY OCHRE VERDIGRIS TWOYEARS
HANDIWORK SMITHWORK PORTAL ANNEAL ALCHEMIST METE METER METIER MASTERY KRYPTOS
SHADOW SHADOWS BERLIN CLOCK CLOCKS LANGLEY NORTHEA EASTNOR NORTHEAST ABSCISSA
PALIMPSEST SUBTLE SHADING ABSENCE NUANCE IQLUSION TOTALLY INVISIBLE POSSIBLE
EARTHS MAGNETIC FIELD INFORMATION GATHERED TRANSMITTED SLOWLY DECRYPTABLY
BETWEEN DIGETAL REGIONS UNDERNEATH RIVER FINEST STEEL WIRES SILVER COPPER
GOLDEN IRON WORK ANVIL TONGS FORGE HAMMERS CHISEL BELLOWS CRUCIBLE FURNACE
GRINDSTONES POLISH POLISHED ENGRAVING ENGRAVED CASTING MOLDING TEMPER TEMPERED
QUENCH QUENCHED ANNEALED ANNEALING SOLDER SOLDERED SMELT SMELTED INGOT INGOTS
BRASS BRONZE METAL METALS NEEDLE NEEDLES KNOT KNOTS ARCHIVE ARCHIVES TEACHER
STUDENT MASTER MASTERS GUTTER GUTTERS LETTER LETTERS WORKSHOP BARN BARNS
STRAW STRAWS BALE BALES FODDER LATTICE EMBER EMBERS AZURE UMBER INDIGO VERDANT
PATINA GILDING GILDED ALLOY ALLOYS DRAWN DRAWING DREW FILE FILES FILING GRIND
GRINDER LATH LATHE MOULD PRICK PRICKED BLOOD FINGER FINGERS DAWN SUNRISE NOON
MIDNIGHT GRATEFUL DEPART FAREWELL GOODBYE JOURNEY ROAD ROADS ALPINE VENNA
BERNE VIENNA ANATOMIST SURGEON SURGICAL PELLEGRIN ACCESSION MARGINALIA
TREATISE TEXTILES TIGHTLY WOUND UNRAVEL UNRAVELED REVEALED ROUTE TWELVE
FAILED CORRESPONDENTS COUNTRIES SEEKING LEGENDS INSTRUMENT DEMONSTRATION
ADDRESS ANSWER MANNER ARCHIVIST EXAMINING EXQUISITE RESIDUE PRACTICE STUDY
YEARS PEACE CALLING AWAIT AWAITING WHITESMITH SOTTILE LEGGERE TANTO QUALUNQUE
"""
for w in EXTRA.split():
    if 5 <= len(w) <= 8:
        spans[len(w)].add(w)

# ---- 3. write staged files -----------------------------------------------------
def dump(path: Path, words: set[str]) -> int:
    lst = sorted(words)
    path.write_text("\n".join(lst) + "\n")
    return len(lst)


story_counts = {}
for L in (5, 6, 7, 8):
    n = dump(ROOT / f"pk9_vocab_story{L}.txt", spans[L])
    story_counts[L] = n
    print(f"story vocab len {L}: {n}")

# broad stage: story vocab + curated craft lists (already deduped by the repo)
for L in (5, 6, 7):
    curated = ROOT / f"curated_w{L}.txt"
    words = set(spans[L])
    if curated.exists():
        words |= {w.strip().upper() for w in curated.read_text().split() if len(w.strip()) == L}
    n = dump(ROOT / f"pk9_vocab_broad{L}.txt", words)
    print(f"broad vocab len {L}: {n}")

# 8-letter T-keyword candidates (story words only; the sweep also has an
# all-permutations mode)
print("8-letter T-key candidates:", story_counts[8])
