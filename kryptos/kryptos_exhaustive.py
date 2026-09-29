#!/usr/bin/env python3
"""EXHAUSTIVE K4 ATTACK - every untested classical mechanism vs the 24
artist-confirmed letters (EAST/NORTHEAST/BERLIN/CLOCK).
  A. Beaufort / variant-Beaufort period search
  B. Position-dependent shifts: k(p) = linear, quadratic, cubic mod 26
  C. Keystream = any of the sculpture's own texts (cross-correlation)
  D. Pure transposition sweep (anchors must reappear literally)
  E. Gronsfeld numeric keys / Porta / misc keys
"""
import itertools
from collections import Counter

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4 = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
      "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCH = {**{22+i: c for i, c in enumerate("EAST")},
        **{26+i: c for i, c in enumerate("NORTHEAST")},
        **{64+i: c for i, c in enumerate("BERLIN")},
        **{70+i: c for i, c in enumerate("CLOCK")}}
NEED = ("NORTHEAST", "BERLIN", "CLOCK")
BIGRAMS = list(set(("TH HE IN ER AN RE ON AT ND ST ES EN OF TE ED OR TI HI "
                    "AS TO AL AR BE EA EE HA IS IT LE ME NG NT OU RA SE VE WA").split()))
def score(t):
    t = "".join(ch for ch in t if ch.isalpha())
    bg = [t[i:i+2] for i in range(len(t)-1)]
    return sum(b in BIGRAMS for b in bg)/len(bg) if bg else 0

def ks(conv, mode):
    out = {}
    for p, pl in ANCH.items():
        c = K4[p-1]
        if conv == "std":
            ci, pi = ord(c)-65, ord(pl)-65
        else:
            ci, pi = KRY.index(c), KRY.index(pl)
        out[p] = (ci-pi) % 26 if mode == "vig" else (ci+pi) % 26
    return out

def periods(kmap):
    ok = []
    for L in range(1, 50):
        seen, good = {}, True
        for p, v in kmap.items():
            r = p % L
            if r in seen and seen[r] != v: good = False; break
            seen[r] = v
        if good: ok.append((L, len(seen)))
    return ok

print("="*72); print("A. BEAUFORT (C=K-P) and VARIANT (C=P-K) period search"); print("="*72)
for conv in ("std", "tableau"):
    for mode in ("beaufort",):
        k = ks(conv, mode)                      # K = C + P
        print(f"  [{conv}] Beaufort keystream pos22-34:",
              "".join(chr(65+k[p]) for p in range(22, 35)),
              "| consistent periods:", [L for L, _ in periods(k) if L <= 48][:12])
    kv = {p: (-v) % 26 for p, v in ks(conv, "vig").items()}   # K = P - C
    print(f"  [{conv}] variant-Beaufort consistent periods:",
          [L for L, _ in periods(kv) if L <= 48][:12])

print(); print("="*72); print("B. POSITION-DEPENDENT SHIFTS k(p) mod 26 fit to all 24 anchors")
print("="*72)
for conv in ("std", "tableau"):
    k = ks(conv, "vig")
    hits = []
    for a in range(26):
        for b in range(26):
            if all((a*p+b) % 26 == k[p] for p in k): hits.append(("lin", a, b))
    for a in range(26):
        for b in range(26):
            for c0 in range(26):
                if all((a*p*p+b*p+c0) % 26 == k[p] for p in k):
                    hits.append(("quad", a, b, c0))
    print(f"  [{conv}] linear/quadratic fits:", hits if hits else "NONE")
k = ks("std", "vig")
cub = []
for a in range(26):
    for b in range(26):
        for c0 in range(26):
            for d0 in range(26):
                if all((a*p**3+b*p*p+c0*p+d0) % 26 == k[p] for p in k):
                    cub.append((a, b, c0, d0))
print(f"  [std] cubic fits:", cub if cub else "NONE")

