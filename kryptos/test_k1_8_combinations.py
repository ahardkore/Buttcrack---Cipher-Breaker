#!/usr/bin/env python3
"""Systematic combinatorial search over all K1-K8 clues on PK9."""

import json
import itertools

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct9 = cts['PK9']
N = len(ct9)

# K1-8 Vocabulary
KEYWORDS = [
    # PK1
    "PROVENANCE", "ARCHIVE", "PELLEGRIN", "ARCHIVISTS", "TWELVE", "EIGHT",
    # PK2
    "MARGINS", "MARGINALIA", "NEEDLE", "TEXTILES", "TREATISE", "SEVEN",
    "UNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODO",
    # PK3
    "PENTIMENTO", "ORDINATE", "BERN", "ANATOMIST", "SURGICAL", "VIENNESE", "FIFTEEN", "SIX",
    # PK4
    "FURLONGS",
    # PK5
    "FIBERS", "LENS",
    # PK6
    "PORTAL", "WHITESMITH", "WORKSHOP", "TOOLS", "GUTTER", "RESIDUE", "PRACTICE", "MAKING", "TEN",
    # PK7
    "HEARTH", "BELLOWS", "COALS", "FIRE", "HEAT", "WHITE",
    # K1-K4 (Sanborn)
    "KRYPTOS", "PALIMPSEST", "ABSCISSA", "BERLIN", "CLOCK", "EAST", "NORTHEAST",
    # Pellegrin 1530 Title
    "LAFLEURDELASCIENCEDEPOURTRAICTURE", "PATRONSDEBRODERIE", "MORESQUES",
    # Artisan actions
    "ANVIL", "HAMMER", "CRUCIBLE", "FURNACE", "TEMPER", "ANNEAL", "CHISEL",
    "SILVER", "GOLD", "WIRE", "DRAWPLATE", "PUNCHED", "TONGS"
]

print(f"Loaded {len(KEYWORDS)} unique keywords from K1-8.")
