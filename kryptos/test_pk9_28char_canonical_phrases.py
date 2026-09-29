import math

with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
k2std = [ord(c) - ord('A') for c in KRYPTOS]
hpos = {c: i for i, c in enumerate(KRYPTOS)}
PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
ct_kr = [hpos[c] for c in PK9_RAW]

p1 = [5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6]
p2 = [4, 0, 6, 5, 3, 2, 7, 1]
W1, H1 = 18, 8
W2, H2 = 8, 18

pt_to_mid = [None] * 144
idx = 0
for c_idx in range(W1):
    col = p1[c_idx]
    for r in range(H1):
        pt_to_mid[r * W1 + col] = idx
        idx += 1

mid_to_z = [None] * 144
idx = 0
for c_idx in range(W2):
    col = p2[c_idx]
    for r in range(H2):
        mid_to_z[r * W2 + col] = idx
        idx += 1

pt_to_z = [mid_to_z[pt_to_mid[i]] for i in range(144)]

phrases28 = [
    "THEINVESTIGATIONLOGITEMEIGHT",
    "INVESTIGATIONLOGITEMEIGHTKNO",
    "TIGHTLYWOUNDITSTHREADINSCRIB",
    "THEACCESSIONLOGSAYSONCEUNRAV",
    "ELELEDITREVEALSTHEROUTETOTHE",
    "LOSTARCHIVEOFPELLEGRINTWELVE",
    "IHAVEFOUNDREFERENCESTOTHEKNOT",
    "INSEVENOTHERRECORDSINOURARCHI",
    "UNAGOTANTOSOTTILEDALEGGEREQU",
    "ALUNQUENODOIBELIEVEDTHISTOBE",
    "JUSTATURNOFPHRASEBUTTHEOTHER",
    "SEVENTHMONTHIWROTETOFIFTEENC",
    "THESTRINGSMEASURETWOFURLONGS",
    "WEEXAMINEDTHEFIBERSUNDERTHEL",
    "THEWHITESMITHSWORKSHOPISFILL",
    "EDWITHTHEOLDTOOLSOFHISTRADEM",
    "HEPOINTEDTOTHEHEARTHANDSAIDT",
    "HATTHEWORKCOULDONLYBEGINWHEN",
    "ATLASTTHEWORKWASGOINGTOPROVE",
    "ANEEDLEFROMTHERESIDUEOFHISPR"
]

print("Testing 28-character Canonical Phrases as PK9 Keystream:")
for p in phrases28:
    shifts = [hpos[c] for c in p]
    pt = []
    for i in range(144):
        z_idx = pt_to_z[i]
        s = shifts[z_idx % 28]
        p_kr = (ct_kr[z_idx] - s + 26) % 26
        pt.append(chr(65 + k2std[p_kr]))
    pt_str = "".join(pt)
    sc = score_quad(pt_str)
    print(f"Phrase: {p} -> Score: {sc:.4f}")
    if sc > -7.5:
        print("  PT:", pt_str[:80])
