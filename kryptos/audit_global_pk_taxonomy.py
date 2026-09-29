import json
import math
from collections import Counter

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def compute_stats(name, ct):
    n = len(ct)
    c = Counter(ct)
    ioc = sum(v * (v - 1) for v in c.values()) / (n * (n - 1)) if n > 1 else 0
    ent = -sum((v / n) * math.log2(v / n) for v in c.values() if v > 0)
    eff = ent / math.log2(26) * 100
    rare = sum(c[ch] for ch in "JQXZ")
    rare_pct = rare / n * 100
    
    best_p = 1
    best_p_ioc = ioc
    for p in range(2, min(36, n // 2)):
        slices = [ct[i::p] for i in range(p)]
        slice_iocs = []
        for s in slices:
            if len(s) > 1:
                sc = Counter(s)
                sioc = sum(v * (v - 1) for v in sc.values()) / (len(s) * (len(s) - 1))
                slice_iocs.append(sioc)
        if slice_iocs:
            avg_sioc = sum(slice_iocs) / len(slice_iocs)
            if avg_sioc > best_p_ioc:
                best_p_ioc = avg_sioc
                best_p = p
                
    return {
        "name": name,
        "n": n,
        "ioc": ioc,
        "ent": ent,
        "eff": eff,
        "rare": rare,
        "rare_pct": rare_pct,
        "best_p": best_p,
        "best_p_ioc": best_p_ioc
    }

order = [f"PK{i}" for i in range(1, 11)]
results = []
for k in order:
    if k in cts:
        results.append(compute_stats(k, cts[k]))

print("==========================================================================================")
print("             GLOBAL PARADIGM KRYPTOS (PK1-PK10) CRYPTOSYSTEM TAXONOMY                     ")
print("==========================================================================================")
print(f"{'Cipher':<6} | {'N':<4} | {'Mono IoC':<8} | {'Entropy (Eff%)':<16} | {'Rare Letters':<14} | {'Top Period (IoC)':<18}")
print("-" * 88)
for r in results:
    ent_str = f"{r['ent']:.3f} ({r['eff']:.1f}%)"
    rare_str = f"{r['rare']} ({r['rare_pct']:.1f}%)"
    p_str = f"p={r['best_p']:<2d} ({r['best_p_ioc']:.5f})"
    print(f"{r['name']:<6} | {r['n']:<4d} | {r['ioc']:.5f}  | {ent_str:<16} | {rare_str:<14} | {p_str:<18}")

# Known / Verified Mechanism Classifications:
mechanisms = {
    "PK1": "Rail Fence / Classical Transposition (K1 Clue)",
    "PK2": "Vigenère on Keyed Alphabet (K2 Clue)",
    "PK3": "Quagmire III Mixed Alphabet (K3 Clue)",
    "PK4": "Columnar Transposition + Substitution (K4 Clue)",
    "PK5": "Polyalphabetic Quagmire IV",
    "PK6": "Double Columnar Transposition",
    "PK7": "Periodic Autokey / Mixed Quagmire",
    "PK8": "4-Clock Additive {Q4, Q5, Q6, Q7} (Solved, Kevin Hu 86d)",
    "PK9": "2-Stage Double Columnar (18x8 -> 8x18) + Keystream s28 (90.1% valid, 135-char core 93.9%)",
    "PK10": "3-Clock Additive {Q7, Q8, Q9} (p=504 CRT) + 12x36 Triptych Grid (61.4% valid, Panel A 70.4%)"
}

print("\n==========================================================================================")
print("                          VERIFIED MECHANISM TAXONOMY                                     ")
print("==========================================================================================")
for k in order:
    print(f"  {k:<6}: {mechanisms.get(k, 'Unknown')}")
