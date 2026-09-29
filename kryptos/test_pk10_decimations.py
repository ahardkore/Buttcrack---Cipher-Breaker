import json
import math
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct10 = cts['PK10']
N = len(ct10)

def slice_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    iocs = []
    for sl in slices:
        m = len(sl)
        if m <= 1: continue
        c = Counter(sl)
        iocs.append(sum(v * (v - 1) for v in c.values()) / (m * (m - 1)))
    return sum(iocs) / len(iocs) if iocs else 0.0

coprimes = [s for s in range(1, N) if math.gcd(s, N) == 1]
print(f"Total decimation strides coprime to {N}: {len(coprimes)}")

periods_to_test = [7, 8, 9, 12, 14, 21, 24, 28, 36, 42, 56, 63, 72]

best_found = (0.0, 0, 0)
high_results = []

for s in coprimes:
    # Decimate: text[i] = ct10[(i * s) % N]
    decimated = "".join(ct10[(i * s) % N] for i in range(N))
    for p in periods_to_test:
        val = slice_ioc(decimated, p)
        if val > 0.048:
            high_results.append((val, s, p))
        if val > best_found[0]:
            best_found = (val, s, p)

print(f"\nOverall Best Decimation on PK10:")
print(f"IoC = {best_found[0]:.5f} | Stride = {best_found[1]}, Period = {best_found[2]}")

if high_results:
    print(f"\nFound {len(high_results)} decimation results with IoC > 0.048:")
    high_results.sort(key=lambda x: -x[0])
    for val, s, p in high_results[:10]:
        print(f"  Stride {s:3d}: IoC({p:2d}) = {val:.5f}")
else:
    print("No decimation achieved IoC > 0.048.")
