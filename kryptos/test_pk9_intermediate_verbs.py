# Automated Crib Test on PK9 Intermediate Columns using Latin & Germanic Metalworking Verbs
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

p2 = [7, 0, 5, 2, 4, 3, 6, 1]
p1 = [15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8]
p2_inv = {p2[i]: i for i in range(8)}
s28 = [25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6]

# Step 1: Recover intermediate matrix mid (8 rows x 18 cols)
# t = p2_inv[r] * 18 + col_mid
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

print("=== PK9 Intermediate Matrix mid (8 rows x 18 cols) ===")
for r in range(8):
    print(f"Row {r}: {mid[r]}")

# Plaintext P under confirmed p1:
P_rows = []
for r in range(8):
    P_rows.append("".join(mid[r][p1[c]] for c in range(18)))

print("\n=== Plaintext P under Confirmed p1 ===")
for r in range(8):
    print(f"Row {r}: {P_rows[r]}")

# Step 2: Test Metalworking Verbs
latin_verbs = [
    "CALFACERE", "EXTINGUERE", "DURARE", "MOLLIRE", "SCULPERE", "INCIDERE",
    "FUNDERE", "FLARE", "COQUERE", "PURGARE", "LIMARE", "POLIRE", "TUNDERE",
    "DUCTARE", "DEAURARE", "ADURERE", "SECARE", "FUNGERE", "MISCERE", "COAGULARE"
]

germanic_verbs = [
    "SEAR", "QUENCH", "SMELT", "FORGE", "HAMMER", "CHISEL", "GRAVE", "ENGRAVE",
    "CAST", "SOLDER", "BRAZE", "TEMPER", "HARDEN", "SOFTEN", "BLOW", "DRAW",
    "BEAT", "POUND", "FILE", "BURNISH", "POLISH", "CLEAVE", "PIERCE", "WELD",
    "LARD", "BOIL", "HEAT", "MELT", "FLUX", "COOL", "DAMP", "SEARE"
]

all_verbs = sorted(list(set(latin_verbs + germanic_verbs)))
print(f"\nLoaded {len(all_verbs)} Latin and Germanic metalworking verbs.")

# Check which verbs are already present in P_rows
print("\n--- 1. Verbs Directly Present in Decrypted Plaintext Rows ---")
found_verbs = []
for r_idx, r_text in enumerate(P_rows):
    for v in all_verbs:
        pos = r_text.find(v)
        if pos != -1:
            found_verbs.append((v, r_idx, pos))
            print(f"  Verb \"{v}\" found in Row {r_idx} at pos {pos}: ...{r_text[max(0, pos-2):min(18, pos+len(v)+2)]}...")

# Check cross-row verbs (e.g. Row 3 -> 4, Row 5 -> 6)
full_p = "".join(P_rows)
print("\n--- 2. Verbs Present across Row Wraps / Full Stream ---")
for v in all_verbs:
    pos = full_p.find(v)
    if pos != -1 and not any(v == fv[0] for fv in found_verbs):
        print(f"  Verb \"{v}\" found in continuous stream at char {pos}: ...{full_p[max(0, pos-3):min(len(full_p), pos+len(v)+3)]}...")

# Step 3: Anagram check on each row of mid:
# Can any unused verb be formed as an anagram within any row of mid?
print("\n--- 3. Verbs Formable as Subsets / Anagrams within Rows of mid ---")
from collections import Counter
for r_idx in range(8):
    c_row = Counter(mid[r_idx])
    formable = []
    for v in all_verbs:
        if len(v) >= 4 and all(c_row[ch] >= Counter(v)[ch] for ch in Counter(v)):
            formable.append(v)
    if formable:
        print(f"  Row {r_idx} can form verbs: {formable}")
