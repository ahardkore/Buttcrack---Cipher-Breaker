import json
import time

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct10 = cts["PK10"]
N = len(ct10)

def slice_ioc(text, p):
    total = 0.0
    for r in range(p):
        sl = text[r::p]
        L = len(sl)
        if L < 2:
            continue
        counts = {}
        for c in sl:
            counts[c] = counts.get(c, 0) + 1
        total += sum(n * (n - 1) for n in counts.values()) / (L * (L - 1))
    return total / p

# Load common keywords from words_6, words_7, words_8, words_9, words_12, words_14
keywords_by_len = {}
for wlen in [6, 7, 8, 9, 12, 14]:
    fname = f"words_{wlen}.txt"
    keywords_by_len[wlen] = []
    try:
        with open(fname) as f:
            for line in f:
                w = line.strip().upper()
                if len(w) == wlen and w.isalpha():
                    keywords_by_len[wlen].append(w)
                if len(keywords_by_len[wlen]) >= 3000:
                    break
    except FileNotFoundError:
        pass
    print(f"Loaded {len(keywords_by_len[wlen])} words of length {wlen}.")

# Test block units: unit=2, 3, 4, 6, 7, 8, 9
configurations = [
    # (unit, width, num_blocks, height)
    (2, 7, 252, 36),
    (2, 9, 252, 28),
    (3, 7, 168, 24),
    (3, 8, 168, 21),
    (3, 6, 168, 28),
    (4, 7, 126, 18),
    (4, 9, 126, 14),
    (6, 7, 84, 12),
    (7, 8, 72, 9),
    (8, 7, 63, 9),
    (9, 7, 56, 8),
    (9, 8, 56, 7),
]

print("Scanning block-columnar configurations on PK10...")
best_ioc_overall = 0.0
best_config = None

t0 = time.time()
for unit, w, num_blocks, h in configurations:
    kws = keywords_by_len.get(w, [])[:2000]
    best_ioc_conf = 0.0
    best_kw = ""

    for kw in kws:
        # Determine column order
        order = sorted(range(w), key=lambda i: (kw[i], i))
        # Columnar read of blocks
        # Grid of blocks: h rows, w cols
        # In ciphertext: columns read out according to order
        # To invert: write columns by order, read by rows
        blocks = [None] * num_blocks
        idx = 0
        for col_idx in order:
            for r in range(h):
                b = ct10[idx * unit : (idx + 1) * unit]
                blocks[r * w + col_idx] = b
                idx += 1
        
        reconstructed = "".join(blocks)
        
        # Check IoC at p=7, 8, 9
        ioc7 = slice_ioc(reconstructed, 7)
        ioc8 = slice_ioc(reconstructed, 8)
        ioc9 = slice_ioc(reconstructed, 9)
        max_ioc = max(ioc7, ioc8, ioc9)

        if max_ioc > best_ioc_conf:
            best_ioc_conf = max_ioc
            best_kw = kw

    print(f"Unit {unit}, Width {w} (tested {len(kws)} keys): Best max-IoC = {best_ioc_conf:.5f} (kw: {best_kw})")
    if best_ioc_conf > best_ioc_overall:
        best_ioc_overall = best_ioc_conf
        best_config = (unit, w, best_kw)

print(f"\nCompleted in {time.time()-t0:.2f}s. Best overall: {best_ioc_overall:.5f} with {best_config}")
