W, H = 12, 12
perm = [3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10]

# out[r * 12 + c] = z[perm[c] * 12 + r]
# where z[i] is decrypted with shift[i % 28].
# So the character at plaintext position (r, c) comes from z index: i = perm[c] * 12 + r.
# And its shift is i % 28!

print("Plaintext Grid with Shift Indices (0..27) for each cell:")
for r in range(H):
    row_shifts = []
    for c in range(W):
        i = perm[c] * 12 + r
        s_idx = i % 28
        row_shifts.append(f"{s_idx:2d}")
    print(f"Row {r:2d}: " + " ".join(row_shifts))
