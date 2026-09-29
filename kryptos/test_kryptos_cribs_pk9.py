import json
from solve_pk8_with_cribs import solve_additive_crib, KRYPTOS_ALPHABET

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ct9 = cts["PK9"]
N = len(ct9)

# Build a comprehensive list of candidate phrases from Kryptos K1-K4 and Paradigm lore
phrases = [
    # K2
    "ITWASTOTALLYINVISIBLE", "HOWSTHATPOSSIBLE", "THEYUSEDTHEEARTHS",
    "EARTHSMAGNETICFIELD", "MAGNETICFIELD", "INFORMATIONWASGATHERED",
    "TRANSMITTEDUNDERGROUND", "UNDERGROUNDTOAN", "UNKNOWNLOCATION",
    "DOESLANGLEYKNOWABOUT", "ITSBURIEDOUTTHERE", "BURIEDOUTTHERESOMEWHERE",
    "WHOKNOWSTHEEXACTLOCATION", "ONLYWWTHISWASHISLAST", "THISWASHISLASTMESSAGE",
    "THIRTYEIGHTDEGREES", "FIFTYSEVENMINUTES", "SIXPOINTFIVESECONDS",
    "SEVENTYSEVENDEGREES", "EIGHTMINUTESFORTYFOUR", "FORTYFOURSECONDSWEST",
    "LAYERTWO", "EASTNORTHEAST",
    # K1
    "BETWEENSUBTLESHADING", "ANDTHEABSENCEOF", "ILLUSIONOFNUANCE",
    # K3
    "SLOWLYDESPARATLYSLOWLY", "REMAINDSOFPASSAGEDEBRIS", "POINTEDTOTHEHEARTH",
    # K4 clues
    "NORTHEAST", "BERLINCLOCK", "EASTNORTHEAST",
    # Pellegrin / Needle lore
    "UNAGOTANTOSOTTILEDALEGGERE", "LEGGEREEQUALUNQUENODO",
    "THELOSTARCHIVEOF", "ARCHIVEOFPELLEGRIN", "TWELVEPRIORARCHIVISTS",
    "THEWHITESMITHSNEEDLE", "EXQUISITENEEDLE", "DRAWNTHROUGHTHEDIE",
    "DRAWNTHROUGHTHEHOLE", "SMALLESTHOLEINTHEDIE", "DRAWPLATEMUSTBEUSED"
]

print(f"Testing {len(phrases)} canonical phrases against PK9 under [4, 7] clocks...")

hits = []
for p in phrases:
    # Test lengths >= 11
    if len(p) < 11:
        continue
    crib = p[:14] # use 14 chars (2 full periods of 7)
    for pos in range(N - len(crib) + 1):
        res = solve_additive_crib(ct9, [4, 7], [(pos, crib)])
        if res["consistent"] and res["determined_count"] == N:
            # Check ranks: (10, 10) means fully consistent over GF(2) and GF(13)
            hits.append((pos, crib, p, res["ranks"]))

print(f"Found {len(hits)} consistent placements:")
for pos, crib, full_p, ranks in hits:
    print(f"  pos {pos:3d} | ranks {ranks} | crib: {crib} ({full_p})")
