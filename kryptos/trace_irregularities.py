p1 = [5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6]
p2 = [4, 0, 6, 5, 3, 2, 7, 1]
W1, H1 = 18, 8
W2, H2 = 8, 18
N = 144

# We want to know: for a plaintext position (r, c), which original index t in Z does it come from?
# Plaintext is pt[r * W1 + c]
# invert_col(mid, W1, H1, p1, pt):
# mid was read into cols by p1, read by rows to pt
# Specifically:
# col_order in p1: col = p1[c_idx].
# pt[r * W1 + col] = mid[idx++]
# Let's map pt index -> mid index -> Z index:

pt_to_mid = [None] * N
idx = 0
for c_idx in range(W1):
    col = p1[c_idx]
    for r in range(H1):
        pt_to_mid[r * W1 + col] = idx
        idx += 1

mid_to_z = [None] * N
idx = 0
for c_idx in range(W2):
    col = p2[c_idx]
    for r in range(H2):
        mid_to_z[r * W2 + col] = idx
        idx += 1

# Now pt_to_z[t_pt] gives the index in Z
pt_to_z = [mid_to_z[pt_to_mid[i]] for i in range(N)]

# Look at Row 0 chars 0..4: 'JVRMB'
print("Row 0, chars 0..4 ('JVRMB'):")
for c in range(5):
    pt_idx = c
    z_idx = pt_to_z[pt_idx]
    shift_idx = z_idx % 28
    print(f"  Pos {c}: PT char at {pt_idx} comes from Z[{z_idx}] (shift index {shift_idx} mod 28)")

# Look at Row 1 chars 12..17: 'SKWJER'
print("\nRow 1, chars 12..17 ('SKWJER'):")
for c in range(12, 18):
    pt_idx = 1 * W1 + c
    z_idx = pt_to_z[pt_idx]
    shift_idx = z_idx % 28
    print(f"  Pos {c}: PT char at {pt_idx} comes from Z[{z_idx}] (shift index {shift_idx} mod 28)")

# Look at Row 4 chars 13..17: 'AAUON'
print("\nRow 4, chars 13..17 ('AAUON'):")
for c in range(13, 18):
    pt_idx = 4 * W1 + c
    z_idx = pt_to_z[pt_idx]
    shift_idx = z_idx % 28
    print(f"  Pos {c}: PT char at {pt_idx} comes from Z[{z_idx}] (shift index {shift_idx} mod 28)")
