# Automated N-Gram & Steganography Scan on PK10 129 Non-Lexical Characters
import math
from collections import Counter

with open("pk10_record_6943.txt") as f:
    lines = [l.strip() for l in f if l.startswith("# Row")]

rows = [l.split(":")[1].split("(")[0].strip() for l in lines]
core_rows = [r[2:38] for r in rows]

# Load words and craft terms
words = set()
with open("all_words.txt") as f:
    for line in f:
        w = line.strip().upper()
        if w.isalpha(): words.add(w)

craft_additions = [
    "KUUP", "GRUNGE", "PREDAMP", "BLEAR", "HANT", "LOCOU", "CHEVR", "WESHPL",
    "BAUL", "SURIVI", "YERK", "DYER", "ADAY", "FIR", "AMP", "DAMP", "SLY",
    "TON", "SLANT", "VIVA", "WAIT", "HUNK", "ACT", "CUM", "WRY", "SWE", "FAB",
    "BYE", "YEA", "APPS", "PLOW", "FLY", "CIG", "MOTH", "RAFT", "TRY", "BAG",
    "YARR", "IAN", "DAD", "BUB", "PROW", "NOOK", "RAP", "DAG", "ADD", "SAD",
    "MAT", "VAS", "GET", "PROP", "TEA", "TIM", "MAE", "ORT", "GOD", "GOES", "RED",
    "DYE", "OCH", "BIG", "LED", "DAYS", "VERI", "ELD", "WER", "HAVE", "AVE"
]
for cw in craft_additions: words.add(cw)

# Re-run dynamic programming segmentation to extract exactly the non-lexical characters
def extract_non_lex(row):
    n = len(row)
    dp = [-9999.0] * (n + 1)
    parent = [-1] * (n + 1)
    dp[0] = 0.0
    for i in range(n):
        if dp[i] <= -9000.0: continue
        for L in range(1, min(15, n - i + 1)):
            sub = row[i : i + L]
            if sub in words and len(sub) >= 2:
                score = (L ** 1.8) * 10.0
                if dp[i] + score > dp[i + L]:
                    dp[i + L] = dp[i] + score
                    parent[i + L] = i
            else:
                score = -25.0 * L
                if dp[i] + score > dp[i + L]:
                    dp[i + L] = dp[i] + score
                    parent[i + L] = i
    tokens = []
    curr = n
    while curr > 0:
        prev = parent[curr]
        tokens.append(row[prev:curr])
        curr = prev
    tokens.reverse()
    
    non_lex = []
    for t in tokens:
        if not (t in words and len(t) >= 2):
            non_lex.append(t)
    return "".join(non_lex)

all_non_lex = ""
row_non_lex = []
for r in core_rows:
    nl = extract_non_lex(r)
    row_non_lex.append(nl)
    all_non_lex += nl

print("==========================================================================================")
print("             PK10 NON-LEXICAL RESIDUE STEGANOGRAPHIC SCAN (N = 129)                       ")
print("==========================================================================================\n")
print(f"Total non-lexical characters extracted: {len(all_non_lex)}")
print(f"Non-lexical stream:\n{all_non_lex}\n")

print("Row-by-Row Non-Lexical Residues:")
for r_idx, nl in enumerate(row_non_lex):
    print(f"  Row {r_idx:2d} ({len(nl):2d} chars): {nl}")

# Statistical Invariants of the Non-Lexical Residue
c = Counter(all_non_lex)
n = len(all_non_lex)
ioc = sum(v * (v - 1) for v in c.values()) / (n * (n - 1)) if n > 1 else 0
ent = -sum((v / n) * math.log2(v / n) for v in c.values() if v > 0)
eff = ent / math.log2(26) * 100

print(f"\n--- Statistical Invariants of Residue (N = {n}) ---")
print(f"Monogram IoC:        {ioc:.5f} (Random: 0.03846, English: 0.06670)")
print(f"Shannon Entropy:     {ent:.4f} bits (Efficiency: {eff:.1f}%)")
print(f"Distinct Characters: {len(c)} / 26")

# Rare letters count in non-lexical residue:
rare = sum(c[ch] for ch in "JQXZ")
print(f"Rare Letters (J,Q,X,Z): {rare} / {n} ({rare/n*100:.2f}%)")

# Letter Frequency Distribution
print("\nMost Frequent Letters in Residue:")
for ch, cnt in c.most_common(10):
    print(f"  {ch}: {cnt:2d} ({cnt/n*100:.1f}%)")

# Parity Distribution
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
even_kr = sum(c[ch] for ch in c if KRYPTOS.index(ch) % 2 == 0)
odd_kr  = sum(c[ch] for ch in c if KRYPTOS.index(ch) % 2 == 1)
print(f"\nParity in Kryptos Alphabet: Even = {even_kr} ({even_kr/n*100:.1f}%), Odd = {odd_kr} ({odd_kr/n*100:.1f}%)")

# Repeated Digrams in Residue
digrams = Counter([all_non_lex[i:i+2] for i in range(len(all_non_lex)-1)])
print("\nRepeated Digrams in Residue:")
for d, cnt in digrams.most_common(8):
    if cnt > 1:
        print(f"  Digram \"{d}\": {cnt} occurrences")
