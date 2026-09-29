import json

with open("pk_all_ciphertexts.json") as f:
    ct10 = json.load(f)["PK10"]

def word_to_perm(w):
    indexed = sorted(enumerate(w), key=lambda x: x[1])
    perm = [0]*len(w)
    for rank, (orig_pos, _) in enumerate(indexed):
        perm[orig_pos] = rank
    return perm

def ioc(nums):
    counts = {}
    for c in nums: counts[c] = counts.get(c, 0) + 1
    n = len(nums)
    if n <= 1: return 0.0
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))

def period_ioc(nums, p):
    slices = [nums[i::p] for i in range(p)]
    return sum(ioc(s) for s in slices if len(s) > 1) / p

keywords = [
    # 7-letter words
    "UNRAVEL", "KRYPTOS", "NEEDLES", "DRAWPIN", "HAMMERS", "STRIKES", "ANVILSS",
    "FORGING", "SMITHSY", "BURNING", "GLOWING", "HEATING", "FURNACE", "BELLOWS",
    "CHISELS", "QUENCHY", "ANNEALS", "TEMPERS", "PIERCED", "PUNCHED", "PELLEGR",
    # 8-letter words
    "TREASURE", "PRACTICE", "WORKSHOP", "MORESQUE", "ARABIQUE", "YTALIQUE",
    "DRAWPLAT", "HERMETIC", "ALCHEMIC", "ANATOMIS", "SURGICAL", "OBSIDIAN",
    # 9-letter words
    "UNRAVELED", "PELLEGRIN", "ARCHIVIST", "ACCESSION", "BLACKBIRD", "COMPLETED",
    "THREADING", "NEEDLEMAN", "SCULPTURE", "WHITEHEAT", "SECRETKEY"
]

ct_nums = [ord(c) - 65 for c in ct10]

print("Testing candidate keywords on PK10...")
for kw in keywords:
    W = len(kw)
    H = 504 // W
    perm = word_to_perm(kw)
    
    # Model 1: CT is columns, read row-by-row
    Z1 = [0]*504
    for r in range(H):
        for c in range(W):
            Z1[r * W + c] = ct_nums[perm[c] * H + r]
            
    # Check periods 7, 8, 9, 56, 63, 72
    iocs1 = {p: period_ioc(Z1, p) for p in [7, 8, 9, 56, 63, 72]}
    max_p1 = max(iocs1, key=iocs1.get)
    if iocs1[max_p1] > 0.048:
        print(f"Keyword {kw:<12} (W={W:2d}) Model 1: max IoC = {iocs1[max_p1]:.4f} at period {max_p1}")

    # Model 2: CT is rows, read col-by-col
    Z2 = [0]*504
    for c in range(W):
        for r in range(H):
            Z2[r * W + c] = ct_nums[r * W + perm[c]]
            
    iocs2 = {p: period_ioc(Z2, p) for p in [7, 8, 9, 56, 63, 72]}
    max_p2 = max(iocs2, key=iocs2.get)
    if iocs2[max_p2] > 0.048:
        print(f"Keyword {kw:<12} (W={W:2d}) Model 2: max IoC = {iocs2[max_p2]:.4f} at period {max_p2}")