print(); print("="*72); print("C. KEYSTREAM = SCULPTURE TEXT (correlation at all offsets)")
print("="*72)
K1P = ("BETWEENSUBTLESHADINGANDTHEABSENCEOFLIGHTLIESTHENUANCEOFIQLUSION")
K2P = ("ITWASTOTALLYINVISIBLEHOWSTHATPOSSIBLETHEYUSEDTHEEARTHSMAGNETICFIELDX"
       "THEINFORMATIONWASGATHEREDANDTRANSMITTEDUNDERGRUUNDTOANUNKNOWNLOCATIONX"
       "DOESLANGLEYKNOWABOUTTHISTHEYSHOULDITSBURIEDOUTTHERESOMEWHEREX"
       "WHOKNOWSTHEEXACTLOCATIONONLYWWTHISWASHISLASTMESSAGEX"
       "THIRTYEIGHTDEGREESFIFTYSEVENMINUTESSIXPOINTFIVESECONDSNORTH"
       "SEVENTYSEVENDEGREESEIGHTMINUTESFORTYFOURSECONDSWESTXLAYERTWO")
K3P = ("SLOWLYDESPARATLYSLOWLYTHEREMAINSOFPASSAGEDEBRISTHATENCUMBEREDTHE"
       "LOWERPARTOFTHEDOORWAYWASREMOVEDWITHTREMBLINGHANDSIMADEATINYBREACH"
       "INTHEUPPERLEFTHANDCORNERANDTHENWIDENINGTHEHOLEALITTLEIINSERTEDTHE"
       "CANDLEANDPEEREDINTHEHOTAIRESCAPINGFROMTHECHAMBERCAUSEDTHEFLAMETO"
       "FLICKERBUTPRESENTLYDETAILSOFTHEROOMWITHINEMERGEDFROMTHEMISTX"
       "CANYOUSEEANYTHINGQ")
K1C = "EMUFPHZLRFAXYUSDJKZLDKRNSHGNFIVJYQTQUXQBQVYUVLLTREVJYQTMKYRDMFD"
K2C = ("VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKKDQMCPFQZDQMMIAGPFXHQRLG"
       "TIMVMZJANQLVKQEDAGDVFRPJUNGEUNAQZGZLECGYUXUEENJTBJLBQCRTBJDFHRR"
       "YIZETKZEMVDUFKSJHKFWHKUWQLSZFTIHHDDDUVHDWKBFUFPWNTDFIYCUQZEREE"
       "VLDKFEZMOQQJLTTUGSYQPFEUNLAVIDXFLGGTEZFKZBSFDQVGOGIPUFXHHDRKFF"
       "HQNTGPUAECNUVPDJMQCLQUMUNEDFQELZZVRRGKFFVOEEXBDMVPNFQXEZLGREDNQ"
       "FMPNZGLFLPMRJQYALMGNUVPDXVKPDQUMEBEDMHDAFMJGZNUPLGEWJLLAETG")
K3C = ("ENDYAHROHNLSRHEOCPTEOIBIDYSHNAIACHTNREYULDSLLSLLNOHSNOSMRWXMNE"
       "TPRNGATIHNRARPESLNNELEBLPIIACAEWMTWNDITEENRAHCTENEUDRETNHAEOE"
       "TFOLSEDTIWENHAEIOYTEYQHEENCTAYCREIFTBRSPAMHHEWENATAMATEGYEERLB"
       "TEEFOASFIOTUETUAEOTOARMAEERTNRTIBSEDDNIAAHTTMSTEWPIEROAGRIEWFEB"
       "AECTDDHILCEIHSITEGOEAOSDDRYDLORITRKLMLEHAGTDHARDPNEOHMGFMFEUHE"
       "ECDMRIPFEIMEHNLSSTTRTVDOHW")
TABLEAU = "".join(KRY[i:]+KRY[:i] for i in range(26))
MORSE = ("VIRTUALLYINVISIBLESHADOWFORCESLUCIDMEMORYDIGETALINTERPRETATIT"
         "TISYOURPOSITIONSOSRQ")
