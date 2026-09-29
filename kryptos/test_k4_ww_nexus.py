import json

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Let's inspect the exact letters of K4 on the physical copper scroll
# The copper scroll has 28 characters per row or 30 characters per row.
# In the sculpture, K4 starts at line 24.
# Let's print K4 with the known cribs aligned:

print("K4 Ciphertext and Known Cribs Alignment:")
pt_display = ["."] * 97
for i, c in enumerate("EASTNORTHEAST"):
    pt_display[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    pt_display[63 + i] = c

print("CT: " + K4_CT)
print("PT: " + "".join(pt_display))

# Check the W positions:
for i in [20, 36, 48, 58, 74]:
    print(f"Index {i:2d} (1-based {i+1:2d}): CT='{K4_CT[i]}', preceding='{K4_CT[i-1]}', following='{K4_CT[i+1]}'")

# Check shifts at cribs:
shifts_k = []
for i in range(97):
    if pt_display[i] != '.':
        s = (ALPH_K.index(K4_CT[i]) - ALPH_K.index(pt_display[i])) % 26
        shifts_k.append((i, pt_display[i], K4_CT[i], s, ALPH_K[s]))
    else:
        shifts_k.append((i, '.', K4_CT[i], None, '.'))

print("\nCrib 1 (EASTNORTHEAST, 21..33):")
for i in range(21, 34):
    print(f"  pos {i:2d}: PT={shifts_k[i][1]} CT={shifts_k[i][2]} shift={shifts_k[i][3]:2d} key_char={shifts_k[i][4]}")

print("\nCrib 2 (BERLINCLOCK, 63..73):")
for i in range(63, 74):
    print(f"  pos {i:2d}: PT={shifts_k[i][1]} CT={shifts_k[i][2]} shift={shifts_k[i][3]:2d} key_char={shifts_k[i][4]}")

# Notice the shift sequence:
# Crib 1 shifts: [1, 10, 21, 18, 1, 15, 2, 23, 5, 2, 19, 0, 2]
# Crib 2 shifts: [11, 17, 2, 5, 15, 11, 9, 8, 7, 20, 0]

# Check if there is an autokey relation:
# If key is plaintext: K[i] = PT[i - lag]
# If key is ciphertext: K[i] = CT[i - lag]
print("\nChecking Autokey relation:")
for lag in range(1, 30):
    # check CT autokey on Crib 1:
    ct_matches = 0
    for i in range(21, 34):
        k_val = shifts_k[i][3]
        if i - lag >= 0:
            ct_prev = ALPH_K.index(K4_CT[i - lag])
            if k_val == ct_prev:
                ct_matches += 1
    if ct_matches >= 3:
        print(f"  CT Autokey lag {lag}: {ct_matches}/13 matches on Crib 1")

