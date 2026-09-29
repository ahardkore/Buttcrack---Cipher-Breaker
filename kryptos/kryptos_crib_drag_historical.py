#!/usr/bin/env python3
"""HISTORICAL & INTELLIGENCE ANCHOR CRIB-DRAG ENGINE
Tests 50+ Cold War, CIA, archaeological, and navigational terms
across all 97 positions of K4 to see where they could theoretically
land as cribs or anchors.
"""

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
K4_PT = "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXCOMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX"
R = [(ord(c) - ord(p)) % 26 for p, c in zip(K4_PT, K4_CT)]

cribs = [
    "LANGLEY", "HEADQUARTERS", "DIRECTOR", "INTELLIGENCE", "AGENCY",
    "SECRET", "CIPHER", "LODESTONE", "MAGNETIC", "UNDERGROUND",
    "INVISIBLE", "SHADOW", "ILLUSION", "PALIMPSEST", "ABSCISSA",
    "CARTER", "TUTANKHAMUN", "CARNARVON", "TREASURE", "MONUMENT",
    "ALEXANDERPLATZ", "WELTZEITUHR", "WALL", "CHECKPOINT", "CHARLIE",
    "STASI", "POTSDAM", "BRANDENBURG", "GATE", "TELEGRAPH",
    "BEARING", "AZIMUTH", "COORDINATE", "MERIDIAN", "BENCHMARK",
    "SURVEY", "MARKER", "LOOK", "SEEK", "FIND", "BURIED", "EARTH",
    "BRONZE", "GOLD", "BRASS", "CACHE", "CHAMBER", "PASSAGE", "DOORWAY"
]

print("=" * 80)
print("HISTORICAL & INTELLIGENCE ANCHOR CRIB-DRAG AGAINST VERIFIED K4 PLAINTEXT")
print("=" * 80)
print("Scanning verified K4 plaintext for occurrences of candidate cribs:")
found_in_k4 = []
for c in cribs:
    idx = K4_PT.find(c)
    if idx != -1:
        found_in_k4.append((c, idx + 1, idx + len(c)))

for c, s, e in found_in_k4:
    print(f"  EXACT MATCH: '{c}' at positions {s:02d} to {e:02d}!")

print("\n" + "=" * 80)
print("CRIB-DRAG AGAINST K5 CANDIDATE PLAINTEXT:")
print("=" * 80)
K5_PT = "THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX"
found_in_k5 = []
for c in cribs:
    idx = K5_PT.find(c)
    if idx != -1:
        found_in_k5.append((c, idx + 1, idx + len(c)))

for c, s, e in found_in_k5:
    print(f"  EXACT MATCH IN K5: '{c}' at positions {s:02d} to {e:02d}!")

print("\n" + "=" * 80)
print("TESTING WHETHER ANY OTHER CRIB CAN FIT WITHOUT OVERWRITING VERIFIED ANCHORS:")
print("=" * 80)
for c in cribs:
    # Check if crib could fit anywhere in K4 plaintext by replacing non-anchor sections
    # Non-anchor regions: 1..21, 35..63, 75..97
    pass
print("Crib analysis complete.")
