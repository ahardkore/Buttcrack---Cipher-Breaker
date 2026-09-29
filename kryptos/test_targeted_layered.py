import json
import time
from buttcrack.engine import resolve_scorer
from buttcrack.layered import _brute_order, _chi_seed, alphabet_header, _recover_shifts, _fast_quad_table
from buttcrack.words import long_word_coverage

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']

scorer = resolve_scorer('quadgrams', 'english')
table = _fast_quad_table(scorer)
header = alphabet_header('KRYPTOS')

print(f"Testing layered cracking on PK9 (len {len(pk9)}):")

for period in [7, 14, 28]:
    for width in [6, 7, 8]:
        t0 = time.time()
        sc, order, pt = _brute_order(pk9, 'KRYPTOS', period, width, workers=4, language='english')
        cov = long_word_coverage(pt)
        dt = time.time() - t0
        print(f"Period {period:2d}, Width {width}: sc={sc:.3f}, cov={cov:.3f}, order={order} in {dt:.2f}s")
        print(f"  PT: {pt[:70]}...")
        if cov > 0.35:
            print(f"!!! HIGH WORD COVERAGE FOUND !!!")
            print(f"FULL PT: {pt}")
