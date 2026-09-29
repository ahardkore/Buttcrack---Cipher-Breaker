import math, time
from collections import Counter

# Load quadgrams
with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

# Load Z
Z_STR = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN"
N = len(Z_STR)
W = 12
H = 12

# Load theophilus 12-letter words
with open("theophilus_w12.txt") as f:
    words12 = [line.strip().upper() for line in f if len(line.strip()) == 12 and line.strip().isalpha()]

print(f"Loaded {len(words12)} 12-letter Theophilus words.")

def get_order(kw):
    return sorted(range(len(kw)), key=lambda i: (kw[i], i))

def invert_columnar(src, w, perm):
    h = len(src) // w
    # Write into cols by perm, read by rows
    res = [None] * len(src)
    idx = 0
    for col_idx in perm:
        for r in range(h):
            res[r * w + col_idx] = src[idx]
            idx += 1
    return "".join(res)

print("Sweeping all Theophilus 12x12 pairs...")
best_sc = -999.0
best_pair = None
best_pt = ""

t0 = time.time()
tested = 0
for w2 in words12:
    p2 = get_order(w2)
    mid = invert_columnar(Z_STR, W, p2)
    for w1 in words12:
        p1 = get_order(w1)
        pt = invert_columnar(mid, W, p1)
        sc = score_quad(pt)
        tested += 1
        if sc > best_sc:
            best_sc = sc
            best_pair = (w1, w2)
            best_pt = pt

elapsed = time.time() - t0
print(f"Evaluated {tested} pairs in {elapsed:.2f}s ({tested/elapsed:.0f} pairs/sec).")
print(f"Best Score: {best_sc:.4f} | Keywords: {best_pair}")
print(f"Plaintext:\n{best_pt}")
