from collections import Counter

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
M = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF"

print(f"Length of M: {len(M)}")
print(f"M: {M}")

print("\n--- 7 Columns of M ---")
for r in range(7):
    col = M[r::7]
    counts = Counter(col).most_common()
    counts_str = " ".join(f"{c}:{n}" for c, n in counts[:6])
    print(f"Col {r} (len {len(col)}): {col}")
    print(f"      Top freqs: {counts_str}")

print("\n--- 14 Columns of M ---")
for r in range(14):
    col = M[r::14]
    counts = Counter(col).most_common()
    counts_str = " ".join(f"{c}:{n}" for c, n in counts[:4])
    print(f"Col {r:2d} (len {len(col):2d}): {col} | Top: {counts_str}")
