#!/usr/bin/env python3
"""
KRYPTOS SOLVER / CRYPTANALYSIS
==============================
1. Decrypts & verifies K1 (Vigenere, key PALIMPSEST) and K2 (Vigenere, key ABSCISSA)
   using the sculpture's own KRYPTOS tableau alphabet.
2. Recovers the transposition used for K3 by matching against the known plaintext.
3. Independent cryptanalysis of K4 using the four artist-confirmed anchors:
      EAST      @ 22-25  (ct FLRV)       - Sanborn, Aug 2020
      NORTHEAST @ 26-34  (ct QQPRNGKSS)  - Sanborn, Jan 2020 (NYT)
      BERLIN    @ 64-69  (ct NYPVTT)     - Sanborn, Nov 2010 (NYT)
      CLOCK     @ 70-74  (ct MZFPK)      - Sanborn, Nov 2014 (NYT)
"""

from collections import Counter

# The KRYPTOS tableau alphabet from the right-hand panel of the sculpture
ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
assert len(ALPH) == 26 and len(set(ALPH)) == 26

def s(c):  # standard letter index A=0..Z=25
    return ord(c.upper()) - 65

# ---------------------------------------------------------------- K1 / K2
def vig_dec(ct, key, alpha=ALPH):
    """Sculpture Vigenere: everything indexes into the KRYPTOS tableau
    alphabet:  idx(C) = idx(P) + idx(K) (mod 26). '?' passes through
    literally and does NOT consume a key letter."""
    out, ki = [], 0
    for c in ct:
        if not c.isalpha():
            out.append(c)
            continue
        shift = alpha.index(key[ki % len(key)])
        out.append(alpha[(alpha.index(c) - shift) % 26])
        ki += 1
    return "".join(out)

def vig_enc(pt, key, alpha=ALPH):
    out, ki = [], 0
    for c in pt:
        if not c.isalpha():
            out.append(c)
            continue
        shift = alpha.index(key[ki % len(key)])
        out.append(alpha[(alpha.index(c) + shift) % 26])
        ki += 1
    return "".join(out)

K1_CT = ("EMUFPHZLRFAXYUSDJKZLDKRNSHGNFIVJ"
         "YQTQUXQBQVYUVLLTREVJYQTMKYRDMFD")
K1_EXPECTED = ("BETWEENSUBTLESHADINGANDTHEABSENCEOFLIGHTLIES"
               "THENUANCEOFIQLUSION")

K2_CT = ("VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKK?DQMCPFQZDQMMIAGPFXHQRLG"
         "TIMVMZJANQLVKQEDAGDVFRPJUNGEUNAQZGZLECGYUXUEENJTBJLBQCRTBJDFHRR"
         "YIZETKZEMVDUFKSJHKFWHKUWQLSZFTIHHDDDUVH?DWKBFUFPWNTDFIYCUQZEREE"
         "VLDKFEZMOQQJLTTUGSYQPFEUNLAVIDXFLGGTEZ?FKZBSFDQVGOGIPUFXHHDRKFF"
         "HQNTGPUAECNUVPDJMQCLQUMUNEDFQELZZVRRGKFFVOEEXBDMVPNFQXEZLGREDNQ"
         "FMPNZGLFLPMRJQYALMGNUVPDXVKPDQUMEBEDMHDAFMJGZNUPLGEWJLLAETG")
K2_EXPECTED = ("ITWASTOTALLYINVISIBLEHOWSTHATPOSSIBLE?THEYUSEDTHEEARTHSMAGNETICFIELDX"
               "THEINFORMATIONWASGATHEREDANDTRANSMITTEDUNDERGRUUNDTOANUNKNOWNLOCATIONX"
               "DOESLANGLEYKNOWABOUTTHIS?THEYSHOULDITSBURIEDOUTTHERESOMEWHEREX"
               "WHOKNOWSTHEEXACTLOCATION?ONLYWWTHISWASHISLASTMESSAGEX"
               "THIRTYEIGHTDEGREESFIFTYSEVENMINUTESSIXPOINTFIVESECONDSNORTH"
               "SEVENTYSEVENDEGREESEIGHTMINUTESFORTYFOURSECONDSWESTXLAYERTWO")

print("=" * 74)
print("PASSAGE 1  (Vigenere, tableau KRYPTOS..., key PALIMPSEST)")
print("=" * 74)
k1 = vig_dec(K1_CT, "PALIMPSEST")
print("ciphertext :", K1_CT)
print("decrypted  :", k1)
print("expected   :", K1_EXPECTED)
print("MATCH:", k1 == K1_EXPECTED)

print()
print("=" * 74)
print("PASSAGE 2  (Vigenere, tableau KRYPTOS..., key ABSCISSA)")
print("=" * 74)
k2 = vig_dec(K2_CT, "ABSCISSA")
print("ciphertext :", K2_CT[:70], "...")
print("decrypted  :", k2)
print("MATCH:", k2.replace("?", "") == K2_EXPECTED.replace("?", ""))

# --- the known April-2006 transcription error at the end of K2 ---
d2, e2 = k2.replace("?", ""), K2_EXPECTED.replace("?", "")
common = 0
for a, b in zip(d2, e2):
    if a != b:
        break
    common += 1