KEYS = "PALIMPSESTABSCISSAKRYPTOSWELTZEITUHRBERLINCLOCKEASTNORTHEAST"
STREAMS = [("K1-plaintext", K1P), ("K2-plaintext", K2P), ("K3-plaintext", K3P),
           ("K1-ciphertext", K1C), ("K2-ciphertext", K2C), ("K3-ciphertext", K3C),
           ("K4-ciphertext", K4), ("tableau-676", TABLEAU), ("morse-K0", MORSE),
           ("keyword-chain", KEYS*5)]
for conv in ("std", "tableau"):
    k = ks(conv, "vig")
    kb = {p: (-v) % 26 for p, v in k.items()}
    print(f"\n[{conv}] scanning offsets of every stream...")
    found_any = False
    for name, S in STREAMS:
        for label, kk in (("vig", k), ("beaufort", kb)):
            for t in range(0, max(1, len(S)-96)):
                m = sum(1 for p, v in kk.items()
                        if t+p-1 < len(S) and ord(S[t+p-1])-65 == v)
                if m >= 22:
                    found_any = True
                    print(f"  HIT {name} offset={t} mode={label}: {m}/24 match")
    if not found_any:
        print("  no stream/offset reaches even 22/24")

print(); print("="*72); print("D. PURE TRANSPOSITION SWEEP (anchor words must reappear)")
print("="*72)
cand = {}
def add(name, text):
    if all(w in text for w in NEED):
        cand[name] = text
        print(f"  *** {name} contains ALL anchors: {text}")

add("identity", K4)
add("reverse", K4[::-1])
for r in range(1, 97):
    t = K4[r:]+K4[:r]
    if all(w in t for w in NEED):
        cand[f"rotation{r}"] = t
        print(f"  *** rotation {r}: {t}")

for d in range(2, 49):                      # rail fence decrypt
    fence = [[] for _ in range(d)]
    idx, dn = 0, 1
    for i in range(97):
        fence[idx].append(i); 
        if idx == 0: dn = 1
        elif idx == d-1: dn = -1
        idx += dn
    order = [i for row in fence for i in row]
    dec = [None]*97
    for out_pos, src in enumerate(order): dec[src] = K4[out_pos]
    add(f"railfence-d{d}", "".join(dec))
    enc = "".join(K4[i] for i in order)     # other direction
    add(f"railfence-d{d}-enc", enc)

for k in range(2, 97):                      # decimation
    for s in range(97):
        t = "".join(K4[(s+i*k) % 97] for i in range(97))
        if all(w in t for w in NEED):
            cand[f"decim{k},{s}"] = t; print(f"  *** decimation k={k} s={s}: {t}")

for c in range(2, 13):                      # chunk swaps/reversals
    size = 97//c
    chunks = [K4[i*size:(i+1)*size] for i in range(c)] + [K4[c*size:]]
    add(f"chunks-rev-{c}", "".join(chunks[::-1]))
    add(f"chunks-within-{c}", "".join(ch[::-1] for ch in chunks))

for w in range(4, 41):                      # incomplete columnar, natural
    rows = [K4[i:i+w] for i in range(0, 97, w)]
    h = len(rows)
    col_read = "".join("".join(r[j] for r in rows if j < len(r)) for j in range(w))
    add(f"col-nat-w{w}", col_read)
    row_of_cols = "".join("".join(K4[j::w] if False else "" for j in range(w)))
    # write by columns into width w, read rows:
    h2 = (97+w-1)//w
    grid = []
    it = iter(K4)
    cols = []
    for j in range(w):
        col = []
        for i in range(h2):
            try: col.append(next(it))
            except StopIteration: break
        cols.append(col)
    add(f"writecols-w{w}", "".join("".join(cols[j][i] if i < len(cols[j]) else ""
                                        for j in range(w)) for i in range(h2)))

