# Automated Nautical & Maritime Navigation Lexicon Audit on PK9
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

p2 = [7, 0, 5, 2, 4, 3, 6, 1]
p1 = [15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8]
p2_inv = {p2[i]: i for i in range(8)}
s28 = [25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6]

# Recover intermediate matrix mid (8 rows x 18 cols)
mid = []
for r in range(8):
    row_chars = []
    for c_mid in range(18):
        t = p2_inv[r] * 18 + c_mid
        phase = t % 28
        shift = s28[phase]
        ct = PK9_RAW[t]
        ct_idx = KRYPTOS.index(ct)
        pt_idx = (ct_idx - shift + 26) % 26
        row_chars.append(KRYPTOS[pt_idx])
    mid.append("".join(row_chars))

# Plaintext P under confirmed p1:
P_rows = ["".join(mid[r][p1[c]] for c in range(18)) for r in range(8)]
full_p = "".join(P_rows)

print("==========================================================================================")
print("             PK9 NAUTICAL & MARITIME NAVIGATION LEXICON AUDIT                             ")
print("==========================================================================================\n")

nautical_terms = [
    "ANCHOR", "BEACON", "BOOM", "BOW", "CABIN", "CAPSTAN", "CHART", "CLEAT",
    "COMPASS", "CORDAGE", "CURRENT", "DECK", "DEPTH", "DRIFT", "EAST", "FATHOM",
    "FLOTILLA", "GALE", "HARBOR", "HAVEN", "HELM", "HULL", "KEEL", "KNOT",
    "LASH", "LATITUDE", "LEAGUE", "LONGITUDE", "MANOWAR", "MARIN", "MARINER",
    "MAST", "MOOR", "NAUTICAL", "NAVY", "NORTH", "OAR", "OARS", "PILOT",
    "PINNACE", "PORT", "PROW", "QUAY", "REEF", "RIG", "RUDDER", "SAIL",
    "SEAMAN", "SECTOR", "SESTIA", "SEXTANT", "SHIP", "SHORE", "SOUND",
    "SOUTH", "SPAR", "STARBOARD", "STERN", "STORM", "SURF", "SURGE",
    "TACK", "TIDE", "TIMBER", "TRANSIT", "VESSEL", "VOYAGE", "WAKE",
    "WATCH", "WATER", "WAVE", "WEST", "WHARF", "WIND", "YACHT", "YAWL"
]

print(f"Loaded {len(nautical_terms)} Early Modern English nautical and navigation terms.\n")

# 1. Direct matches in Plaintext Rows
print("--- 1. Direct Nautical Matches in PK9 Plaintext Rows ---")
found_terms = []
for r_idx, r_text in enumerate(P_rows):
    for term in nautical_terms:
        pos = r_text.find(term)
        if pos != -1:
            found_terms.append((term, r_idx, pos))
            surround = r_text[max(0, pos-3):min(18, pos+len(term)+3)]
            print(f"  Term \"{term:8s}\" found in Row {r_idx:2d} at pos {pos:2d}: ...{surround}...")

# 2. Continuous Stream Matches across Row Wraps
print("\n--- 2. Continuous Stream Matches across Row Wraps ---")
for term in nautical_terms:
    pos = full_p.find(term)
    if pos != -1 and not any(term == ft[0] for ft in found_terms):
        surround = full_p[max(0, pos-4):min(len(full_p), pos+len(term)+4)]
        print(f"  Term \"{term:8s}\" found across wrap at char {pos:3d}: ...{surround}...")

# 3. Anagram Subsets in Rows of mid
print("\n--- 3. Nautical Terms Formable as Anagram Subsets in mid Rows ---")
from collections import Counter
for r_idx in range(8):
    c_mid = Counter(mid[r_idx])
    formable = []
    for term in nautical_terms:
        if len(term) >= 4:
            cw = Counter(term)
            if all(c_mid[ch] >= cw[ch] for ch in cw):
                formable.append(term)
    if formable:
        print(f"  Row {r_idx:2d} can form nautical terms: {formable}")

# 4. Homophonic and Dual-Thematic Analysis:
print("\n=== 4. Thematic Fusion: Metallurgy + Naval/River Harbor Defense ===")
print("  - BOOM:   Naval harbor defense spar (Potomac River Langley boom) & crucible flue spar.")
print("  - MARIN:  Ye mariner (traditional sea/celestial navigation dedication toward EAST).")
print("  - EAST:   Compass cardinal direction (Sanborn confirmed K4 anchor).")
print("  - SESTIA: Sestia / sextus / sextant (dividing navigational compass / balance).")
print("  - ORES:   Metal ores (homophone of OARS, the mariner oars).")
