import json
from buttcrack.scoring import get_scorer as resolve_scorer

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
C = cts['PK9']
N = len(C)

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
scorer = resolve_scorer('quadgrams', 'english')
s13 = [0, 2, 9, 10, 10, 6, 7]

# Define route generators for a grid of shape (rows, cols)
def gen_routes(rows, cols):
    routes = {}
    
    # 1. Row-major forward (identity)
    routes['row_major_fwd'] = [r * cols + c for r in range(rows) for c in range(cols)]
    
    # 2. Row-major reverse
    routes['row_major_rev'] = routes['row_major_fwd'][::-1]
    
    # 3. Col-major forward (standard transpose)
    routes['col_major_fwd'] = [r * cols + c for c in range(cols) for r in range(rows)]
    
    # 4. Col-major reverse
    routes['col_major_rev'] = routes['col_major_fwd'][::-1]
    
    # 5. Serpentine rows (boustrophedon)
    serp_r = []
    for r in range(rows):
        if r % 2 == 0:
            serp_r.extend(r * cols + c for c in range(cols))
        else:
            serp_r.extend(r * cols + c for c in range(cols - 1, -1, -1))
    routes['serpentine_rows'] = serp_r
    
    # 6. Serpentine cols
    serp_c = []
    for c in range(cols):
        if c % 2 == 0:
            serp_c.extend(r * cols + c for r in range(rows))
        else:
            serp_c.extend(r * cols + c for r in range(rows - 1, -1, -1))
    routes['serpentine_cols'] = serp_c

    # 7. Spiral clockwise inward from top-left
    top, bottom, left, right = 0, rows - 1, 0, cols - 1
    spiral = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1): spiral.append(top * cols + c)
        top += 1
        for r in range(top, bottom + 1): spiral.append(r * cols + right)
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1): spiral.append(bottom * cols + c)
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1): spiral.append(r * cols + left)
            left += 1
    if len(spiral) == N:
        routes['spiral_cw_in'] = spiral
        routes['spiral_cw_out'] = spiral[::-1]

    # 8. Diagonals (anti-diagonals)
    diag = []
    for s in range(rows + cols - 1):
        for r in range(rows):
            c = s - r
            if 0 <= c < cols:
                diag.append(r * cols + c)
    if len(diag) == N:
        routes['diagonal_fwd'] = diag
        routes['diagonal_rev'] = diag[::-1]

    return routes

geometries = [
    (12, 12),
    (16, 9),
    (9, 16),
    (18, 8),
    (8, 18),
    (24, 6),
    (6, 24)
]

print("Sweeping all route transpositions across 7 geometries and 128 parity masks...")

best_sc = -999.0
best_info = None

for rows, cols in geometries:
    routes = gen_routes(rows, cols)
    for r_name, perm in routes.items():
        # Evaluate both forward mapping and inverse mapping
        # inv_perm: pt[i] = Z[perm[i]] vs Z[i] = pt[perm[i]]
        inv_perm = [0] * N
        for i, p in enumerate(perm): inv_perm[p] = i

        for mask in range(128):
            shifts = [(s13[i] + 13 * ((mask >> i) & 1)) % 26 for i in range(7)]
            z = [ALPH_K[(ALPH_K.index(ch) - shifts[i % 7]) % 26] for i, ch in enumerate(C)]
            
            # Forward route: pt[i] = z[perm[i]]
            pt1 = "".join(z[perm[i]] for i in range(N))
            sc1 = scorer.average(pt1)
            if sc1 > best_sc:
                best_sc = sc1
                best_info = (f"({rows}x{cols}) {r_name} fwd | mask={mask:07b}", sc1, pt1)
                if sc1 > -6.0:
                    print(f"  >>> HIT: {best_info[0]} sc={sc1:.3f}\n    PT: {pt1}")

            # Inverse route: pt[i] = z[inv_perm[i]]
            pt2 = "".join(z[inv_perm[i]] for i in range(N))
            sc2 = scorer.average(pt2)
            if sc2 > best_sc:
                best_sc = sc2
                best_info = (f"({rows}x{cols}) {r_name} inv | mask={mask:07b}", sc2, pt2)
                if sc2 > -6.0:
                    print(f"  >>> HIT: {best_info[0]} sc={sc2:.3f}\n    PT: {pt2}")

print(f"\nCompleted! Best route: {best_info[0]} | sc={best_info[1]:.3f}")
print(f"PT: {best_info[2][:75]}...")
