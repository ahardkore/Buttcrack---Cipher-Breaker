import math

with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

Z_STR = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN"
N = 144
W1 = 18
H1 = 8
W2 = 8
H2 = 18

def get_perm(word):
    return sorted(range(len(word)), key=lambda i: (word[i], i))

def invert_col(src, w, perm):
    h = len(src) // w
    res = [None] * len(src)
    idx = 0
    for col_idx in perm:
        for r in range(h):
            res[r * w + col_idx] = src[idx]
            idx += 1
    return "".join(res)

kryptos_18 = [
    "PALIMPSESTABSCISSA",
    "ABSCISSAPALIMPSEST",
    "KRYPTOSUNDERGROUND",
    "UNDERGROUNDKRYPTOS",
    "NORTHEASTSOUTHEAST",
    "SOUTHEASTNORTHEAST",
    "SCULPTURENORTHEAST",
    "NORTHEASTSCULPTURE",
    "THEWHITESMITHSWORK",
    "THEWHITESMITHSSHOP",
    "ACCESSIONLOGITEMEI",
    "INVESTIGATIONLOGIT",
    "ANINTERLOCKINGGRID"
]

kryptos_8 = [
    "ABSCISSA",
    "VIRGINIA",
    "MONUMENT",
    "SANBORNS",
    "TREASURY",
    "PROPERLY",
    "FURLONGS",
    "PRACTICE",
    "RESIDUEE",
    "WORKSHOP",
    "BELLOWSS",
    "ARCHIVES"
]

print("Testing iconic Kryptos keyword combinations on PK9 Z:")
for p18 in kryptos_18:
    order18 = get_perm(p18)
    for p8 in kryptos_8:
        order8 = get_perm(p8)
        
        # Mode 0: invert W2=8, then W1=18
        mid0 = invert_col(Z_STR, W2, order8)
        pt0 = invert_col(mid0, W1, order18)
        sc0 = score_quad(pt0)
        
        # Mode 1: invert W1=18, then W2=8
        mid1 = invert_col(Z_STR, W1, order18)
        pt1 = invert_col(mid1, W2, order8)
        sc1 = score_quad(pt1)
        
        if sc0 > -6.4 or sc1 > -6.4:
            print(f"Words: ({p18}, {p8}) -> Mode 0: {sc0:.4f} | Mode 1: {sc1:.4f}")
            if sc0 > sc1:
                print("  PT0:", pt0[:80])
            else:
                print("  PT1:", pt1[:80])
