"""Numerical observations about the PK8-PK10 parameter sets.

READ THIS FIRST.  Despite the file name and the word "THEOREM" below, nothing
here verifies a cipher, a key or a plaintext.  Each section computes an
arithmetic identity among quantities chosen after the fact -- lcm of the clock
periods, sums of selected letters, a grid width picked to match a period --
and prints it as proved.  The GPS section is the clearest case: it sums four
chosen letters to reach 57, then takes a different chosen sum modulo 60 to
reach 6.  With enough freedom in what to add and what modulus to apply, any
target can be hit, so none of this is evidence about the sculpture or the
ciphers.

None of these identities was used to break anything.  The claims that *can* be
checked against the ciphertexts live in verify_pk_records.py, which
re-encrypts each stored plaintext under the key its record names.  See
AUDIT.md.
"""
# Comprehensive Mathematical Verification of All Cryptanalytic Theorems across PK8, PK9, PK10
import math

print("==========================================================================================")
print("             ARITHMETIC IDENTITIES AMONG THE PK8-PK10 PARAMETERS (NOT EVIDENCE)               ")
print("==========================================================================================\n")

# Theorem 1: CRT Single-Cycle & Keystream Periods
print("--- THEOREM 1: CHINESE REMAINDER THEOREM PERIOD PROGRESSION ---")
def lcm(a, b): return abs(a * b) // math.gcd(a, b)
def lcm_list(nums):
    res = nums[0]
    for n in nums[1:]: res = lcm(res, n)
    return res

p_pk8 = lcm_list([4, 5, 6, 7])
p_pk9 = lcm_list([4, 7])
p_pk10 = lcm_list([7, 8, 9])

print(f"PK8:  Clocks {{4, 5, 6, 7}} -> Period = lcm(4,5,6,7) = {p_pk8} (Ciphertext length = 153)")
print(f"PK9:  Clocks {{4, 7}}       -> Period = lcm(4,7)     = {p_pk9}  (Ciphertext length = 144)")
print(f"PK10: Clocks {{7, 8, 9}}    -> Period = lcm(7,8,9)   = {p_pk10} (Ciphertext length = 504)")

gcd_78 = math.gcd(7, 8)
gcd_79 = math.gcd(7, 9)
gcd_89 = math.gcd(8, 9)
print(f"Pairwise coprimality in PK10: gcd(7,8)={gcd_78}, gcd(7,9)={gcd_79}, gcd(8,9)={gcd_89}")
print("Proof: Since all clocks are pairwise coprime, the keystream forms a single non-repeating")
print(f"CRT cycle covering all 504 characters: 7 x 8 x 9 = {7 * 8 * 9} = N_PK10.\n")

# Theorem 2: Isophasic Columnar Invariant
print("--- THEOREM 2: ISOPHASIC COLUMNAR INVARIANT & 2D TORUS DUALITY ---")
H = 12
gcd_h7 = math.gcd(H, 7)
gcd_h8 = math.gcd(H, 8)
gcd_h9 = math.gcd(H, 9)
v_per7 = 7 // gcd_h7
v_per8 = 8 // gcd_h8
v_per9 = 9 // gcd_h9
v_total = lcm_list([v_per7, v_per8, v_per9])
print(f"Row height H = {H}")
print(f"  Clock 7: gcd(12, 7) = {gcd_h7} -> Vertical Period = {v_per7}")
print(f"  Clock 8: gcd(12, 8) = {gcd_h8} -> Vertical Period = {v_per8}")
print(f"  Clock 9: gcd(12, 9) = {gcd_h9} -> Vertical Period = {v_per9}")
print(f"Total Column Vertical Period: lcm({v_per7}, {v_per8}, {v_per9}) = {v_total}")
print(f"Total Grid Width: W = 42 columns.")
print("Proof: The vertical clock period across column strides equals exactly 42, establishing")
print("an exact self-dual harmonic relation with the grid width W = 42!\n")

# Theorem 3: The 12x12 Modular Triptych Theorem
print("--- THEOREM 3: THE 12x12 MODULAR TRIPTYCH THEOREM (3 x 144 = 432) ---")
n_pk9 = 144
n_pk10_core = 432
n_pk10_pad = 72
n_pk10_total = 504

print(f"PK9 Dimension:         12 x 12 = {12 * 12} characters")
print(f"PK10 Core Dimension:   3 x (12 x 12) = 3 x 144 = {3 * 144} characters (12 rows x 36 cols)")
print(f"PK10 Outer Padding:    6 columns x 12 rows = {6 * 12} characters")
print(f"PK10 Total Dimension:  12 rows x 42 cols = {12 * 42} characters")
print("Proof: PK10 core is an exact 3-panel architectural triptych of PK9 modular panels!\n")

# Theorem 4: Transposition Generating Reflection Laws
print("--- THEOREM 4: TRANSPOSITION REFLECTION GENERATING LAWS ---")
p2 = [7, 0, 5, 2, 4, 3, 6, 1]
print("PK9 p2:", p2)
p2_sums = [p2[2*k] + p2[2*k+1] for k in range(4)]
p2_diffs = [abs(p2[2*k] - p2[2*k+1]) for k in range(4)]
print(f"  Pairwise sums:        {p2_sums} (Identically 7!)")
print(f"  Pairwise differences: {p2_diffs} (Exact odd sequence {{7, 3, 1, 5}}!)")

p1 = [15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8]
print("\nPK9 p1 bilateral symmetry in Z_18 (x + y = 17):")
for x in range(9):
    comp = 17 - x
    pos1 = p1.index(x)
    pos2 = p1.index(comp)
    print(f"  Pair ({x:2d}, {comp:2d}): pos {pos1:2d} and pos {pos2:2d} -> pos_sum = {pos1+pos2:2d}")

# Theorem 5: The Dual-Cipher GPS Coordinate Theorem
print("\n--- THEOREM 5: DUAL-CIPHER GPS COORDINATE THEOREM ---")
print("Target CIA Langley Sculpture GPS Coordinates: 38 deg 57 min 6.5 sec N, 77 deg 8 min 44 sec W")
print("1. Latitude Degrees (38 N):   PK10 Sum_Kr(Col 1) - Sum_Kr(Col 5) = 166 - 128 = 38")
print("2. Latitude Minutes (57 N):   PK9  Sum_Kr(J V R M) = 16 + 22 + 1 + 18 = 57")
print("3. Latitude Seconds (6 N):    PK9  Sum_Kr,1(JVRMBAUON) = 126 = 6 mod 60")
print("4. Longitude Degrees (77 W):  PK10 Sum_Std(Row 0 Pad: LUJDPT) = 11+20+9+3+15+19 = 77")
print("5. Longitude Minutes (8 W):   PK10 Sum_Kr(Col 40) - Sum_Kr(Col 29) = 155 - 147 = 8")
print("6. Longitude Seconds (44 W):  PK10 Sum_Std(Col 40) - Sum_Std(Col 5) = 152 - 108 = 44")
print("7. Modular Null 1:            PK9  Sum_Kr(AUON) = 52 = 2 x 26 = 0 mod 26")
print("8. Modular Null 2:            PK10 Sum_Std(Col 0) = 156 = 6 x 26 = 0 mod 26")
print("\nThe five identities above hold arithmetically. None of them is evidence")
print("about the ciphers: the quantities and moduli were chosen after the fact.")
print("Checks that can fail live in verify_pk_records.py.")
