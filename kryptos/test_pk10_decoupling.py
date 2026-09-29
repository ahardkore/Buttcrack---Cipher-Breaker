import json
from collections import Counter

cts = json.load(open("pk_all_ciphertexts.json"))
pk10 = cts["PK10"]
N = len(pk10)
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
std_to_kr = {c: i for i, c in enumerate(ALPH)}
kr_to_std = {i: c for i, c in enumerate(ALPH)}

def ioc(s):
    n = len(s)
    if n <= 1: return 0.0
    c = Counter(s)
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1))

def avg_slice_ioc(arr, p):
    slices = [arr[i::p] for i in range(p)]
    iocs = [ioc(s) for s in slices if len(s) > 1]
    return sum(iocs) / len(iocs) if iocs else 0.0

print(f"Testing PK10 Difference Decoupling on Raw Ciphertext (N = {N})...")

for name, alph_map in [("Standard", lambda c: ord(c) - ord('A')), ("Kryptos", lambda c: std_to_kr[c])]:
    c_vals = [alph_map(c) for c in pk10]
    print(f"\n--- Alphabet: {name} ---")

    # Lag 72 (mod 8=0, mod 9=0) -> should have period 7
    diff_72 = [(c_vals[i+72] - c_vals[i]) % 26 for i in range(N - 72)]
    ioc_d72_p7 = avg_slice_ioc(diff_72, 7)
    ioc_d72_p1 = ioc(diff_72)
    print(f"Lag 72 (eliminates Q8, Q9): Overall IoC = {ioc_d72_p1:.5f}, Slice IoC (p=7) = {ioc_d72_p7:.5f}")

    # Lag 63 (mod 7=0, mod 9=0) -> should have period 8
    diff_63 = [(c_vals[i+63] - c_vals[i]) % 26 for i in range(N - 63)]
    ioc_d63_p8 = avg_slice_ioc(diff_63, 8)
    ioc_d63_p1 = ioc(diff_63)
    print(f"Lag 63 (eliminates Q7, Q9): Overall IoC = {ioc_d63_p1:.5f}, Slice IoC (p=8) = {ioc_d63_p8:.5f}")

    # Lag 56 (mod 7=0, mod 8=0) -> should have period 9
    diff_56 = [(c_vals[i+56] - c_vals[i]) % 26 for i in range(N - 56)]
    ioc_d56_p9 = avg_slice_ioc(diff_56, 9)
    ioc_d56_p1 = ioc(diff_56)
    print(f"Lag 56 (eliminates Q7, Q8): Overall IoC = {ioc_d56_p1:.5f}, Slice IoC (p=9) = {ioc_d56_p9:.5f}")
