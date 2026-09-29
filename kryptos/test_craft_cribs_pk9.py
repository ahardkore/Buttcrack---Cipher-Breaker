import json
from buttcrack.additive_crib import solve_additive_crib
from buttcrack.engine import resolve_scorer

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
scorer = resolve_scorer('quadgrams', 'english')

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

print(f"Testing {len(craft_cribs)} craft cribs across PK9 under [4, 5, 7]...")
best_sc = -999.0
best_info = ""

for crib in craft_cribs:
    L = len(crib)
    for pos in range(len(pk9) - L + 1):
        for alph in ['KRYPTOS', 'STANDARD']:
            res = solve_additive_crib(pk9, [4, 5, 7], [(pos, crib)], alphabet=alph)
            if res['consistent']:
                det_cnt = len(res['determined_positions'])
                if det_cnt >= 140:
                    pt = res['plaintext']
                    sc = scorer.average(pt)
                    if sc > best_sc:
                        best_sc = sc
                        best_info = f"crib={crib} pos={pos} alph={alph} sc={sc:.3f}"
                        print(f"New best: {best_info}")
                        print(f"  PT: {pt[:70]}...")

print(f"\nSearch complete. Best score: {best_sc:.3f} ({best_info})")
