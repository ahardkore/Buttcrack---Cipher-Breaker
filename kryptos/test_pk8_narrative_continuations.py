import numpy as np, sys, time, itertools
sys.path.insert(0, 'buttcrack/src')
from buttcrack.additive_crib import _periods, _row, _alphabet
from buttcrack.wordlm import word_segment

pk8 = 'COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY'
ps = [4, 5, 6, 7]
alpha = _alphabet('KRYPTOS')
index = {c: i for i, c in enumerate(alpha)}
k2std = np.array([ord(c) - ord('A') for c in alpha], dtype=np.int32)
ct_kr = np.array([index[c] for c in pk8], dtype=int)

quad = np.fromfile('quad.bin', dtype=np.float32).reshape(26, 26, 26, 26)

M = np.array([_row(t, ps) for t in range(153)], dtype=int)
A0 = M[0 : 18]
W0 = np.linalg.lstsq(A0.T, M.T, rcond=None)[0].T
W0_int = np.round(W0).astype(int)
D = (ct_kr - (W0_int @ ct_kr[:18])) % 26

# Generate all natural continuations from PK7
openers = [
    # Nine days continuations
    "AFTER NINE DAYS", "FOR NINE DAYS", "ON THE TENTH DAY", "WHEN NINE DAYS",
    "THE NINE DAYS", "NINE DAYS IN THE", "NINE DAYS PASSED", "NINE DAYS HE",
    "NINE DAYS WE", "NINE DAYS I", "THROUGH NINE DAYS", "DURING NINE DAYS",
    "AT THE END OF NINE", "AFTER THE NINE DAYS",
    # Actions
    "HE DREW THE", "HE TOOK THE", "HE PULLED THE", "HE HELD THE", "HE REMOVED THE",
    "HE WITHDREW THE", "HE PLACED THE", "HE LAID THE", "HE SET THE",
    "WITH LONG TONGS HE", "WITH HIS TONGS HE", "UPON THE ANVIL HE",
    "AT LAST THE", "AT LAST HE", "AT LAST WE", "AT LAST I",
    "THE STEEL WAS", "THE IRON WAS", "THE PIECE WAS", "THE METAL WAS",
    "PURIFIED IN THE", "PURIFIED BY THE", "PURIFIED AT LAST",
    "I WATCHED AS HE", "I WATCHED HIM", "I TENDED THE", "I PUMPED THE",
    "WE WATCHED AS", "WE WAITED AS", "WE WAITED FOR",
    "DAY AFTER DAY", "EACH DAY HE", "EACH DAY I", "EACH DAY WE",
    "NOW HE SAID", "THEN HE SAID", "FIRST HE SAID",
    "TO FORGE THE", "TO MAKE THE", "TO DRAW THE", "DRAWING THE",
    "THE NEEDLE", "A NEEDLE", "ONE NEEDLE"
]

actions = [
    "HE DREW THE STEEL", "HE DREW THE IRON", "HE DREW THE METAL",
    "HE PULLED THE STEEL", "HE PULLED THE IRON", "HE TOOK THE STEEL",
    "HE TOOK THE IRON", "HE TOOK UP THE", "HE TOOK HIS",
    "HE LAID THE STEEL", "HE PLACED THE STEEL", "HE SET THE STEEL",
    "HE HELD THE STEEL", "HE HELD THE TONGS", "HE STRUCK THE STEEL",
    "HE BEAT THE STEEL", "HE HAMMERED THE", "HE BEGAN TO DRAW",
    "HE BEGAN TO FORGE", "HE BEGAN TO WORK", "HE BEGAN THE WORK",
    "THE STEEL WAS READY", "THE IRON WAS READY", "THE WORK BEGAN",
    "WE BEGAN TO FORGE", "WE BEGAN TO DRAW", "I TOOK THE HAMMER",
    "I HELD THE TONGS", "I WATCHED HIM DRAW", "I WATCHED HIM FORGE",
    "IN THE WHITE COALS", "IN THE WHITE HEAT", "IN THE FLAME HE",
    "FROM THE HEARTH HE", "FROM THE COALS HE", "FROM THE FIRE HE"
]

conts = [
    "FROM THE FLAME", "FROM THE FIRE", "FROM THE COALS", "FROM THE HEARTH",
    "OUT OF THE FLAME", "OUT OF THE FIRE", "OUT OF THE COALS",
    "UPON THE ANVIL", "ON THE ANVIL", "WITH HIS TONGS", "WITH LONG TONGS",
    "AND LAID IT UPON", "AND PLACED IT ON", "AND STRUCK IT WITH",
    "AND BEGAN TO BEAT", "AND BEGAN TO DRAW", "INTO A FINE WIRE",
    "INTO A SLENDER", "THROUGH THE DIE", "THROUGH THE HOLE",
    "TO MAKE A NEEDLE", "TO FORGE A NEEDLE", "OF HIS OWN MAKING",
    "OF MY OWN MAKING", "UNTIL IT WAS THIN", "UNTIL IT WAS FINE"
]

candidates = set()
for o in openers:
    for a in actions:
        candidates.add(f"{o} {a}")
for a in actions:
    for c in conts:
        candidates.add(f"{a} {c}")

prefixes18 = set()
for cand in candidates:
    clean = "".join(ch for ch in cand.upper() if 'A' <= ch <= 'Z')
    if len(clean) >= 18:
        prefixes18.add(clean[:18])

prefix_list = sorted(list(prefixes18))
print(f"Generated {len(prefix_list)} unique 18-character candidate prefixes.")

t0 = time.time()
c_kr_all = np.array([[index[c] for c in p] for p in prefix_list], dtype=int)
k_win = (ct_kr[0:18] - c_kr_all) % 26
full_k = (k_win @ W0_int.T) % 26
pt_kr = (ct_kr - full_k) % 26
pt_std = k2std[pt_kr]

scores = quad[pt_std[:, :-3], pt_std[:, 1:-2], pt_std[:, 2:-1], pt_std[:, 3:]].sum(axis=1) / 150.0

top_indices = np.argsort(scores)[::-1][:15]
print(f"Evaluated {len(prefix_list)} prefixes in {time.time()-t0:.3f}s!\n")

for rank, idx in enumerate(top_indices):
    pt_str = "".join(chr(ord('A') + c) for c in pt_std[idx])
    seg = word_segment(pt_str)
    print(f"Rank {rank+1:2d}: Score {scores[idx]:.4f} | LongCov: {seg.long_coverage:.2f} | Prefix: {prefix_list[idx]}")
    print(f"  {pt_str[:75]}")
    print(f"  {pt_str[75:]}\n")