LINES = ["OBKR", "UOXOGHULBSOLIFBBWFLRVQQPRNGKSSO",
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYP", "VTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"]
for rows in (LINES, LINES[1:]):             # engraved layout columns
    for down in (True, False):
        rr = rows if down else rows[::-1]
        colt = "".join("".join(r[j] for r in rr if j < len(r))
                       for j in range(max(map(len, rr))))
        add(f"engraved-cols{'-up' if not down else ''}-{'with' if rows is LINES else 'no'}OBKR", colt)

best = sorted(((score(t), n) for n, t in cand.items()) if cand else [(0, "none")],
              reverse=True)[:5]
print("anchor-containing candidates:", len(cand))
# also report the best English-ish outputs across simple ops even w/o anchors
pool = [("identity", K4), ("reverse", K4[::-1])]
pool += [(f"railfence-d{d}", None) for d in ()]
tops = []
for d in range(2, 49):
    fence = [[] for _ in range(d)]
    idx, dn = 0, 1
    for i in range(97):
        fence[idx].append(i)
        if idx == 0: dn = 1
        elif idx == d-1: dn = -1
        idx += dn
    order = [i for row in fence for i in row]
    dec = [None]*97
    for out_pos, src in enumerate(order): dec[src] = K4[out_pos]
    tops.append((score("".join(dec)), f"railfence-d{d}", "".join(dec)))
tops.sort(reverse=True)
print("best bigram scores among railfence decodings (English ~0.25+):")
for sc, n, t in tops[:3]:
    print(f"  {sc:.3f} {n}: {t[:60]}...")

print(); print("="*72); print("E. GRONSFELD / PORTA / misc keys"); print("="*72)
def grons(ct, digits, alpha=KRY):
    out, ki = [], 0
    for c in ct:
        sh = int(digits[ki % len(digits)])
        out.append(alpha[(alpha.index(c)-sh) % 26]); ki += 1
    return "".join(out)
for digits, name in [("38576577844", "coords"), ("385765", "lat"), ("77844", "lon"),
                     ("1990", "year"), ("11031990", "dedication"),
                     ("19891109", "wall-fall")]:
    d = grons(K4, digits)
    print(f"  gronsfeld {name:<12} -> {d[:40]}... score {score(d):.3f}",
          "ANCHORS!" if all(w in d for w in NEED) else "")

PORTA = {"AB":"NOPQRSTUVWXYZABCDEFGHIJKLM", "CD":"OPQRSTUVWXYZNMABCDEFGHIJKL",
         "EF":"QRSTUVWXYZPONMLKJIHGFEDCBA", "GH":"RSTUVWXYZQPONMLKJIHGFEDCBA",
         "IJ":"STUVWXYZRQPONMLKJIHGFEDCBA", "KL":"UVWXYZTSRQPONMLKJIHGFEDCBA",
         "MN":"WXYZVUTSRQPONMLKJIHGFEDCBA", "OP":"XYZWVUTSRQPONMLKJIHGFEDCBA",
         "QR":"YZXWVUTSRQPONMLKJIHGFEDCBA", "ST":"ZXYWVUTSRQPONMLKJIHGFEDCBA",
         "UV":"YZXWVUTSRQPONMLKJIHGFEDCBA", "WX":"XYZWVUTSRQPONMLKJIHGFEDCBA",
         "YZ":"YZXWVUTSRQPONMLKJIHGFEDCBA"}
def porta(ct, key):
    out, ki = [], 0
    for c in ct:
        k = key[ki % len(key)]
        for pair, row in PORTA.items():
            if k in pair:
                out.append(row[STD.index(c)]); break
        ki += 1
    return "".join(out)
for key in ("KRYPTOS", "PALIMPSEST", "ABSCISSA", "WEBSTER", "BERLINCLOCK"):
    p = porta(K4, key)
    print(f"  porta {key:<12} -> {p[:40]}... score {score(p):.3f}",
          "ANCHORS!" if all(w in p for w in NEED) else "")

# sanity: could K4 be a pure transposition of the Lacy reconstruction?
RECON = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
         "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
print("\nmultiset(K4) == multiset(reconstruction)?", Counter(K4) == Counter(RECON))
print("\nDONE.")
