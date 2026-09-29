KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
shifts = [5, 4, 9, 15, 16, 5, 6, 10, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

print("Possible 28-character key phrases under all 26 indicators on KRYPTOS:")
for ind in range(26):
    k_phrase = "".join(KRYPTOS[(s + ind) % 26] for s in shifts)
    # Check if k_phrase has common bigrams/trigrams
    print(f"Ind {ind:2d} ({KRYPTOS[ind]}): {k_phrase}")
