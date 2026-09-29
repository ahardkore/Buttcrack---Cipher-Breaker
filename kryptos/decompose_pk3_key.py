from buttcrack.additive_words import recover_word_keys

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
pk3_key = "BFPNBZITCSGKFENPJQHQVMWIQNUBWFAVXOZATKBJ"
pad = [ALPH.index(c) for c in pk3_key]

with open("words_alpha.txt") as f:
    words = [line.strip().upper() for line in f if line.strip().isalpha()]

print("Searching word keys for PK3 on KRYPTOS alphabet...")
res = recover_word_keys(pad, [10, 8], words, alphabet=ALPH, max_nodes=50000000, max_results=20)
print("Results (KRYPTOS):", res)

if not res['tuples']:
    print("Searching on STANDARD alphabet...")
    ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pad_std = [ALPH_STD.index(c) for c in pk3_key]
    res_std = recover_word_keys(pad_std, [10, 8], words, alphabet=ALPH_STD, max_nodes=50000000, max_results=20)
    print("Results (STANDARD):", res_std)

