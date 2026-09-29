import sys
import random
from buttcrack.engine import resolve_scorer
from buttcrack.ciphers.columnar import _decode_units

with open('pk_all_ciphertexts.json') as f:
    import json
    cts = json.load(f)

pk9 = cts['PK9']
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)
scorer = resolve_scorer('quadgrams', 'english')
ALPH = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'

def make_keystream(components):
    # components: list of lists of ints
    L = 144
    ks = []
    for i in range(L):
        s = sum(comp[i % len(comp)] for comp in components) % 26
        ks.append(s)
    return ks

def decrypt_with_ks(ct, ks):
    return ''.join(ALPH[(ALPH.index(c) - k) % 26] for c, k in zip(ct, ks))

def hillclimb_sumclock(ct, periods, n_restarts=50):
    best_overall_score = -999.0
    best_overall_components = None
    
    for restart in range(n_restarts):
        # random init
        comps = [[random.randint(0, 25) for _ in range(p)] for p in periods]
        cur_ks = make_keystream(comps)
        cur_sc = scorer.average(decrypt_with_ks(ct, cur_ks))
        
        improved = True
        step = 0
        while improved and step < 500:
            step += 1
            improved = False
            # try perturbing each component coordinate
            for c_idx, comp in enumerate(comps):
                for pos in range(len(comp)):
                    orig_val = comp[pos]
                    best_val = orig_val
                    best_cand_sc = cur_sc
                    for v in range(26):
                        if v == orig_val: continue
                        comp[pos] = v
                        cand_ks = make_keystream(comps)
                        sc = scorer.average(decrypt_with_ks(ct, cand_ks))
                        if sc > best_cand_sc:
                            best_cand_sc = sc
                            best_val = v
                    if best_cand_sc > cur_sc:
                        comp[pos] = best_val
                        cur_sc = best_cand_sc
                        improved = True
                    else:
                        comp[pos] = orig_val
                        
        if cur_sc > best_overall_score:
            best_overall_score = cur_sc
            best_overall_components = [[x for x in comp] for comp in comps]
            cand_ks = make_keystream(best_overall_components)
            pt = decrypt_with_ks(ct, cand_ks)
            print(f"[{periods}] Restart {restart:2d}: score = {best_overall_score:.3f}")
            comp_strs = ["".join(ALPH[x] for x in c) for c in best_overall_components]
            print(f"  Comps: {' + '.join(comp_strs)}")
            print(f"  PT: {pt[:70]}...")
            if best_overall_score > -5.2:
                print("!!! EXCELLENT PLAINTEXT FOUND !!!")
                print(f"FULL PT: {pt}")
                return best_overall_score, best_overall_components, pt
                
    return best_overall_score, best_overall_components, decrypt_with_ks(ct, make_keystream(best_overall_components))

print("=== HILL CLIMBING ON STREAM M ===")
for p_tuple in [(3, 7), (4, 7), (5, 7), (2, 7), (4, 5, 7)]:
    print(f"\n--- Testing periods {p_tuple} on M ---")
    hillclimb_sumclock(M, p_tuple, n_restarts=30)

print("\n=== HILL CLIMBING ON RAW C ===")
for p_tuple in [(4, 7), (5, 7), (3, 7), (4, 5, 7)]:
    print(f"\n--- Testing periods {p_tuple} on raw C ---")
    hillclimb_sumclock(pk9, p_tuple, n_restarts=30)
