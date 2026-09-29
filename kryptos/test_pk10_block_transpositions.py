import json
import itertools
from collections import Counter
import sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.transsub import _undo_columnar

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

ct10 = cts['PK10']
N = len(ct10)
print(f"PK10 Length: {N}")

def slice_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    iocs = []
    for sl in slices:
        m = len(sl)
        if m <= 1: continue
        c = Counter(sl)
        iocs.append(sum(v * (v - 1) for v in c.values()) / (m * (m - 1)))
    return sum(iocs) / len(iocs) if iocs else 0.0

print(f"Raw PK10 IoC: p7={slice_ioc(ct10, 7):.4f}, p8={slice_ioc(ct10, 8):.4f}, p9={slice_ioc(ct10, 9):.4f}")

units = [2, 3, 4, 6, 7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42]
best_found = (0.0, 0, 0, None, 0)

for u in units:
    for w in [2, 3, 4, 5, 6, 7, 8]:
        if (N % (w * u)) == 0:
            perms = list(itertools.permutations(range(w)))
            # Sample up to 120 perms
            sample = perms if len(perms) <= 120 else perms[:120]
            max_ioc_config = 0.0
            best_p_config = 0
            best_perm_config = None

            for p in sample:
                undone = _undo_columnar(ct10, list(p), incomplete=False, unit=u)
                for period in [7, 8, 9]:
                    val = slice_ioc(undone, period)
                    if val > max_ioc_config:
                        max_ioc_config = val
                        best_p_config = period
                        best_perm_config = p

            if max_ioc_config > 0.046:
                print(f"SPIKE! Unit={u:2d}, Width={w:2d} (Rows={N//(w*u):2d}): max IoC = {max_ioc_config:.5f} at period {best_p_config} (perm {best_perm_config})")
            if max_ioc_config > best_found[0]:
                best_found = (max_ioc_config, u, w, best_perm_config, best_p_config)

print(f"\nOverall Best Block Configuration on PK10:")
print(f"IoC = {best_found[0]:.5f} | Unit = {best_found[1]}, Width = {best_found[2]}, Period = {best_found[4]}, Perm = {best_found[3]}")
