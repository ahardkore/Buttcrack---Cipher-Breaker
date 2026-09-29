import json

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
ct9 = cts['PK9']
n = len(ct9)

# Load quadgrams
with open('english_quads.tsv') as f:
    lines = f.readlines()
log_probs = {}
for line in lines:
    q, sc = line.strip().split('\t')
    log_probs[q] = float(sc)

def score_text(txt):
    return sum(log_probs.get(txt[i:i+4], -8.0) for i in range(len(txt)-3)) / (len(txt)-3)

# Precompute dictionary permutations for widths 6, 8, 9, 12, 16
perms_by_w = {}
for w in [6, 8, 9, 12, 16]:
    perms = set()
    with open('words_alpha.txt') as f:
        for line in f:
            word = line.strip().upper()
            if len(word) == w:
                p = tuple(sorted(range(w), key=lambda i: (word[i], i)))
                perms.add(p)
    perms_by_w[w] = list(perms)
    print(f'Width {w}: loaded {len(perms_by_w[w])} permutations')

keys = ['WEBSTER', 'WOMACKA', 'WILLIAM', 'WALTERW', 'LANGLEY', 'BERLINS', 'KRYPTOS', 'SANBORN', 'SCHEIDT', 'PALIMPS',
        'PROVENA', 'MARGINS', 'ORDINAT', 'PORTALS', 'NEEDLES', 'WHITESM', 'FORGING', 'HEARTHS']

def invert_columnar(M, W, perm):
    rows = n // W
    cols = [M[i*rows : (i+1)*rows] for i in range(W)]
    # perm[c_idx] is the original column index of the c_idx-th column in M
    # grid[r][perm[c_idx]] = cols[c_idx][r]
    grid = [[None]*W for _ in range(rows)]
    for c_idx in range(W):
        orig_col = perm[c_idx]
        for r in range(rows):
            grid[r][orig_col] = cols[c_idx][r]
    return ''.join(''.join(row) for row in grid)

best_overall = (-999.0, '', 0, (), '')

for k in keys:
    shifts = [ALPH.index(c) for c in k]
    for mode, sgn in [('Q3', -1), ('Q3_rev', 1)]:
        if sgn == -1:
            M = ''.join(ALPH[(ALPH.index(ct9[i]) - shifts[i % len(k)]) % 26] for i in range(n))
        else:
            M = ''.join(ALPH[(ALPH.index(ct9[i]) + shifts[i % len(k)]) % 26] for i in range(n))
        
        for w in [6, 8, 9, 12, 16]:
            for p in perms_by_w[w]:
                pt = invert_columnar(M, w, p)
                sc = score_text(pt)
                if sc > best_overall[0]:
                    best_overall = (sc, k, w, p, pt)
                    if sc > -5.5:
                        print(f'HIT: sc={sc:.3f} | key={k} mode={mode} w={w} | PT={pt[:50]}...')

print('\nTesting complete.')
print(f'Best overall: score={best_overall[0]:.3f} | key={best_overall[1]} w={best_overall[2]}')
print(f'PT: {best_overall[4]}')
