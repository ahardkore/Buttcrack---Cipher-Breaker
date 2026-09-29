import json

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

morse_phrases = [
    "VIRTUALLYINVISIBLE",
    "SHADOWFORCES",
    "LUCIDMEMORY",
    "DIGETALINTERPRETATUON",
    "DIGITALINTERPRETATION",
    "THISISYOURPOSITION",
    "TISYOURPOSITION",
    "YOURPOSITION",
    "SOS",
    "RQ",
    "ABSCISSA",
    "PALIMPSEST",
    "KRYPTOS",
    "WILLIAMWEBSTER",
    "WALTERWOMACKA",
    "ONLYWW",
    "EASTNORTHEAST",
    "BERLINCLOCK",
    "URANIAWELTZEITUHR",
    "ALEXANDERPLATZ",
    "SANBORN",
    "SCHEIDT",
    "LANGLEY",
    "VIRGINIA",
    "COMPASSROSE",
    "LODESTONE",
    "PETRIFIEDWOOD",
    "COPPERPLATE"
]

crib1_pos = 21
crib1_text = "EASTNORTHEAST"

crib2_pos = 63
crib2_text = "BERLINCLOCK"

for phrase in morse_phrases:
    L = len(phrase)
    # Check if phrase matches key at crib 1
    # Key at pos i is: K[i] = (CT[i] - PT[i]) mod 26
    # Let's test repeating phrase with all offsets
    for off in range(L):
        # test crib 1:
        match1 = True
        for j, p in enumerate(crib1_text):
            k_char = phrase[(crib1_pos + j - off) % L]
            exp_c = ALPH_K[(ALPH_K.index(p) + ALPH_K.index(k_char)) % 26]
            if exp_c != K4_CT[crib1_pos + j]:
                match1 = False
                break
        if match1:
            print(f"MATCH on Crib 1: phrase={phrase}, offset={off} (KRYPTOS)")
            
        # test standard:
        match1_std = True
        for j, p in enumerate(crib1_text):
            k_char = phrase[(crib1_pos + j - off) % L]
            exp_c = ALPH_STD[(ALPH_STD.index(p) + ALPH_STD.index(k_char)) % 26]
            if exp_c != K4_CT[crib1_pos + j]:
                match1_std = False
                break
        if match1_std:
            print(f"MATCH on Crib 1: phrase={phrase}, offset={off} (STANDARD)")

print("Evaluation of Morse phrases as repeating keys complete.")
