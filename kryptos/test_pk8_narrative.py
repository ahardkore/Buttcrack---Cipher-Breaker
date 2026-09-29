from solve_pk8_with_cribs import solve_additive_crib
import json, math

with open("pk_all_ciphertexts.json") as f:
    ct8 = json.load(f)["PK8"]

quad = {}
total = 0
with open("english_quadgrams.txt") as f:
    for line in f:
        p = line.strip().split()
        if len(p) == 2:
            quad[p[0]] = float(p[1])
            total += float(p[1])
for k in quad:
    quad[k] = math.log10(quad[k] / total)

def score_text(txt):
    if "?" in txt: return -999.0
    s = sum(quad.get(txt[i:i+4], -9.5) for i in range(len(txt)-3))
    return s / (len(txt) - 3)

# Candidate beginnings for PK8 (length >= 18)
candidates = [
    # Nine days
    "FORNINEDAYSIWATCHED",
    "FORNINEDAYSITENDED",
    "FORNINEDAYSIWORKED",
    "FORNINEDAYSWEWAITED",
    "AFTERNINEDAYSINTHE",
    "AFTERNINEDAYSHEWITH",
    "ONTHETENTHDAYHETRO",
    "ONTHETENTHDAYHETOK",
    "ONTHETENTHDAYWITHL",
    "WHENTHENINEDAYSPAS",
    "WHENTHENINEDAYSHAD",
    "EACHDAYITENDEDTHEF",
    "EACHDAYIPUMPEDTHEB",
    "EACHDAYIWASALLOWED",
    "EACHDAYHEEXAMINEDT",
    "EACHDAYHECHECKEDTH",
    # Anvil / Tongs / Hammer
    "HEHELDTHESTEELWITH",
    "WITHLONGTONGSHEDRE",
    "WITHLONGTONGSHEPUL",
    "HETRANSERREDTHEIRO",
    "HEPLACEDTHEGLOWING",
    "HEPLACEDTHESTEELON",
    "HEPLACEDTHEIRONONT",
    "HELAIDTHEGLOWINGST",
    "HELAIDTHEIRONUPONT",
    "HESTRUCKTHEGLOWING",
    "HESTRUCKTHESTEELWI",
    "HEBEGANTOSTRIKETHE",
    "HEBEGANTODRAWTHEWI",
    "HEBEGANTOHAMMERTHE",
    "WITHAHEAVYHAMMERHE",
    "WITHEACHBLOWOFTHEH",
    "WITHEACHSTROKEOFTH",
    # Draw-plate / Wire / Needle
    "HEDREWTHESTEELTHRO",
    "HEDREWTHEWIRETHROU",
    "THROUGHTHEDRAWPLAT",
    "INTOTHEDRAWPLATEHE",
    "THROUGHEACHHOLEINT",
    "THROUGHEACHHOLEOFT",
    "THEIRONBECAMETHINN",
    "THEWIREBECAMETHINN",
    "UNTILTHEWIREWASFIN",
    "UNTILTHESTEELWASFI",
    "THENHEPIERCEDTHEEY",
    "THENWITHAFINECENTR",
    "WITHASMALLHAMMERHE",
    "WITHASMALLPUNCHHES",
    "HESTRUCKASMALLHOLE",
    # Tempering / Quenching
    "HEQUENCHEDTHESTEEL",
    "HEQUENCHEDITINWATE",
    "THENHEQUENCHEDTHEF",
    "HEPLUNGEDITINTOWAT",
    "HEPLUNGEDTHEGLOWIN",
    "INCOLDWATERHEQUENC",
    # First-person narrator actions
    "ITENDEDTHEBELLOWSF",
    "IPUMPEDTHEBELLOWSW",
    "IWATCHEDASHESTRUCK",
    "IWATCHEDASHEDREWTH",
    "HEHANDEDMETHEHAMME",
    "HEHANDEDMETHESTEEL",
    "HETOLDMETOSTRIKETH",
    "HETOLDMETOPUMPTHEB",
    "HEWARNEDMETOKEEPT",
    "HECOMMANDEDMETOBL",
]

print(f"Testing {len(candidates)} candidate cribs of length 18+ on PK8 at pos 0...")
best_sc = -999.0
best_cand = None

for c in candidates:
    crib18 = c[:18]
    res = solve_additive_crib(ct8, [4, 5, 6, 7], [(0, crib18)])
    if res["consistent"] and res["determined_count"] == 153:
        pt = res["plaintext"]
        sc = score_text(pt)
        if sc > -7.0:
            print(f"High score: {sc:.4f} | Crib: {crib18} | PT: {pt[:70]}")
        if sc > best_sc:
            best_sc = sc
            best_cand = (crib18, pt, sc)

print(f"Done. Best candidate: {best_cand[0] if best_cand else None} with score {best_sc:.4f}")
if best_cand:
    print(f"Plaintext preview: {best_cand[1]}")
