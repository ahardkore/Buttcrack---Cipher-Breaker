import numpy as np, sys, time, re
sys.path.insert(0, 'buttcrack/src')
from buttcrack.additive_crib import _periods, _row, _alphabet
from buttcrack.wordlm import word_segment

pk8 = 'COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY'
ps = [4, 5, 6, 7]
alpha = _alphabet('KRYPTOS')
index = {c: i for i, c in enumerate(alpha)}
k2std = np.array([ord(c) - ord('A') for c in alpha], dtype=np.int32)
std2kr = np.array([alpha.index(chr(ord('A') + i)) for i in range(26)], dtype=np.int32)
ct_kr = np.array([index[c] for c in pk8], dtype=int)

# Load quadgrams from binary
quad = np.fromfile('quad.bin', dtype=np.float32).reshape(26, 26, 26, 26)

# Design matrix and unimodular basis for window 0..17
M = np.array([_row(t, ps) for t in range(153)], dtype=int)
A0 = M[0 : 18]
W0 = np.linalg.lstsq(A0.T, M.T, rcond=None)[0].T
W0_int = np.round(W0).astype(int)
D = (ct_kr - (W0_int @ ct_kr[:18])) % 26

# Load vocabulary
with open('all_words.txt') as f:
    dict_set = set(line.strip() for line in f)

# Filter words from Hendrie and narrative
word_counts = {}
for fname in ['theophilus_book3_english.txt', 'pk_submission_manifest.json']:
    with open(fname, errors='ignore') as f:
        for w in re.findall(r'[A-Z]+', f.read().upper()):
            if w in dict_set and 2 <= len(w) <= 12:
                word_counts[w] = word_counts.get(w, 0) + 1

# List of common English words to add
common_extra = [
    'HE', 'WE', 'I', 'THE', 'AND', 'IN', 'OF', 'IT', 'TO', 'WITH', 'FOR', 'AT', 'ON', 'BY', 'AS', 'UPON',
    'AFTER', 'WHEN', 'THEN', 'NOW', 'ONCE', 'SOON', 'EACH', 'EVERY', 'ALL', 'BEFORE', 'DURING', 'WHILE',
    'DAY', 'DAYS', 'NINE', 'TEN', 'YEARS', 'YEAR', 'TIME', 'HOURS', 'FIRST', 'SECOND', 'LAST', 'END',
    'SMITH', 'WHITESMITH', 'MASTER', 'APPRENTICE', 'MAN', 'WORK', 'WORKSHOP', 'SHOP', 'TRADE',
    'FIRE', 'HEARTH', 'FORGE', 'COALS', 'FLAME', 'HEAT', 'WHITE', 'HOT', 'GLOWING', 'BURNING',
    'STEEL', 'IRON', 'METAL', 'WIRE', 'NEEDLE', 'ROD', 'PIECE', 'STRAND', 'THREAD',
    'HAMMER', 'ANVIL', 'TONGS', 'BELLOWS', 'DRAWPLATE', 'PLATE', 'DIE', 'DIES', 'HOLE', 'HOLES',
    'PUNCH', 'CHISEL', 'FILE', 'WHETSTONE', 'WATER', 'OIL', 'TROUGH',
    'TOOK', 'DREW', 'PULLED', 'HELD', 'PLACED', 'LAID', 'STRUCK', 'BEAT', 'HAMMERED', 'TENDED',
    'BEGAN', 'STARTED', 'MADE', 'WORKED', 'STUDIED', 'LEARNED', 'WATCHED', 'WAITED', 'KEPT',
    'TEMPERED', 'PURIFIED', 'HEATED', 'COOLED', 'QUENCHED', 'SHAPED', 'FORMED', 'DRAWN',
    'SAID', 'TOLD', 'SPOKE', 'WARNED', 'SHOWED', 'EXPLAINED', 'ASKED', 'ANSWERED',
    'COULD', 'WOULD', 'SHOULD', 'MIGHT', 'MUST', 'WAS', 'WERE', 'HAD', 'BEEN',
    'FINE', 'THIN', 'SLENDER', 'SHARP', 'ROUND', 'SMOOTH', 'SOFT', 'HARD',
    'ENOUGH', 'PATIENCE', 'SKILL', 'CARE', 'SECRET', 'PRACTICE', 'RESIDUE',
    'KNOT', 'ARCHIVE', 'PELLEGRIN', 'TEXTILES', 'TREATISE'
]

for w in common_extra:
    word_counts[w] = word_counts.get(w, 0) + 500

# Remove obvious Latin words
latin_stop = {'CUM', 'UT', 'DE', 'QUOD', 'AD', 'SUPER', 'SED', 'NON', 'SI', 'ET', 'PER', 'EX', 'ITA', 'HOC', 'HAEC'}
vocab = [w for w, c in word_counts.items() if w not in latin_stop and c >= 2]
vocab.sort(key=lambda w: (-word_counts[w], len(w)))
print(f'Active vocabulary size: {len(vocab)} words')

