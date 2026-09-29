import json

with open("pk_all_ciphertexts.json") as f:
    ct = json.load(f)["PK10"]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
b = [5, 5, 8, 7, 16, 10, 22] # Q7 from PK9

# Try all 7 circular cyclic rotations of Q7
from collections import Counter
def get_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    total_pairs = sum(len(sl)*(len(sl)-1) for sl in slices)
    total_coinc = sum(sum(v*(v-1) for v in Counter(sl).values()) for sl in slices)
    return total_coinc / total_pairs if total_pairs > 0 else 0

print("Testing subtraction of Q7 on PK10 across cyclic rotations and phases:")
for rot in range(7):
    cur_b = b[rot:] + b[:rot]
    # Decrypt ct by cur_b[i % 7]
    dec = []
    for i in range(len(ct)):
        c_kr = KRYPTOS.index(ct[i])
        p_kr = (c_kr - cur_b[i % 7] + 26) % 26
        dec.append(KRYPTOS[p_kr])
    dec_str = "".join(dec)
    
    # After subtracting Q7, the remaining cipher has clocks {8, 9}.
    # So its period should be 8, 9, or 72!
    # Check IoC at period 8, 9, 72!
    ioc8 = get_ioc(dec_str, 8)
    ioc9 = get_ioc(dec_str, 9)
    ioc72 = get_ioc(dec_str, 72)
    print(f"Rot {rot}: IoC(8)={ioc8:.4f}, IoC(9)={ioc9:.4f}, IoC(72)={ioc72:.4f}")
