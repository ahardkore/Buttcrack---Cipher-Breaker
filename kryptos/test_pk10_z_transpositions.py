import math, time

with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

Z_PK10 = "ASGKUHCPALCOWACYCCUWPMIMRUCDEOXWQBCFBATGCSKDUASKFATGMDADYLDBSOZTFRCPNLMSHNBUZUHDDDHKNENSDMIRVTYAGDBPIUKNQSTIAHBNJTHZKPTHIXEOLUSISSTDTISLRMLUYJEKXSEJUOKUKMIMCCELHHSOLNLUWIOOADAYTHKSEVACCHASRVFTSYTYEHEPDULEEOWMNNUWUWNUSZUDENLWYZAXSVNECGOENTFOTTHOREENUETOLDYGIOIULIVPRANKTXNTOIIUBWEOFAPSOSFLOMATARDTVLSEPTMHPOFPVLIRFUECBNARRBIHHGEVUYUSSEONFVFIBOPFGGHQQOLRSEBELAURUNWAKREMEEYDUQQHPFYXYGUSQWUALNHDENFAPUIUBAYLSLVGPHYISBTPORESBCLIRFNGFGIYEJOHWSWODTTIDPFSNOQTTRYDPMXTSACDOPMNRRNGGDSHFYOWEOFKDYTVUYYKSECUIMSNETBE"
N = len(Z_PK10)

print(f"PK10 Z Length: {N} | Untransposed Quad Score: {score_quad(Z_PK10):.4f}")

widths = [7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42]

# Test standard read-in/read-out routes (by row read by col, by col read by row)
for w in widths:
    h = N // w
    # Route 1: Write by rows, read by cols
    r1 = "".join(Z_PK10[c + r * w] for c in range(w) for r in range(h))
    sc1 = score_quad(r1)
    
    # Route 2: Write by cols, read by rows
    r2 = "".join(Z_PK10[r + c * h] for r in range(h) for c in range(w))
    sc2 = score_quad(r2)

    # Route 3: Boustrophedon rows, read by cols
    r3_chars = []
    for c in range(w):
        for r in range(h):
            idx = r * w + (c if r % 2 == 0 else (w - 1 - c))
            r3_chars.append(Z_PK10[idx])
    sc3 = score_quad("".join(r3_chars))

    print(f"Grid {h:2d} x {w:2d}: Row->Col = {sc1:.4f} | Col->Row = {sc2:.4f} | Boustrophedon = {sc3:.4f}")
