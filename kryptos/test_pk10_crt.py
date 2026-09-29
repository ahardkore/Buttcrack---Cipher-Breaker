import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
b = [5, 5, 8, 7, 16, 10, 22] # Q7 from PK9

# If Q7 is known:
# For each of 504 positions, we subtract Q7[i % 7]:
z = []
for i in range(504):
    c_kr = KRYPTOS.index(ct[i])
    p_kr = (c_kr - b[i % 7] + 26) % 26
    z.append(KRYPTOS[p_kr])
z = "".join(z)

from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

print(f"z Period 72 IoC: {get_ioc(z, 72):.4f}")
print(f"z Period  8 IoC: {get_ioc(z,  8):.4f}")
print(f"z Period  9 IoC: {get_ioc(z,  9):.4f}")