# Fast forward evaluation function
def check_prefix_validity(p_kr, length):
    # p_kr is array of length >= 14
    if length >= 14:
        p34 = k2std[(D[34] + np.dot(W0_int[34, :14], p_kr[:14])) % 26]
        p35 = k2std[(D[35] + np.dot(W0_int[35, :14], p_kr[:14])) % 26]
        p36 = k2std[(D[36] + np.dot(W0_int[36, :14], p_kr[:14])) % 26]
        p37 = k2std[(D[37] + np.dot(W0_int[37, :14], p_kr[:14])) % 26]
        if quad[p34, p35, p36, p37] < -8.0:
            return False
            
    if length >= 15:
        p38 = k2std[(D[38] + np.dot(W0_int[38, :15], p_kr[:15])) % 26]
        if quad[p35, p36, p37, p38] < -8.0:
            return False
            
    if length >= 16:
        p39 = k2std[(D[39] + np.dot(W0_int[39, :16], p_kr[:16])) % 26]
        p47 = k2std[(D[47] + np.dot(W0_int[47, :16], p_kr[:16])) % 26]
        p48 = k2std[(D[48] + np.dot(W0_int[48, :16], p_kr[:16])) % 26]
        p49 = k2std[(D[49] + np.dot(W0_int[49, :16], p_kr[:16])) % 26]
        p50 = k2std[(D[50] + np.dot(W0_int[50, :16], p_kr[:16])) % 26]
        p64 = k2std[(D[64] + np.dot(W0_int[64, :16], p_kr[:16])) % 26]
        p65 = k2std[(D[65] + np.dot(W0_int[65, :16], p_kr[:16])) % 26]
        p66 = k2std[(D[66] + np.dot(W0_int[66, :16], p_kr[:16])) % 26]
        p67 = k2std[(D[67] + np.dot(W0_int[67, :16], p_kr[:16])) % 26]
        p71 = k2std[(D[71] + np.dot(W0_int[71, :16], p_kr[:16])) % 26]
        p72 = k2std[(D[72] + np.dot(W0_int[72, :16], p_kr[:16])) % 26]
        p73 = k2std[(D[73] + np.dot(W0_int[73, :16], p_kr[:16])) % 26]
        p74 = k2std[(D[74] + np.dot(W0_int[74, :16], p_kr[:16])) % 26]
        
        if quad[p36, p37, p38, p39] < -8.0: return False
        if quad[p47, p48, p49, p50] < -8.0: return False
        if quad[p64, p65, p66, p67] < -8.0: return False
        if quad[p71, p72, p73, p74] < -8.0: return False

    return True

print('Forward validator compiled. Testing search across opening words...')

# Opening word candidates
starters = [
    'FOR', 'AFTER', 'ON', 'WITH', 'IN', 'AT', 'FROM', 'BY', 'THROUGH', 'UPON', 'BEFORE',
    'WHEN', 'THEN', 'NOW', 'ONCE', 'SOON', 'DAY', 'NINE', 'TEN',
    'HE', 'I', 'WE', 'THE', 'EACH', 'EVERY'
]

hits = []
nodes_evaluated = 0

t0 = time.time()
for w1 in starters:
    # DFS from w1
    stack = [(w1, [w1])]
    while stack:
        cur_str, cur_words = stack.pop()
        nodes_evaluated += 1
        
        # Check pruning if length >= 14
        if len(cur_str) >= 14:
            p_kr = std2kr[[ord(c) - ord('A') for c in cur_str[:18]]]
            if not check_prefix_validity(p_kr, len(cur_str)):
                continue
                
        if len(cur_str) >= 18:
            prefix18 = cur_str[:18]
            p_kr18 = std2kr[[ord(c) - ord('A') for c in prefix18]]
            full_pt_kr = (D + (W0_int @ p_kr18)) % 26
            full_pt_std = k2std[full_pt_kr]
            
            sc = quad[full_pt_std[:-3], full_pt_std[1:-2], full_pt_std[2:-1], full_pt_std[3:]].sum() / 150.0
            if sc > -6.0:
                pt_text = ''.join(chr(ord('A') + c) for c in full_pt_std)
                seg = word_segment(pt_text)
                print(f'>>> HIT: Score {sc:.4f} | LongCov: {seg.long_coverage:.2f} | Prefix: {prefix18} ({cur_words})')
                print(f'    PT: {pt_text[:75]}')
                print(f'        {pt_text[75:]}\n')
                hits.append((sc, prefix18, pt_text))
            continue
            
        # Expand with next word
        rem = 18 - len(cur_str)
        # Choose next words: limit length to rem + 6 so we don't overshoot wildly
        for w in vocab:
            if len(w) <= rem + 6:
                stack.append((cur_str + w, cur_words + [w]))

print(f'Evaluated {nodes_evaluated} word-graph nodes in {time.time()-t0:.2f}s. Hits: {len(hits)}')
