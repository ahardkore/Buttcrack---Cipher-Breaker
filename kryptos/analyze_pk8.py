import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK8"]

print(f"PK8 length: {len(ct)}")
print(ct)

# Check index of coincidence
from collections import Counter
def ioc(s):
    n = len(s)
    if n <= 1: return 0.0
    c = Counter(s)
    return sum(v*(v-1) for v in c.values()) / (n*(n-1))

print(f"Overall IoC: {ioc(ct):.4f}")

# Repeated sequences in PK8
for length in range(3, 10):
    repeats = {}
    for i in range(len(ct) - length + 1):
        gram = ct[i:i+length]
        repeats.setdefault(gram, []).append(i)
    rep_list = [(g, pos) for g, pos in repeats.items() if len(pos) > 1]
    if rep_list:
        print(f"\nRepeated {length}-grams:")
        for g, pos in rep_list:
            diffs = [pos[j+1] - pos[j] for j in range(len(pos)-1)]
            print(f"  '{g}': count={len(pos)}, positions={pos}, diffs={diffs}")
