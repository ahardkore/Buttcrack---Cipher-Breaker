import sys
sys.path.insert(0, 'buttcrack/src')
import json
from collections import Counter

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

pk10 = cts['PK10']
N = len(pk10)
print(f"PK10 length: {N}")

def slice_ioc(s, p):
    slices = [s[i::p] for i in range(p)]
    iocs = []
    for sl in slices:
        m = len(sl)
        if m <= 1: continue
        c = Counter(sl)
        iocs.append(sum(v * (v - 1) for v in c.values()) / (m * (m - 1)))
    return sum(iocs) / len(iocs) if iocs else 0.0

def eval_reveals(s):
    i7 = slice_ioc(s, 7)
    i8 = slice_ioc(s, 8)
    i9 = slice_ioc(s, 9)
    return i7, i8, i9, (i7 + i8 + i9) / 3.0

raw_i7, raw_i8, raw_i9, raw_avg = eval_reveals(pk10)
print(f"Raw PK10: IoC(7)={raw_i7:.4f}, IoC(8)={raw_i8:.4f}, IoC(9)={raw_i9:.4f} | Avg={raw_avg:.4f}")

# Test 1: Simple Matrix Transpositions (reading by cols instead of rows)
print("\n--- Testing Simple Grid Transpositions (M^T) ---")
divisors = [7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42, 56, 63, 72]
for W in divisors:
    H = N // W
    # Write by rows of width W, read by cols
    grid = [pk10[r*W:(r+1)*W] for r in range(H)]
    col_read = ''.join(grid[r][c] for c in range(W) for r in range(H))
    i7, i8, i9, avg = eval_reveals(col_read)
    if avg > 0.045 or i7 > 0.05 or i8 > 0.05 or i9 > 0.05:
        print(f"Width {W:2d} (H={H:2d}) Col-Read: IoC(7)={i7:.4f}, IoC(8)={i8:.4f}, IoC(9)={i9:.4f} | Avg={avg:.4f} (*** SPIKE ***)")
    else:
        print(f"Width {W:2d} (H={H:2d}) Col-Read: Avg={avg:.4f}")

# Test 2: Serpentine / Boustrophedon reads
print("\n--- Testing Serpentine / Alternating Reads ---")
for W in divisors:
    H = N // W
    # Boustrophedon rows
    b_rows = []
    for r in range(H):
        row = pk10[r*W:(r+1)*W]
        b_rows.append(row if r % 2 == 0 else row[::-1])
    s_b = ''.join(b_rows)
    i7, i8, i9, avg = eval_reveals(s_b)
    if avg > 0.045:
        print(f"Width {W:2d} Boustrophedon: Avg={avg:.4f} (*** SPIKE ***)")
