import json

with open("pk_all_ciphertexts.json") as f:
    c = json.load(f)
pk10 = c["PK10"]
N = len(pk10)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
q7_base = [0, 2, 9, 23, 23, 6, 20]

print(f"PK10 Length: {N}")

# We will test both Kryptos alphabet and Standard alphabet
# And both Vigenere (C - K) and Beaufort (K - C)
# Under all 26 shifts of q7

for alph_name, alph in [("Kryptos", ALPH), ("Standard", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")]:
    C = [alph.index(ch) for ch in pk10]
    for mode in ["Vigenere", "Beaufort"]:
        best_p72_ioc = 0
        best_c = 0
        for c_shift in range(26):
            q7 = [(v + c_shift) % 26 for v in q7_base]
            
            # Partially decrypt by removing q7
            part_dec = []
            for t in range(N):
                k7 = q7[t % 7]
                if mode == "Vigenere":
                    p_val = (C[t] - k7 + 26) % 26
                else:
                    p_val = (k7 - C[t] + 26) % 26
                part_dec.append(p_val)
            
            # Now compute average slice IoC at period 72
            # 72 slices, each has 504 / 72 = 7 letters!
            iocs = []
            for s in range(72):
                slice_vals = [part_dec[i] for i in range(s, N, 72)]
                # compute slice IoC
                cnts = {}
                for v in slice_vals:
                    cnts[v] = cnts.get(v, 0) + 1
                ioc = sum(cnt * (cnt - 1) for cnt in cnts.values()) / (7 * 6)
                iocs.append(ioc)
            avg_ioc = sum(iocs) / len(iocs)
            if avg_ioc > best_p72_ioc:
                best_p72_ioc = avg_ioc
                best_c = c_shift
        
        print(f"{alph_name:8s} {mode:8s}: Best Period-72 IoC = {best_p72_ioc:.5f} (at c={best_c})")
