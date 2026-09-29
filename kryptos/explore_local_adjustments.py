import json

ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
k2std = [ord(c) - ord('A') for c in ALPH]
hpos = {c: i for i, c in enumerate(ALPH)}

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)

undone = cts['PK9_UNDONE']

base_key = 'FNCEPSOOHGUMAA'
base_shifts = [hpos[c] for c in base_key]

with open('all_words.txt') as f:
    words = set(w.strip().upper() for w in f if len(w.strip()) >= 3 and w.strip().isalpha())

def eval_shifts(shifts):
    pt = []
    for i, ch in enumerate(undone):
        s = shifts[i % 14]
        p_kr = (hpos[ch] - s) % 26
        pt.append(chr(ord('A') + k2std[p_kr]))
    pt_str = ''.join(pt)
    
    # Word count
    found = []
    for l in range(3, 12):
        for i in range(len(pt_str) - l + 1):
            w = pt_str[i:i+l]
            if w in words:
                found.append((i, w))
    return pt_str, len(found)

# Let's test varying each column from 0 to 25 while keeping the other 13 columns fixed
cur_shifts = base_shifts.copy()
pt_str, best_words = eval_shifts(cur_shifts)
print(f"Base Key: {base_key} | Words found: {best_words}")

improved = True
pass_num = 0
while improved:
    improved = False
    pass_num += 1
    for col in range(14):
        best_s = cur_shifts[col]
        best_w = best_words
        old_s = cur_shifts[col]
        for s in range(26):
            if s == old_s:
                continue
            cur_shifts[col] = s
            _, n_w = eval_shifts(cur_shifts)
            if n_w > best_w:
                best_w = n_w
                best_s = s
        if best_w > best_words:
            print(f"Pass {pass_num}, Col {col:2d}: shifted {ALPH[old_s]} -> {ALPH[best_s]} | Words: {best_words} -> {best_w}")
            cur_shifts[col] = best_s
            best_words = best_w
            improved = True
        else:
            cur_shifts[col] = old_s

final_key = ''.join(ALPH[s] for s in cur_shifts)
final_pt, final_words = eval_shifts(cur_shifts)

print(f"\nFinal Optimized Key: {final_key} | Total Words: {final_words}")
print(f"Final Plaintext:\n{final_pt}")
print("\nRows of Plaintext:")
for r in range(11):
    print(f"  Row {r:2d}: {final_pt[r*14:min((r+1)*14, len(final_pt))]}")
