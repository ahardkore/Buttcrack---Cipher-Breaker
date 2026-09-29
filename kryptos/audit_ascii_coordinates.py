# Automated ASCII Coordinate Cross-Correlation on PK10 72 Padding Characters
import math

with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

rows = [l.split(":")[1].split("(")[0].strip() for l in lines]

# 6 padding columns (Cols 0, 1 on left, Cols 38..41 on right)
pad_cols = [
    ("Col 0 (PK10 Col 29)", "".join(rows[r][0] for r in range(12))),
    ("Col 1 (PK10 Col 1)",  "".join(rows[r][1] for r in range(12))),
    ("Col 38 (PK10 Col 24)", "".join(rows[r][38] for r in range(12))),
    ("Col 39 (PK10 Col 5)",  "".join(rows[r][39] for r in range(12))),
    ("Col 40 (PK10 Col 4)",  "".join(rows[r][40] for r in range(12))),
    ("Col 41 (PK10 Col 40)", "".join(rows[r][41] for r in range(12))),
]

print("==========================================================================================")
print("             PK10 PADDING CHARACTERS ASCII COORDINATE CORRELATION                         ")
print("==========================================================================================\n")

print("--- 1. ASCII Values & Invariant Signatures ---")
for name, s in pad_cols:
    ascii_vals = [ord(c) for c in s]
    ascii_sum = sum(ascii_vals)
    print(f"{name}: {s}")
    print(f"  ASCII: {ascii_vals} -> Sum = {ascii_sum} (Sum mod 100 = {ascii_sum % 100}, mod 26 = {ascii_sum % 26})")

# Check ASCII of target letters:
print("\n--- 2. ASCII Values of Coordinate Cardinal Letters ---")
for ch in ["N", "W", "M", "E", "S"]:
    print(f"  Letter '{ch}': ASCII = {ord(ch)}")
print("  Notice: ASCII('M') = 77 -> Exact Longitude Degrees of Kryptos (77 deg W)!")

# Check ASCII differences between padding columns:
print("\n--- 3. Pairwise ASCII Column Sum Differences ---")
for i in range(len(pad_cols)):
    for j in range(i+1, len(pad_cols)):
        n1, s1 = pad_cols[i]
        n2, s2 = pad_cols[j]
        sum1 = sum(ord(c) for c in s1)
        sum2 = sum(ord(c) for c in s2)
        diff = abs(sum1 - sum2)
        print(f"  |Sum({n1[-8:-1]}) - Sum({n2[-8:-1]})| = |{sum1} - {sum2}| = {diff:3d} (mod 100 = {diff%100:2d}, mod 60 = {diff%60:2d})")

# Check Row-by-Row ASCII sums of the 6 padding characters
print("\n--- 4. Row-by-Row Padding ASCII Sums (6 chars/row) ---")
for r in range(12):
    p_chars = rows[r][0:2] + rows[r][38:42]
    ascii_vals = [ord(c) for c in p_chars]
    s_ascii = sum(ascii_vals)
    print(f"  Row {r:2d} ({p_chars}): ASCII = {ascii_vals} -> Sum = {s_ascii} (mod 100 = {s_ascii%100:2d}, mod 26 = {s_ascii%26:2d})")

print(f"\nTotal ASCII Sum of all 72 padding characters: {sum(ord(c) for r in range(12) for c in (rows[r][0:2] + rows[r][38:42]))}")
print(f"Average ASCII per padding character: {sum(ord(c) for r in range(12) for c in (rows[r][0:2] + rows[r][38:42])) / 72:.2f} (Expected for A-Z: 77.50)")
