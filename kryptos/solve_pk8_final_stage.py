# Final Stage: Subtract Q5, Q6, Q7 and Solve Q4 directly on PK8
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY"
N = len(PK8_CT)
ct = [KRYPTOS.index(c) for c in PK8_CT]

# Proven decoupled vectors:
q5 = [0, 25, 12, 5, 18]       # from Stride 84
q6 = [0, 0, 8, 17, 10, 18]    # from Stride 140
q7 = [0, 19, 5, 9, 12, 4, 4]  # from Stride 60

# Subtract Q5, Q6, Q7:
Y = []
for t in range(N):
    s_part = (q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26
    y = (ct[t] - s_part + 26) % 26
    Y.append(y)

print("==========================================================================================")
print("             PK8 FINAL STAGE: DECOUPLING Y = C - (Q5 + Q6 + Q7)                           ")
print("==========================================================================================\n")

# Check monogram IoC of the 4 slices of Y:
print("--- Monogram IoC of the 4 slices of Y (mod 4) ---")
for p in range(4):
    slice_chars = [KRYPTOS[Y[t]] for t in range(p, N, 4)]
    c = Counter(slice_chars)
    ioc = sum(v*(v-1) for v in c.values()) / (len(slice_chars)*(len(slice_chars)-1))
    print(f"  Slice {p} (len {len(slice_chars)}): Monogram IoC = {ioc:.5f}")
