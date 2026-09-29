import itertools
from collections import Counter

# Load quadgrams
quads = {}
with open('english_quads.tsv') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 2:
            quads[parts[0]] = float(parts[1])

def score_text(text):
    return sum(quads.get(text[i:i+4], -9.5) for i in range(len(text)-3)) / (len(text)-3)

# Top candidate Z stream from list_top_z
Z = "VTNWCSTYVVOVISENZXAVVTOSQMSKJSEMHJPWDLASHEYGXNOSEHREOTNSYNOEATLLOOLTEEAIRRPEPXTATEMSINSFQMSUDOILISUTCTBEUCYWADMAYNCDSCOUHTJTSSUMKATTIEUWFWFAEHIK"
N = len(Z)

print("Testing AMSCO transposition on Z...")
best_sc = -999.0
best_pt = ""
best_kw = ""

for W in [5, 6, 7, 8]:
    # Test all permutations of width W
    perms = list(itertools.permutations(range(W)))
    if len(perms) > 5040:
        # Sample for larger widths
        import random
        random.seed(42)
        perms = random.sample(perms, 5000)
        
    for p in perms:
        for start_pat in [0, 1]: # start with 1-2-1-2 or 2-1-2-1
            # Build AMSCO grid
            # In AMSCO, characters are placed in columns in blocks of 1 and 2
            # Let's compute column lengths
            col_lens = [0] * W
            cur_len = 0
            row = 0
            pat = start_pat
            while cur_len < N:
                for c in range(W):
                    block_sz = 1 if ((row + c + pat) % 2 == 0) else 2
                    if cur_len + block_sz > N:
                        block_sz = N - cur_len
                    col_lens[c] += block_sz
                    cur_len += block_sz
                    if cur_len >= N:
                        break
                row += 1
                
            # Extract columns from Z based on perm p
            cols = []
            idx = 0
            # If Z was read column by column:
            valid = True
            col_data = {}
            for col_idx in p:
                l = col_lens[col_idx]
                col_data[col_idx] = Z[idx:idx+l]
                idx += l
                
            # Read out by rows
            pt_chars = []
            cur_pos = [0] * W
            row = 0
            while len(pt_chars) < N:
                for c in range(W):
                    block_sz = 1 if ((row + c + pat) % 2 == 0) else 2
                    cp = cur_pos[c]
                    avail = min(block_sz, len(col_data[c]) - cp)
                    if avail > 0:
                        pt_chars.append(col_data[c][cp:cp+avail])
                        cur_pos[c] += avail
                    if len(pt_chars) >= N:
                        break
                row += 1
            pt = "".join(pt_chars)
            sc = score_text(pt)
            if sc > best_sc:
                best_sc = sc
                best_pt = pt
                best_kw = f"W={W}, start={start_pat}, perm={p}"
                if sc > -5.5:
                    print(f"AMSCO HIT! {best_kw}: sc={sc:.4f} | {pt}")

print(f"AMSCO best overall: {best_kw}: sc={best_sc:.4f} | {best_pt[:60]}")
