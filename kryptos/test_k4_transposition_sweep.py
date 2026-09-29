import json
from collections import Counter
from buttcrack.engine import resolve_scorer

scorer = resolve_scorer('quadgrams', 'english')

# Decrypted text under Period 29 with ONLYWW:
dec_text = "KSARNQAPBZDBKZELWMIDUEASTNORTHEASTQGUZOUAFZFEBOSZOPSOZQUGDMGKFSBERLINCLOCKONLYWWQULCKEPJFYANKCAYF"
assert len(dec_text) == 97

print(f"Decrypted text (len {len(dec_text)}): {dec_text}")
print(f"Baseline quadgram score: {scorer.average(dec_text):.3f}")

# Let's test various columnar transpositions on dec_text
# Widths 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 24, 29
best_sc = -999.0
best_hit = ""

for w in range(3, 25):
    # standard columnar read (write by rows, read by cols, or write by cols, read by rows)
    # 1. write rows of width w, read cols
    rows = (97 + w - 1) // w
    # incomplete grid:
    # number of full cols:
    rem = 97 % w
    col_lens = [rows if (rem == 0 or c < rem) else rows - 1 for c in range(w)]
    
    # Try reading down columns in natural order:
    grid = []
    idx = 0
    for r in range(rows):
        row = []
        for c in range(w):
            if idx < 97:
                row.append(dec_text[idx])
                idx += 1
            else:
                row.append('')
        grid.append(row)
        
    # read down columns
    cols_text = []
    for c in range(w):
        for r in range(rows):
            if grid[r][c] != '':
                cols_text.append(grid[r][c])
    cand1 = "".join(cols_text)
    sc1 = scorer.average(cand1)
    if sc1 > best_sc:
        best_sc = sc1
        best_hit = f"Write rows, read cols (w={w}): sc={sc1:.3f}"
        
    # 2. write cols, read rows
    grid2 = [['' for _ in range(w)] for _ in range(rows)]
    idx = 0
    for c in range(w):
        for r in range(col_lens[c]):
            grid2[r][c] = dec_text[idx]
            idx += 1
    cand2 = "".join("".join(grid2[r]) for r in range(rows))
    sc2 = scorer.average(cand2)
    if sc2 > best_sc:
        best_sc = sc2
        best_hit = f"Write cols, read rows (w={w}): sc={sc2:.3f}"

print(f"Best simple transposition: {best_hit}")

# Also test reversing the text:
sc_rev = scorer.average(dec_text[::-1])
print(f"Reversed text score: {sc_rev:.3f}")

