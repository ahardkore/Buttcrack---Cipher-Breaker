import numpy as np

# Load quads
quad = {}
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            quad[parts[0]] = float(parts[1])
total = sum(quad.values())
log_quad = {k: np.log10((v + 0.01) / total) for k, v in quad.items()}

def score_text(t):
    return sum(log_quad.get(t[i:i+4], -9.5) for i in range(len(t)-3)) / (len(t)-3)

craft_words = [
    "SILVERSMITHS", "NEEDLEMAKING", "NEEDLEWORKER", "METALWORKERS", "COPPERPLATES",
    "BLACKSMITHLY", "GOLDSMITHERY", "CONSTRUCTION", "PURIFICATION", "TRANSMUTABLE",
    "MANUFACTURES", "DRAWPLATINGS", "ORGANARIUMSS", "TEMPERAMENTO", "CHALICEMOULD",
    "CRUCIBLEMELT", "FURNACEFLAME", "BELLOWSSANGS", "ANVILSTRIKES", "TEMPEREDIRON",
    "PELLEGRINIAN", "INVESTIGATOR", "ARCHIVISTING", "SANBORNCRYPT", "KRYPTOSMAKET",
    "BERLINCLOCKS", "NORTHEASTERN", "DISCOVERYLOG", "PENTIMENTOSI", "PROVENANCESI",
    "ORDINATELOCK", "ANATOMISTBER"
]
craft_words = [w for w in craft_words if len(w) == 12]

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
shifts28 = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 7, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

z_28 = []
for i in range(144):
    c_idx = KRYPTOS.index(PK9_REAL[i])
    p_kr = (c_idx - shifts28[i % 28] + 26) % 26
    z_28.append(KRYPTOS[p_kr])
z_str = "".join(z_28)

def word_to_order(word):
    return [i for i, _ in sorted(enumerate(word), key=lambda x: x[1])]

w = 12
h = 144 // w

def get_col_map(order):
    m = [0] * 144
    for c in range(w):
        col = order[c]
        for r in range(h):
            m[r * w + col] = c * h + r
    return m

best_sc = -999.0
best_pair = None
best_pt = ""

for w1 in craft_words:
    m1 = get_col_map(word_to_order(w1))
    pt1 = "".join(z_str[m1[k]] for k in range(144))
    sc1 = score_text(pt1)
    if sc1 > best_sc:
        best_sc = sc1
        best_pair = (w1, "NONE")
        best_pt = pt1
        
    for w2 in craft_words:
        m2 = get_col_map(word_to_order(w2))
        pt2 = "".join(z_str[m1[m2[k]]] for k in range(144))
        sc2 = score_text(pt2)
        if sc2 > best_sc:
            best_sc = sc2
            best_pair = (w1, w2)
            best_pt = pt2

print(f"Best Pair: {best_pair} | Quad: {best_sc:.3f}")
print("PT:", best_pt)
