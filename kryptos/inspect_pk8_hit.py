import sys, json
sys.path.insert(0, '/home/user/buttcrack/src')
from buttcrack.additive_crib import solve_additive_crib

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct8 = cts['PK8']

res = solve_additive_crib(ct8, [4, 5, 6, 7], [(130, "WITHOUTPROPERHEAT")], alphabet='KRYPTOS')
print("Consistent:", res['consistent'])
print("Determined positions:", len(res['determined_positions']))
print("Plaintext:")
pt = res['plaintext']
print(pt)

# Print in lines of 30
for i in range(0, len(pt), 30):
    print(f"{i:3d}: {pt[i:i+30]}")
