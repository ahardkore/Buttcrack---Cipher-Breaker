import sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.transsub import _undo_columnar
import json
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    ct9 = json.load(f)['PK9']

order = [3, 5, 1, 4, 2, 0]
undone = _undo_columnar(ct9, order, incomplete=False, unit=3)

print("undone (len 144):")
print(undone)

# Print 7 columns of undone
cols = [undone[i::7] for i in range(7)]
print("\n--- The 7 Columns of undone ---")
for c in range(7):
    cnt = Counter(cols[c])
    top = ' '.join(f'{k}:{v}' for k, v in cnt.most_common(4))
    n = len(cols[c])
    ioc = sum(v * (v - 1) for v in cnt.values()) / (n * (n - 1))
    print(f"Col {c} (len {n:2d}): {cols[c]} | IoC={ioc:.5f} | {top}")