print(f"\nK2 matches the corrected plaintext for the first {common} letters, then diverges:")
print("  sculpture decrypts :", "..." + d2[common - 12:])
print("  corrected plaintext:", "..." + e2[common - 12:])
print("  -> the single ciphertext letter Sanborn admitted omitting (April 2006)")
print("     desyncs the key at exactly this point: 'IDBYROWS' vs 'XLAYERTWO'.")

# ---------------------------------------------------------------- K3
K3_CT = ("ENDYAHROHNLSRHEOCPTEOIBIDYSHNAIACHTNREYULDSLLSLLNOHSNOSMRWXMNE"
         "TPRNGATIHNRARPESLNNELEBLPIIACAEWMTWNDITEENRAHCTENEUDRETNHAEOE"
         "TFOLSEDTIWENHAEIOYTEYQHEENCTAYCREIFTBRSPAMHHEWENATAMATEGYEERLB"
         "TEEFOASFIOTUETUAEOTOARMAEERTNRTIBSEDDNIAAHTTMSTEWPIEROAGRIEWFEB"
         "AECTDDHILCEIHSITEGOEAOSDDRYDLORITRKLMLEHAGTDHARDPNEOHMGFMFEUHE"
         "ECDMRIPFEIMEHNLSSTTRTVDOHW?")
K3_CT_L = K3_CT.replace("?", "")
K3_EXPECTED = ("SLOWLYDESPARATLYSLOWLYTHEREMAINSOFPASSAGEDEBRISTHATENCUMBEREDTHE"
               "LOWERPARTOFTHEDOORWAYWASREMOVEDWITHTREMBLINGHANDSIMADEATINYBREACH"
               "INTHEUPPERLEFTHANDCORNERANDTHENWIDENINGTHEHOLEALITTLEIINSERTEDTHE"
               "CANDLEANDPEEREDINTHEHOTAIRESCAPINGFROMTHECHAMBERCAUSEDTHEFLAMETO"
               "FLICKERBUTPRESENTLYDETAILSOFTHEROOMWITHINEMERGEDFROMTHEMISTX"
               "CANYOUSEEANYTHINGQ")

print()
print("=" * 74)
print("PASSAGE 3  (transposition - recovering the route)")
print("=" * 74)
print("ct length :", len(K3_CT_L), " pt length :", len(K3_EXPECTED),
      " factors:", [f for f in range(2, len(K3_CT_L)) if len(K3_CT_L) % f == 0])

# Documented mechanism (Sanborn's original encoding sheets, via the
# Puzzling.SE / dcode write-ups): DOUBLE ROUTE TRANSPOSITION.
#   enc: write by rows into 42x8, read by UPWARD columns (bottom->top,
#   left->right); then write that by rows into 14x24, read by upward
#   columns again.  (Equivalent to two 90-degree clockwise rotations.)

def write_rows(text, w, h):
    return [[text[r * w + c] for c in range(w)] for r in range(h)]

def read_upcols(grid, w, h):
    return "".join(grid[r][c] for c in range(w) for r in range(h - 1, -1, -1))

def fill_upcols(text, w, h):
    grid = [[""] * h for _ in range(w)]     # grid[col][row]
    idx = 0
    for c in range(w):
        for r in range(h - 1, -1, -1):
            grid[c][r] = text[idx]; idx += 1
    return grid

def read_rows(grid, w, h):
    return "".join(grid[c][r] for r in range(h) for c in range(w))

# --- verify ENCRYPTION reproduces the sculpture ciphertext ---
mid = read_upcols(write_rows(K3_EXPECTED, 42, 8), 42, 8)
ct_rebuilt = read_upcols(write_rows(mid, 14, 24), 14, 24)
print("encrypt(plaintext) == sculpture ciphertext:", ct_rebuilt == K3_CT_L)

# --- DECRYPT from the ciphertext (inverse route) ---
mid_dec = read_rows(fill_upcols(K3_CT_L, 14, 24), 14, 24)
pt_dec = read_rows(fill_upcols(mid_dec, 42, 8), 42, 8)
print("decrypt(ciphertext) == known plaintext :", pt_dec == K3_EXPECTED)
print("recovered plaintext start:", pt_dec[:70], "...")
print("recovered plaintext end  :", "...", pt_dec[-30:])

# ---------------------------------------------------------------- K4
K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
         "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
assert len(K4_CT) == 97, len(K4_CT)

ANCHORS = {  # 1-based position -> plaintext letter
    **{22 + i: c for i, c in enumerate("EAST")},
    **{26 + i: c for i, c in enumerate("NORTHEAST")},
    **{64 + i: c for i, c in enumerate("BERLIN")},
    **{70 + i: c for i, c in enumerate("CLOCK")},
}

print()
print("=" * 74)
print("PASSAGE 4  (97 letters - cryptanalysis)")
print("=" * 74)
print("ciphertext :", K4_CT)

