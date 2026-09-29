# Let us test if the shifts in PK9 are:
# Model A: CT = (PT_transposed + Key)
# Model B: CT = (PT + Key)_transposed

# In Model A:
# ct_i = pt_transposed_i + key_i (key_i has period 28 along the ciphertext).
# Then pt_transposed_i = ct_i - key_i.
# And pt_transposed is arranged as 12 columns of 12 rows.
# Under column permutation perm: pt[r*12 + c] = pt_transposed[perm[c]*12 + r].

# In Model B:
# intermediate_i = pt_i + key_i (key_i has period 28 along the plaintext).
# Then CT is the transposition of intermediate.
# Under column permutation perm: CT[c*12 + r] = intermediate[r*12 + perm[c]]?

# Let us verify the IoC of Model A vs Model B:
# On raw ciphertext, period 28 has IoC = 0.0633.
# If Model B were true (transposition applied to intermediate text),
# would raw ciphertext have a high IoC at period 28?
# Let us simulate Model B and see what the IoC of CT is!

import random
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
english_sample = "THESECRETOFTHEKRYPTOSSCULPTUREATTHECENTRALINTELLIGENCEAGENCYHASREMAINEDUNSOLVEDFORDECADEBYPROFESSIONALANDAMATEURCRYPTANALYSTSWORLDWIDEACROSSALLCONTINENTS"

# Let pt be english text of length 144
pt = english_sample[:144]
# Add period 28 key
key28 = [random.randint(0, 25) for _ in range(28)]
inter = "".join(KRYPTOS[(KRYPTOS.index(pt[i]) + key28[i % 28]) % 26] for i in range(144))

# Now transpose inter with width 12
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]
# Transposition: write row-by-row, read col-by-col
ct = [""] * 144
for c in range(12):
    for r in range(12):
        ct[c * 12 + r] = inter[r * 12 + perm[c]]
ct = "".join(ct)

from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

print("Simulation of Model B (Transposition AFTER Substitution):")
print(f"CT Period 28 IoC: {get_ioc(ct, 28):.4f}")
print(f"CT Period  7 IoC: {get_ioc(ct,  7):.4f}")
print(f"CT Period 12 IoC: {get_ioc(ct, 12):.4f}")

# Now simulate Model A (Transposition BEFORE Substitution):
# PT is transposed first into inter:
inter_A = [""] * 144
for c in range(12):
    for r in range(12):
        inter_A[c * 12 + r] = pt[r * 12 + perm[c]]
inter_A = "".join(inter_A)
# Then encrypted with key28:
ct_A = "".join(KRYPTOS[(KRYPTOS.index(inter_A[i]) + key28[i % 28]) % 26] for i in range(144))
print("\nSimulation of Model A (Transposition BEFORE Substitution):")
print(f"CT Period 28 IoC: {get_ioc(ct_A, 28):.4f}")
print(f"CT Period  7 IoC: {get_ioc(ct_A,  7):.4f}")
print(f"CT Period 12 IoC: {get_ioc(ct_A, 12):.4f}")
