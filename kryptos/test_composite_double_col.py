KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"

shifts = [5, 4, 9, 15, 16, 5, 6, 10, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

z_28 = []
for i in range(144):
    c_idx = KRYPTOS.index(PK9_REAL[i])
    p_kr = (c_idx - shifts[i % 28] + 26) % 26
    z_28.append(KRYPTOS[p_kr])
z_28 = "".join(z_28)

def argsort_stable(w):
    return sorted(range(len(w)), key=lambda i: (w[i], i))

w1 = "BLACKBIRDING"
w2 = "HEMATHERMOUS"

o1 = argsort_stable(w1)
o2 = argsort_stable(w2)

N = 144
W = 12
H = 12

def get_col_map(w, o):
    h = N // w
    # map[r * w + o[c]] = c * h + r
    # This inverts the columnar readout:
    # During encryption: matrix[r][c] is filled row-wise: matrix[r][c] = pt[r*w + c].
    # Then columns are read in order o: ct[c*h + r] = matrix[r][o[c]] = pt[r*w + o[c]].
    # So pt[r*w + o[c]] = ct[c*h + r].
    mapping = [0] * N
    for c in range(w):
        col = o[c]
        for r in range(h):
            mapping[r * w + col] = c * h + r
    return mapping

map1 = get_col_map(W, o1)
map2 = get_col_map(W, o2)

import math
quad = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            quad[parts[0]] = float(parts[1])
            total += float(parts[1])
for k in quad:
    quad[k] = math.log10(quad[k] / total)

def score(t):
    return sum(quad.get(t[i:i+4], -9.5) for i in range(len(t)-3)) / (len(t)-3)

# Test order 1: T1 then T2: pt = z_28[map1[map2[k]]]
pt1 = "".join(z_28[map1[map2[k]]] for k in range(N))
# Test order 2: T2 then T1: pt = z_28[map2[map1[k]]]
pt2 = "".join(z_28[map2[map1[k]]] for k in range(N))

print(f"Order (T1 then T2) Quad: {score(pt1):.4f}")
print("PT1:")
for r in range(12):
    print(f"Row {r:2d}: {pt1[r*12:(r+1)*12]}")

print(f"\nOrder (T2 then T1) Quad: {score(pt2):.4f}")
print("PT2:")
for r in range(12):
    print(f"Row {r:2d}: {pt2[r*12:(r+1)*12]}")