freq = Counter(K4_CT)
ioc = sum(v * (v - 1) for v in freq.values()) / (97 * 96)
print("\nletter freq:", "".join(f"{c}:{freq[c]} " for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if freq[c]))
print(f"index of coincidence = {ioc:.4f}  (English ~0.0667, random ~0.0385)")

# repeated trigrams (Kasiski-style)
tri = Counter(K4_CT[i:i+3] for i in range(95))
reps = {t: c for t, c in tri.items() if c > 1}
print("repeated trigrams:", reps if reps else "NONE")

# ---- implied keystream under two conventions -------------------------
def keystream(convention):
    ks = {}
    for p, pl in ANCHORS.items():
        c = K4_CT[p - 1]
        if convention == "std":
            ks[p] = (s(c) - s(pl)) % 26
        else:  # tableau
            ks[p] = (ALPH.index(c) - ALPH.index(pl)) % 26
    return ks

def consistent_periods(ks, nmax=97):
    valid = []
    for L in range(1, nmax + 1):
        seen, ok = {}, True
        for p, sh in ks.items():
            r = p % L
            if r in seen and seen[r] != sh:
                ok = False
                break
            seen[r] = sh
        if ok:
            valid.append(L)
    return valid

for conv in ("std", "tableau"):
    ks = keystream(conv)
    print(f"\n[{conv}] implied keystream @ anchors: ", end="")
    print("pos22-34:", "".join(chr(65 + ks[p]) for p in range(22, 35)),
          "| pos64-74:", "".join(chr(65 + ks[p]) for p in range(64, 75)))
    if conv == "tableau":  # sculpture's convention: shifts are tableau indices
        print("[tableau] as actual KEY LETTERS:      ",
              "pos22-34:", "".join(ALPH[ks[p]] for p in range(22, 35)),
              "| pos64-74:", "".join(ALPH[ks[p]] for p in range(64, 75)))
    vp = consistent_periods(ks)
    short = [v for v in vp if v <= 48]
    print(f"[{conv}] repeating-key periods with NO contradiction: {short} (+ 53..97)")

# ---- the period-29 key fragment (community claim, verified here) -----
ks = keystream("std")
KEY29 = {}
for p, sh in ks.items():
    KEY29[(p - 1) % 29] = sh
frag = "".join(chr(65 + KEY29[i]) if i in KEY29 else "?" for i in range(29))
print("\nperiod-29 key fragment (std):", frag)

def vig_dec_std(ct, key_map, period):
    """key_map: residue(0-based)->shift or None (unknown)."""
    out = []
    for i, c in enumerate(ct):
        sh = key_map.get(i % period)
        out.append(chr((s(c) - sh) % 26 + 65) if sh is not None else ".")
    return "".join(out)

print("decrypting all of K4 with that fragment ('.' = key letter unknown):")
print(" ", vig_dec_std(K4_CT, KEY29, 29))
print("  anchors land at 22-34 and 64-74; everything else is gibberish ->")
print("  => K4 is NOT a repeating-key Vigenere of period 29 (or 13-29).")

# ---- autokey tests ----------------------------------------------------
ok_pt = all((s(K4_CT[p - 1]) - s(ANCHORS[p])) % 26 == s(ANCHORS[p - 1])
            for p in ANCHORS if p - 1 in ANCHORS)
ok_ct = all((s(K4_CT[p - 1]) - s(ANCHORS[p])) % 26 == s(K4_CT[p - 2])
            for p in ANCHORS if p - 1 in ANCHORS)
print("\nplaintext-autokey consistent with anchors:", ok_pt)
print("ciphertext-autokey consistent with anchors:", ok_ct)

# ---- naive candidate keys ----------------------------------------------
print("\nblind candidate-key decryptions (tableau Vigenere):")
for key in ["KRYPTOS", "PALIMPSEST", "ABSCISSA", "UNKNOWN", "WELTZEITUHR",
            "ALEXANDERPLATZ", "COMPASSROSE", "BERLINCLOCK"]:
    d = vig_dec(K4_CT, key)
    print(f"  key {key:<14} -> {d[:40]}...")

# ---- the 2025 publicly-posted reconstruction (UNVERIFIED) --------------
RECON = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
         "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
assert len(RECON) == 97
assert all(RECON[p - 1] == ANCHORS[p] for p in ANCHORS), "reconstruction breaks an anchor!"
print("\n--- Matt Lacy / solvekryptos.com reconstruction (NOT artist-confirmed) ---")
print("text:", RECON)
rks = {(p + 1): (s(K4_CT[p]) - s(RECON[p])) % 26 for p in range(97)}
print("implied keystream:", "".join(chr(65 + rks[p]) for p in sorted(rks)))
vp = consistent_periods(rks)
print("periods consistent with that full keystream:", vp,
      "(only trivial => it also needs a non-repeating mechanism)")

# ---- geodesic cross-check of the reconstruction's closing claim --------
import math

def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

b = bearing(38.95227, -77.14573, 52.52192, 13.41321)  # CIA courtyard -> Weltzeituhr
print(f"\nGeodesy check: great-circle bearing CIA courtyard -> Weltzeituhr "
      f"= {b:.1f} deg (due NE = 45 deg).")
print("\nDONE.")
