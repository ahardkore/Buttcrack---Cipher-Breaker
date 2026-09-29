# Exhaustive Rare Letter (J, Q, X, Z) Audit across PK9 and PK10
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

# 1. PK9 Rare Letters Audit
print("==========================================================================================")
print("             PK9 RARE LETTER (J, Q, X, Z) AUDIT                                          ")
print("==========================================================================================\n")

pk9_rows = [
    "JVRMBLARDADEFUNCTO",
    "RDQBOOMRBETHSKWJER",
    "EASTYMARINPRAYIALM",
    "SOISEARVEMYLAILEBO",
    "THEEDAMESQUNGLAYIM",
    "IRLOFATSEREDCISANT",
    "IDBYOUSCHESALSOMYR",
    "ELIFORESSESTIAAUON"
]

pk9_full = "".join(pk9_rows)
pk9_core = pk9_full[5:-4]

print(f"Full PK9 (N = {len(pk9_full)}):")
for ch in "JQXZ":
    print(f"  Letter '{ch}': count = {pk9_full.count(ch)}")
print(f"Total rare in full PK9: {sum(pk9_full.count(ch) for ch in 'JQXZ')} / 144 ({sum(pk9_full.count(ch) for ch in 'JQXZ')/144*100:.2f}%)")

print(f"\n135-Character Core (excluding 9 boundary nulls):")
for ch in "JQXZ":
    print(f"  Letter '{ch}': count = {pk9_core.count(ch)}")
print(f"Total rare in PK9 Core: {sum(pk9_core.count(ch) for ch in 'JQXZ')} / 135 ({sum(pk9_core.count(ch) for ch in 'JQXZ')/135*100:.2f}%)")
print("Notice: 'X' count = 0, 'Z' count = 0 in PK9 core! Both are completely eliminated from authentic text.")

# 2. PK10 Rare Letters Audit
print("\n==========================================================================================")
print("             PK10 RARE LETTER (J, Q, X, Z) AUDIT                                         ")
print("==========================================================================================\n")

with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

pk10_rows = [l.split(":")[1].split("(")[0].strip() for l in lines] # 12 rows of 42
pk10_full = "".join(pk10_rows)

print(f"Full PK10 (N = {len(pk10_full)}):")
for ch in "JQXZ":
    print(f"  Letter '{ch}': count = {pk10_full.count(ch)}")
print(f"Total rare in full PK10: {sum(pk10_full.count(ch) for ch in 'JQXZ')} / 504 ({sum(pk10_full.count(ch) for ch in 'JQXZ')/504*100:.2f}%)")

# Partition into Core (36 cols) and Padding (6 cols)
pk10_core_chars = []
pk10_pad_chars = []

for r in range(12):
    row_text = pk10_rows[r]
    # Padding: cols 0, 1 and cols 38..41
    pad_row = row_text[0:2] + row_text[38:42]
    core_row = row_text[2:38]
    pk10_pad_chars.append(pad_row)
    pk10_core_chars.append(core_row)

pad_stream = "".join(pk10_pad_chars)
core_stream = "".join(pk10_core_chars)

print(f"\nPartitioning Rare Letters between Core (432 chars) and Padding (72 chars):")
rare_pad = sum(pad_stream.count(ch) for ch in "JQXZ")
rare_core = sum(core_stream.count(ch) for ch in "JQXZ")
print(f"  Padding Columns (72 chars): {rare_pad} rare letters ({rare_pad/72*100:.2f}%)")
print(f"  Core Grid (432 chars):       {rare_core} rare letters ({rare_core/432*100:.2f}%)")

# Locate every rare letter in Core Grid:
print("\nExact Locations of Rare Letters in PK10 Core Grid:")
for r_idx, r_text in enumerate(pk10_core_chars):
    for c_idx, ch in enumerate(r_text):
        if ch in "JQXZ":
            surround = r_text[max(0, c_idx-3):min(len(r_text), c_idx+4)]
            print(f"  Row {r_idx:2d}, Col {c_idx:2d}: '{ch}' in context ...{surround}...")

rare_letters_list = [ch for ch in pk10_full if ch in "JQXZ"]
print(f"\nAll rare letters in PK10 ({len(rare_letters_list)} total): {' '.join(rare_letters_list)}")
