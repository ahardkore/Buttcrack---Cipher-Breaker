import numpy as np, sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.additive_crib import _periods, _row, _alphabet

pk8 = 'COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY'
alpha = _alphabet('KRYPTOS')
index = {c: i for i, c in enumerate(alpha)}
ct_kr = np.array([index[c] for c in pk8], dtype=int)

print("Testing period-30 (5, 6) residual properties on PK8...")

# Check the coset sizes for period 30 on length 153:
# Indices: 0..152
# Slices t % 30:
for r in range(30):
    sub = ct_kr[r::30]
    # sub has 5 or 6 letters
print(f"30 cosets of length 5 or 6 letters across 153 characters.")
