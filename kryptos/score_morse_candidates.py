import sys
from buttcrack.lang import get_model

model = get_model("english")
K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
ALPH_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

CRIBS = {}
for i, c in enumerate("EASTNORTHEAST"):
    CRIBS[21 + i] = c
for i, c in enumerate("BERLINCLOCK"):
    CRIBS[63 + i] = c

MORSE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..'
}

MORSE_STRINGS = [
    "VIRTUALLYINVISIBLE",
    "DIGETALINTERPRETATUON",
    "DIGITALINTERPRETATION",
    "SHADOWFORCES",
    "LUCIDMEMORY",
    "TISYOURPOSITION",
    "THISISYOURPOSITION",
    "YOURPOSITION",
    "SOS",
    "RQ",
    "EASTNORTHEAST",
    "BERLINCLOCK",
    "KRYPTOS",
    "PALIMPSEST",
    "ABSCISSA"
]

scored_results = []

for m_str in MORSE_STRINGS:
    raw_morse = "".join(MORSE_DICT[c] for c in m_str)
    for dot_val, dash_val in [(0, 1), (1, 0), (0, -1), (1, -1)]:
        bits = [dot_val if ch == '.' else dash_val for ch in raw_morse]
        B = len(bits)
        
        for p in range(1, 27):
            for off in range(B):
                for alph_name, alph in [("Standard", ALPH_STD), ("KRYPTOS", ALPH_K)]:
                    base_k = {}
                    valid = True
                    for pos, pt_char in CRIBS.items():
                        c_idx = alph.index(K4_CT[pos])
                        p_idx = alph.index(pt_char)
                        req_s = (c_idx - p_idx) % 26
                        gate = bits[(pos + off) % B]
                        req_base = (req_s - gate) % 26
                        
                        r = pos % p
                        if r in base_k:
                            if base_k[r] != req_base:
                                valid = False
                                break
                        else:
                            base_k[r] = req_base
                    if valid:
                        # Reconstruct text at all positions where r in base_k
                        pt = []
                        test_letters = []
                        for i in range(len(K4_CT)):
                            r = i % p
                            if r in base_k:
                                s = (base_k[r] + bits[(i + off) % B]) % 26
                                c_idx = alph.index(K4_CT[i])
                                p_idx = (c_idx - s) % 26
                                ch = alph[p_idx]
                                pt.append(ch)
                                if i not in CRIBS:
                                    test_letters.append(ch)
                            else:
                                pt.append("?")
                        if len(test_letters) >= 20:
                            fitness = model.fitness("".join(test_letters))
                            scored_results.append((fitness, m_str, p, off, alph_name, "".join(pt)))

scored_results.sort(key=lambda x: x[0], reverse=True)
print(f"Total scored Morse candidates: {len(scored_results)}")
print("Top 5 candidates by English fitness (crib-free):")
for sc, m_str, p, off, aname, pt in scored_results[:5]:
    print(f"  Score: {sc:.3f} | Phrase: {m_str} (p={p}, off={off}, {aname})")
    print(f"    Plaintext: {pt}")

