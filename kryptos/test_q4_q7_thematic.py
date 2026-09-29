import pandas as pd

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
std_to_kr = {c: i for i, c in enumerate(ALPH)}

def to_shifts(word, alphabet="std"):
    if alphabet == "std":
        return [ord(c) - ord('A') for c in word]
    else:
        return [std_to_kr[c] for c in word]

df = pd.read_csv("top_clocks.csv")

# Test 4-letter candidates
words_4 = ["EAST", "SLOW", "KNOT", "BERN", "GOLD", "IRON", "FIRE", "WIRE", "TOOL", "ANVL", "BEAT", "HEAT", "WORK", "FINE"]
# Test 7-letter candidates
words_7 = ["KRYPTOS", "SANBORN", "LANGLEY", "NEEDLES", "CARTERS", "BELLOWS", "TEMPERD", "DRAWING", "PUNCHES", "ANVILSS", "FURNACE", "HEATING"]

print("Checking if any thematic (Q4, Q7) appear in top_clocks.csv...")

for w4 in words_4:
    for w7 in words_7:
        # Check standard and kryptos representations
        s4_std = to_shifts(w4, "std")
        s7_std = to_shifts(w7, "std")
        
        # Normalized by gauge shift (s4[0] = 0)
        gauge_s4_std = [(x - s4_std[0]) % 26 for x in s4_std]
        gauge_s7_std = [(x + s4_std[0]) % 26 for x in s7_std]
        
        s4_str = "".join(chr(ord('A') + x) for x in gauge_s4_std)
        s7_str = "".join(chr(ord('A') + x) for x in gauge_s7_std)
        
        match = df[(df['str_q4_std'] == s4_str) & (df['str_q7_std'] == s7_str)]
        if len(match) > 0:
            print(f"MATCH FOUND! {w4} + {w7} in Standard: {match[['mode', 'll']]}")

        # Kryptos alphabet
        s4_kr = to_shifts(w4, "kr")
        s7_kr = to_shifts(w7, "kr")
        gauge_s4_kr = [(x - s4_kr[0]) % 26 for x in s4_kr]
        gauge_s7_kr = [(x + s4_kr[0]) % 26 for x in s7_kr]
        s4_kr_str = "".join(ALPH[x] for x in gauge_s4_kr)
        s7_kr_str = "".join(ALPH[x] for x in gauge_s7_kr)
        
        match_kr = df[(df['str_q4_kr'] == s4_kr_str) & (df['str_q7_kr'] == s7_kr_str)]
        if len(match_kr) > 0:
            print(f"MATCH FOUND! {w4} + {w7} in Kryptos: {match_kr[['mode', 'll']]}")

print("Search completed.")
