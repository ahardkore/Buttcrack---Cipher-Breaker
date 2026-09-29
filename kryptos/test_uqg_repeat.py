ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
std_to_kr = {c: i for i, c in enumerate(ALPH)}
kr_to_std = {i: c for i, c in enumerate(ALPH)}

c_uqg_std = [ord(c) - ord('A') for c in "UQG"]
c_uqg_kr = [std_to_kr[c] for c in "UQG"]

print("Ciphertext trigram: UQG")
print("Standard indices:", c_uqg_std)
print("Kryptos indices:", c_uqg_kr)

common_trigrams = [
    "THE", "AND", "ING", "ION", "ENT", "FOR", "TIO", "TER", "HAT", "THA",
    "ERE", "ATE", "ALL", "WIT", "NOT", "WAS", "HIS", "HER", "OUT", "ONE",
    "ARE", "INT", "EST", "STA", "ITH", "TTH", "ETH", "VER", "MEN", "EVE",
    "RES", "MAN", "RED", "IRE", "OLD", "EEN", "CON", "PRO", "STR", "MET"
]

print("\n--- Kryptos Mode (C = (P + K) % 26) ---")
for tri in common_trigrams:
    p_kr = [std_to_kr[c] for c in tri]
    k_kr = [(c_uqg_kr[i] - p_kr[i]) % 26 for i in range(3)]
    k_letters = "".join(ALPH[k] for k in k_kr)
    print(f"Plain: {tri} -> Key shifts: {k_kr} (letters: {k_letters})")

print("\n--- Kryptos Beaufort (C = (K - P) % 26) ---")
for tri in common_trigrams:
    p_kr = [std_to_kr[c] for c in tri]
    k_kr = [(c_uqg_kr[i] + p_kr[i]) % 26 for i in range(3)]
    k_letters = "".join(ALPH[k] for k in k_kr)
    print(f"Plain: {tri} -> Key shifts: {k_kr} (letters: {k_letters})")
