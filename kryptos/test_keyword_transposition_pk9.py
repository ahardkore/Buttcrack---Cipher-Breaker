import numpy as np

# Confirmed and thematic keywords
keywords_pool = [
    # K1-K4 keywords and plaintexts
    "KRYPTOS", "PALIMPSEST", "ABSCISSA", "ORDINATE", "PENTIMENTO",
    "SANBORN", "SCHEIDT", "WEBSTER", "LANGLEY", "VIRGINIA",
    "BERLIN", "CLOCK", "BERLINCLOCK", "EASTNORTHEAST", "NORTHEAST",
    "SHADOW", "FORCES", "LUCID", "MEMORY", "DIGETAL", "VIRTUALLY",
    "INVISIBLE", "INTERPRETATION", "CARTER", "TUTANKHAMUN",
    # PK1-PK8 keywords & narrative
    "PROVENANCE", "PORTAL", "WHITESMITH", "BLACKSMITH", "WORKSHOP",
    "APPRENTICE", "NEEDLE", "NEEDLES", "DRAWPLATE", "DRAWING",
    "TEMPERING", "TEMPER", "BELLOWS", "HEARTH", "FURNACE", "CRUCIBLE",
    "CRUCIBLES", "SILVER", "COPPER", "HAMMER", "HAMMERS", "ANVIL",
    "ANVILS", "TONGS", "PINCERS", "FORCEPS", "GRAVER", "CHISEL",
    "PUNCH", "PUNCHING", "PUNCHED", "QUENCHING", "QUENCHED",
    "ANNEALING", "ANNEALED", "ALLOY", "BRASS", "ORGANARIUM",
    "THEOPHILUS", "PRESBYTER", "ROGER", "HELMARSHAUSEN",
    # Specific length 12 words
    "WHITESMITHS", "APPRENTICES", "INTERPRETAT", "TRANSPOSITIO",
    "SUBSTITUTION", "METALLURGIST", "EXQUISITELY", "HELMARSHAUSE",
    "ORGANARIUMS", "DRAWPLATES__", "TEMPERING___", "PURIFYING___"
]

def word_to_order(word):
    # argsort with stable tie-breaking
    indexed = [(ch, i) for i, ch in enumerate(word.upper()) if ch.isalpha()]
    sorted_idx = sorted(indexed, key=lambda x: x[0])
    order = [x[1] for x in sorted_idx]
    return order

# Candidate Z stream
Z = "VTNWCSTYVVOVISENZXAVVTOSQMSKJSEMHJPWDLASHEYGXNOSEHREOTNSYNOEATLLOOLTEEAIRRPEPXTATEMSINSFQMSUDOILISUTCTBEUCYWADMAYNCDSCOUHTJTSSUMKATTIEUWFWFAEHIK"
N = len(Z)

# Load quadgrams
quad = {}
with open("english_quads.tsv") as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) == 2 and len(parts[0]) == 4:
            quad[parts[0]] = float(parts[1])

def score_text(pt):
    sc = sum(quad.get(pt[i:i+4], -9.5) for i in range(len(pt) - 3))
    return sc / (len(pt) - 3)

def col_decrypt(ct, width, order):
    h = len(ct) // width
    grid = [[None] * width for _ in range(h)]
    k = 0
    for m in range(width):
        col = order[m]
        for r in range(h):
            grid[r][col] = ct[k]
            k += 1
    return "".join("".join(row) for row in grid)

print(f"Testing single and double keyword columnar transpositions on Z (len {N})...")

# 1. Single columnar on widths dividing 144
for w in [6, 8, 9, 12, 16, 18, 24]:
    # Generate orders from keywords of length w or truncation/padding
    orders = []
    for kw in keywords_pool:
        clean = ''.join(c for c in kw.upper() if c.isalpha())
        if len(clean) >= w:
            orders.append((clean[:w], word_to_order(clean[:w])))
    
    for kw_str, o in orders:
        pt = col_decrypt(Z, w, o)
        sc = score_text(pt)
        if sc > -5.2:
            print(f"HIT Single Col [W={w} Key={kw_str}]: sc={sc:.4f} | {pt[:60]}...")

# 2. Double columnar across pairs of keywords
orders_by_w = {}
for w in [8, 9, 12]:
    orders_by_w[w] = []
    for kw in keywords_pool:
        clean = ''.join(c for c in kw.upper() if c.isalpha())
        if len(clean) >= w:
            orders_by_w[w].append((clean[:w], word_to_order(clean[:w])))

for w1 in [8, 9, 12]:
    w2 = 144 // (144 // w1) # e.g. 12, 12
    for kw1, o1 in orders_by_w[w1]:
        for kw2, o2 in orders_by_w.get(w1, []):
            # T1 then T2: decrypt T2 then T1
            mid = col_decrypt(Z, w1, o2)
            pt = col_decrypt(mid, w1, o1)
            sc = score_text(pt)
            if sc > -5.2:
                print(f"HIT Double Col [({w1},{w1}) Keys=({kw1},{kw2})]: sc={sc:.4f} | {pt[:60]}...")

print("Keyword transposition test complete.")
