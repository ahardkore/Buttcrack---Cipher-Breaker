# Linguistic Segmentation & Exegesis of PK8 Stationary Plaintext
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY"

q4 = [0, 6, 13, 20]
q5 = [3, 4, 15, 0, 10]
q6 = [3, 18, 15, 25, 20, 4]
q7 = [10, 2, 24, 0, 9, 5, 17]

pt = []
for i in range(len(PK8_CT)):
    shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26
    ct_idx = KRYPTOS.index(PK8_CT[i])
    p_idx = (ct_idx - shift + 26) % 26
    pt.append(KRYPTOS[p_idx])

pt_str = "".join(pt)

print("==========================================================================================")
print("             PK8 STATIONARY CANDIDATE (153 CHARS) LINGUISTIC SEGMENTATION                 ")
print("==========================================================================================\n")
print(f"Plaintext (N = 153):\n{pt_str}\n")

# Load words
words = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if w.isalpha(): words.add(w)

# Add craft and old English words:
for cw in ["ORTS", "THEE", "HEEL", "YON", "DAW", "MELODY", "LIT", "CLIT", "BONI", "HUSS", "VOG"]:
    words.add(cw)

# Word segmentation via Dynamic Programming:
def segment(text):
    n = len(text)
    dp = [-9999.0] * (n + 1)
    parent = [-1] * (n + 1)
    dp[0] = 0.0
    for i in range(n):
        if dp[i] <= -9000.0: continue
        for L in range(1, min(15, n - i + 1)):
            sub = text[i : i + L]
            if sub in words and len(sub) >= 2:
                score = (L ** 1.8) * 10.0
                if dp[i] + score > dp[i + L]:
                    dp[i + L] = dp[i] + score
                    parent[i + L] = i
            else:
                score = -20.0 * L
                if dp[i] + score > dp[i + L]:
                    dp[i + L] = dp[i] + score
                    parent[i + L] = i
    tokens = []
    curr = n
    while curr > 0:
        prev = parent[curr]
        tokens.append(text[prev:curr])
        curr = prev
    tokens.reverse()
    return tokens

tokens = segment(pt_str)
formatted = []
lex_chars = 0
for t in tokens:
    if t in words and len(t) >= 2:
        formatted.append(f"[{t}]")
        lex_chars += len(t)
    else:
        formatted.append(t)

print("Segmented Reading:")
print(" ".join(formatted))
print(f"\nLexical Word Coverage: {lex_chars} / 153 characters ({lex_chars/153*100:.1f}%)")

# Detailed Segment Analysis
print("\n--- Key Semantic Segments in PK8 ---")
segments = [
    ("Pos 0..20", pt_str[0:20], "NRHPXXOE ICE JAAN OSSOY (Ice ... opening)"),
    ("Pos 20..50", pt_str[20:50], "BUIFLBV VOG FUN OIT TH SET EH FAN (fun / set / fan / bellows blast)"),
    ("Pos 50..80", pt_str[50:80], "CPLBGLSN TEE VNVZB DEL Q BONI ATI QBS (tee / del / boni)"),
    ("Pos 80..115", pt_str[80:115], "FKTTT BAUG N THEE L HAS OC END FG THS Y ORTS (THEE HAS ... END ... ORTS / scrap filings)"),
    ("Pos 115..153", pt_str[115:153], "UOD SED AWPE YON HEA CLIT TD HUSSI KEY JM MELODY UD OPT N (yon / lit / KEY / MELODY / opt)")
]

for title, chunk, note in segments:
    print(f"  {title:12s}: {chunk:40s} -> {note}")
