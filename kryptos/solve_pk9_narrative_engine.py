import json
from buttcrack.additive_crib import solve_additive_crib
from buttcrack.engine import resolve_scorer
from buttcrack.ciphers.columnar import _decode_units

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)

scorer = resolve_scorer('quadgrams', 'english')

# Comprehensive narrative phrases reflecting Dan Robinson's whitesmith story
narrative_phrases = [
    # Tools and actions in the forge
    "HETOKETHEGLOWINGMETALFROM",
    "HEPLACEDTHEMETALONTHEANVIL",
    "HEBEATTHEIRONINTOATHINROD",
    "WITHHEAVYBLOWSOFTHESHAMMER",
    "HEHAMMEREDTHEIRONINTOSHAPE",
    "HETAPEREDTHEENDOFTHEROD",
    "SOTHATITWOULDFITTHROUGH",
    "THEFIRSTHOLEOFTHEDRAWPLATE",
    "THROUGHTHEFIRSTHOLEOFTHE",
    "HETOKUPTHEPLIERSANDPULLED",
    "WITHALLHISSTRENGTHTHEWIRE",
    "HEGREASEDTHEIRONPLATETO",
    "EACHHOLEWASMALLERTHANTHE",
    "AGAINANDAGAINHEDREWTHEWIRE",
    "THROUGHEACHGRADUATEDHOLE",
    "UNTILITWASASFINEASTHREAD",
    "ASFINEASASINGLEHAIRFROM",
    "THENHETOKTHECHISELANDCUT",
    "APIECEOFEQUALLENGTHFOR",
    "HEFLATTENEDONEENDONTHE",
    "WITHATINYPUNCHHEPIERCED",
    "THEEYEOFTHEFIRSTNEEDLE",
    "HETOKUPAFINEMETALFILE",
    "ANDSHARPENEDTHEOTHEREND",
    "TOADICATESHARPPOINTFOR",
    "HEHEATEDTHENEEDLEONCE",
    "MOREINTHEFIREANDQUENCHED",
    "ITINWATERTOHARDENTHESTEEL",
    "THENTEMPEREDITINTHEFLAME",
    "HESMILEDANDHANDEDITTOME",
    "SAYINGTHISISYOUROWNFIRST",
    "NOWTAKETHENEEDLEANDBEG",
    "TOREADTHESECRETOFTHEKNOT",
    # Alternative direct descriptions
    "THEFIRSTLESSONWASDRAWING",
    "THEFIRSTSTEPISTODRAWTHE",
    "TODRAWTHEWIRETHROUGHTHE",
    "FIRSTYOUHEATTHEIRONUNTIL",
    "FIRSTHEATTHESTEELUNTIL",
    "THEWHITEHOTCOALSSHONE",
    "INTHEGLOWOFTHEHEARTHHE",
    "HESHOWEDMEHOWTOPOURTHE",
    "THECRUCIBLEWASPLACEDIN",
    "THEMOLTENMETALBEGANTO",
    "AFTERMANYHOURSOFLABOR",
    "THESECRETOFTHEWHITESMITH",
    "THEWHITESMITHEXPLAINED",
    "HEHANDEDMETHEIRONDRAW",
    "HEPLACEDINMYHANDSATINY",
    "ANEEDLESOFINEITCOULD",
    "FINEENOUGHTOREADANYKNOT",
    "TOREADANYKNOTINTHEWORLD",
    "TOTRACETHELETTERSONTHE",
    "INSCRIBEDUPONITSTHREAD",
    "THEREISNOWAYTOREADTHE",
    "WITHOUTANEEDLEOFYOUR",
    "TAKETHEPLIERSINYOURHAND",
    "PULLTHEWIRETHROUGHTHE",
    "HOLEBYHOLEUNTILITIS",
    "THINNERTHANASTRANDOF",
    "THENTAKETHEHAMMERAND",
    "BEATTHEENDFLATUPONTHE",
    "PIERCETHEEYEWITHCARESO",
    "THATITDOESNOTSPLITTHE",
    "TEMPERITINTHESMOKEAND"
]

print(f"Narrative engine loaded with {len(narrative_phrases)} phrases.")
print("Testing across both raw C and stream M under clock sets [4, 5, 7], [3, 5, 7], and [4, 5, 6, 7]...")

clock_sets = [
    ([4, 5, 7], 14),
    ([3, 5, 7], 13),
    ([4, 5, 6, 7], 18),
]

targets = [("raw C", pk9), ("stream M", M)]

best_sc = -999.0
best_hit = ""

for target_name, text in targets:
    for clocks, min_len in clock_sets:
        for phrase in narrative_phrases:
            L = len(phrase)
            if L < min_len:
                continue
            for pos in range(len(text) - L + 1):
                for alph in ['KRYPTOS', 'STANDARD']:
                    res = solve_additive_crib(text, clocks, [(pos, phrase)], alphabet=alph)
                    if res['consistent']:
                        det = len(res['determined_positions'])
                        if det >= 140:
                            pt = res['plaintext']
                            sc = scorer.average(pt)
                            if sc > -6.5:
                                print(f"CANDIDATE HIT ({target_name}, {clocks}): sc={sc:.3f} | {phrase} at {pos} ({alph})")
                                print(f"  PT: {pt}")
                            if sc > best_sc:
                                best_sc = sc
                                best_hit = f"{target_name} | {clocks} | {phrase} at {pos} ({alph}) | sc={sc:.3f}"
                                print(f"New best: {best_hit}")
                                print(f"  PT: {pt[:65]}...")

print(f"\nSweep complete. Best overall: {best_hit}")
