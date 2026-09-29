import re

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

pk8 = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY"
pk9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

# Compute D under both STD and KRYPTOS
diff_std = [(ord(pk9[i]) - ord(pk8[i])) % 26 for i in range(144)]
diff_k = [(KRYPTOS.index(pk9[i]) - KRYPTOS.index(pk8[i])) % 26 for i in range(144)]

# English quadgram table or word list
# Let's test dragging 50 common English words across P8:
words = [
    "THE", "AND", "THAT", "HAVE", "WITH", "THIS", "FROM", "THEY", "WILL", "WOULD",
    "THERE", "THEIR", "ABOUT", "WHICH", "COULD", "OTHER", "AFTER", "FIRST", "WATER",
    "HAMMER", "ANVIL", "NEEDLE", "COPPER", "SILVER", "BELLOWS", "CRUCIBLE", "TEMPER",
    "QUENCH", "HEATED", "FURNACE", "SECRET", "KRYPTOS", "EASTNORTHEAST", "BERLINCLOCK",
    "WHITESMITH", "SANBORN", "WEBSTER", "LANGLEY", "VIRGINIA", "CENTRAL", "INTELLIGENCE"
]

print("Scanning for depth matches where both P8 and I9 contain valid English letter profiles...")

for alph_name, diff, alpha in [("STD", diff_std, STD), ("KRYPTOS", diff_k, KRYPTOS)]:
    print(f"\n=== Alphabet: {alph_name} ===")
    hits = []
    for w in words:
        w_len = len(w)
        w_idx = [alpha.index(c) for c in w]
        for pos in range(144 - w_len + 1):
            # If P8[pos:pos+len] == w:
            # I9[pos:pos+len] = (w_idx + diff[pos:pos+len]) % 26
            i9_idx = [(w_idx[k] + diff[pos + k]) % 26 for k in range(w_len)]
            i9_str = "".join(alpha[x] for x in i9_idx)
            
            # Check if I9 contains only plausible letters (no rare letters Q, Z, X, J unless short)
            rare_count = sum(1 for c in i9_str if c in "QZXJ")
            if rare_count == 0:
                # Count common vowels / consonants
                vowel_count = sum(1 for c in i9_str if c in "ETAOINSHRDLU")
                if vowel_count >= w_len - 1:
                    hits.append((pos, w, i9_str))
                    
    print(f"Found {len(hits)} plausible word alignments.")
    for pos, w, i9_str in hits[:20]:
        print(f"  Pos {pos:3d}: P8 = {w:15s} --> I9 = {i9_str}")
