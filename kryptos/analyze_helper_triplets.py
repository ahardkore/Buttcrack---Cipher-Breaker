import sys

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
HELPER_T = (
    "WXZK"
    "YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR"
    "ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY"
    "_ABCDEFGHIJKLMNOPQRSTUVWXYZABCD"
)
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

print(f"{'Pos':>3} | {'CT':>2} {'PT':>2} {'T':>2} | {'R_std':>5} {'T_std':>5} {'Diff_std':>8} {'Sum_std':>7} | {'R_kr':>5} {'T_kr':>5} {'Diff_kr':>7} {'Sum_kr':>6}")
print("-" * 75)

for pos in sorted(CRIBS.keys()):
    c = K4_CT[pos]
    p = CRIBS[pos]
    t = HELPER_T[pos]
    
    # Standard:
    c_s = ALPH_STD.index(c)
    p_s = ALPH_STD.index(p)
    t_s = ALPH_STD.index(t) if t != '_' else -1
    r_s = (c_s - p_s) % 26
    diff_s = (r_s - t_s) % 26 if t_s != -1 else -1
    sum_s = (r_s + t_s) % 26 if t_s != -1 else -1
    
    # Kryptos:
    c_k = ALPH_K.index(c)
    p_k = ALPH_K.index(p)
    t_k = ALPH_K.index(t) if t != '_' else -1
    r_k = (c_k - p_k) % 26
    diff_k = (r_k - t_k) % 26 if t_k != -1 else -1
    sum_k = (r_k + t_k) % 26 if t_k != -1 else -1
    
    print(f"{pos+1:3d} | {c:>2} {p:>2} {t:>2} | {r_s:5d} {t_s:5d} {diff_s:8d} {sum_s:7d} | {r_k:5d} {t_k:5d} {diff_k:7d} {sum_k:6d}")

