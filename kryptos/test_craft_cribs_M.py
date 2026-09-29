import json
from buttcrack.additive_crib import solve_additive_crib
from buttcrack.engine import resolve_scorer

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
scorer = resolve_scorer('quadgrams', 'english')

from buttcrack.ciphers.columnar import _decode_units
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)

craft_cribs = [
    "DRAWTHEWIRETHROUGH",
    "THROUGHTHEDRAWPLATE",
    "THEIRONDRAWPLATE",
    "PUNCHEDWITHHOLES",
    "GRADUATEDHOLES",
    "UNTILITBECOMESASFINE",
    "ASFINEASATHREAD",
    "CUTINTOPIECESOF",
    "EQUALLENGTHAND",
    "BEATONEENDFLAT",
    "FLATTENONEENDAND",
    "PIERCEITWITHAPUNCH",
    "PIERCETHEEYEWITH",
    "TOMAKETHEEYEOF",
    "SHARPENTHEPOINT",
    "WITHAFINEMETALFILE",
    "QUENCHITINWATER",
    "QUENCHEDINWATER",
    "TOHARDENTHESTEEL",
    "TOHARDENTHEMETAL",
    "TOTEMPERTHEMETAL",
    "HEATTHESTEELUNTIL",
    "HEATTHEIRONUNTIL",
    "WHITEHOTANDHAMMER",
    "ONTHEANVILUNTIL",
    "WITHTHETONGSHEHELD",
    "HEPLACEDTHECRUCIBLE",
    "INTOEXQUISITENEEDLES",
    "TAKETHISNEEDLEAS",
    "FORYOUROWNPRACTICE",
    "THEFIRSTNEEDLEOF",
    "MYFIRSTNEEDLEWAS",
    "AFTERTENYEARSSTUDY",
    "ATLASTICANDRAWTHE",
    "NOWTAKETHISTOOLAND",
    "THISISYOURFIRSTNEEDLE",
    "YOUHAVEMADEYOUROWN"
]

print(f"Testing {len(craft_cribs)} craft cribs across stream M under [4, 5, 7] and [7]...")
best_sc = -999.0
best_info = ""

for p_set in [[4, 5, 7], [3, 7], [7]]:
    for crib in craft_cribs:
        L = len(crib)
        for pos in range(len(M) - L + 1):
            for alph in ['KRYPTOS', 'STANDARD']:
                res = solve_additive_crib(M, p_set, [(pos, crib)], alphabet=alph)
                if res['consistent']:
                    det_cnt = len(res['determined_positions'])
                    if det_cnt >= 140:
                        pt = res['plaintext']
                        sc = scorer.average(pt)
                        if sc > best_sc:
                            best_sc = sc
                            best_info = f"periods={p_set} crib={crib} pos={pos} alph={alph} sc={sc:.3f}"
                            print(f"New best: {best_info}")
                            print(f"  PT: {pt[:70]}...")

print(f"\nSearch complete. Best score: {best_sc:.3f} ({best_info})")
