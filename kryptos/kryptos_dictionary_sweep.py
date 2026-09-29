#!/usr/bin/env python3
"""DICTIONARY SWEEP.
Track 1: every dictionary word containing Q-U-A (1,681 words) as
         (b) the repeating KEY and (a) keyed Quagmire alphabets,
         checked against the 24 artist-confirmed K4 letters.
Track 2: every 5-letter dictionary word (7,186 words) filling the five
         unknown key residues (17-21) of the period-29 fragment
         GCKAZMUYKLGKORNA?????BLZCDCYY, full K4 decryption + scoring."""

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
         "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCHORS = {**{22+i: c for i, c in enumerate("EAST")},
           **{26+i: c for i, c in enumerate("NORTHEAST")},
           **{64+i: c for i, c in enumerate("BERLIN")},
           **{70+i: c for i, c in enumerate("CLOCK")}}

WORDS = [w.strip().upper() for w in open("words_alpha.txt") if w.strip()]
QUA_WORDS = sorted({w for w in WORDS if len(w) >= 4 and "QUA" in w})
FIVE = sorted({w for w in WORDS if len(w) == 5})
print(f"dictionary: {len(WORDS)} words | QUA words: {len(QUA_WORDS)} | "
      f"5-letter: {len(FIVE)}")
print("common QUA words:", [w for w in QUA_WORDS if w in
      {"QUAGMIRE","QUAIL","QUAKE","QUALITY","QUALM","QUANTITY","QUARRY",
       "QUARTZ","QUASAR","QUASH","QUATREFOIL","QUAVER","QUAY","QUAFF",
       "QUAHOG","AQUA","AQUARIUM","AQUATIC","QUAINT","QUANDARY"}])

def keyed(word):
    seen, out = set(), []
    for ch in word:
        if ch not in seen:
            seen.add(ch); out.append(ch)
    return "".join(out) + "".join(ch for ch in STD if ch not in seen)

BIGRAMS = list(set(("TH HE IN ER AN RE ON AT ND ST ES EN OF TE ED OR TI HI "
                    "AS TO AL AR BE EA EE HA IS IT LE ME NG NT OU RA SE VE WA").split()))

def score(t):
    t = "".join(ch for ch in t if ch.isalpha())
    bg = [t[i:i+2] for i in range(len(t) - 1)]
    return sum(b in BIGRAMS for b in bg) / len(bg) if bg else 0

# ================= TRACK 1b: word as repeating KEY =======================
print("\n" + "=" * 72)
print("TRACK 1b - every QUA word as the repeating key (27 alphabet combos)")
print("=" * 72)
survivors_b = []
for word in QUA_WORDS:
    kw = keyed(word)
    for pn, pa in (("STD", STD), ("KRYPTOS", KRY), (word, kw)):
        pa_idx = {c: i for i, c in enumerate(pa)}
        for cn, ca in (("STD", STD), ("KRYPTOS", KRY), (word, kw)):
            ca_idx = {c: i for i, c in enumerate(ca)}
            for kn, ka in (("STD", STD), ("KRYPTOS", KRY), (word, kw)):
                ka_idx = {c: i for i, c in enumerate(ka)}
                ok = all((ca_idx[K4_CT[p-1]] - pa_idx[ANCHORS[p]]
                          - ka_idx[word[(p-1) % len(word)]]) % 26 == 0
                         for p in ANCHORS)
                if ok:
                    out, ki = [], 0
                    for c in K4_CT:
                        sh = ka_idx[word[ki % len(word)]]
                        out.append(pa[(ca_idx[c] - sh) % 26]); ki += 1
                    dec = "".join(out)
                    survivors_b.append((score(dec), word, pn, cn, kn, dec))
if survivors_b:
    survivors_b.sort(reverse=True)
    for sc, word, pn, cn, kn, dec in survivors_b[:8]:
        print(f"  SURVIVOR key={word} P:{pn} C:{cn} K:{kn} score={sc:.3f}")
        print(f"    {dec}")
else:
    print(f"  tested {len(QUA_WORDS)} words x 27 combos = "
          f"{len(QUA_WORDS)*27} configurations")
    print("  ZERO survive the 24-anchor check.")

# ================= TRACK 1a: word as keyed alphabets =====================
print("\n" + "=" * 72)
print("TRACK 1a - QUA-word keyed alphabets: smallest non-contradicted period")
print("=" * 72)
hits_a = []
for word in QUA_WORDS:
    kw = keyed(word)
    for pn, pa in (("STD", STD), ("KRYPTOS", KRY), (word, kw)):
        pa_idx = {c: i for i, c in enumerate(pa)}
        for cn, ca in (("STD", STD), ("KRYPTOS", KRY), (word, kw)):
            ca_idx = {c: i for i, c in enumerate(ca)}
            shifts = {p: (ca_idx[K4_CT[p-1]] - pa_idx[ANCHORS[p]]) % 26
                      for p in ANCHORS}
            for L in range(1, 49):
                seen, ok = {}, True
                for p, sh in shifts.items():
                    r = p % L
                    if r in seen and seen[r] != sh:
                        ok = False; break
                    seen[r] = sh
                if ok:
                    if L <= 26:
                        hits_a.append((L, len(seen), word, pn, cn))
                    break
if hits_a:
    hits_a.sort()
    print(f"  {len(hits_a)} pairings admit a period <= 26 (best 12):")
    for L, cov, word, pn, cn in hits_a[:12]:
        print(f"    period={L:>2} residues known={cov}/{L}  "
              f"pt-alph={pn if pn != word else word}  ct-alph={cn if cn != word else word}  (word={word})")
else:
    print("  ZERO QUA-word alphabet pairings admit a period <= 26.")

# ================= TRACK 2: 5-letter words into the key gap ==============
print("\n" + "=" * 72)
print("TRACK 2 - every 5-letter word fills period-29 key residues 17-21")
print("=" * 72)
def anchor_shifts(conv):
    sh = {}
    for p, pl in ANCHORS.items():
        c = K4_CT[p - 1]
        if conv == "std":
            sh[p] = (ord(c) - ord(pl)) % 26
        else:
            sh[p] = (KRY.index(c) - KRY.index(pl)) % 26
    return sh

GAP_RES = (17, 18, 19, 20, 21)
GAP_POS = [p for p in range(1, 98) if p % 29 in GAP_RES]

def decrypt_with(base_keymap, gap_shifts, conv):
    keymap = dict(base_keymap)
    for i, r in enumerate(GAP_RES):
        keymap[r] = gap_shifts[i]
    out = []
    for i, c in enumerate(K4_CT):
        sh = keymap[(i + 1) % 29]
        if conv == "std":
            out.append(chr((ord(c) - 65 - sh) % 26 + 65))
        else:
            out.append(KRY[(KRY.index(c) - sh) % 26])
    return "".join(out)

best = []
for conv in ("std", "tableau"):
    base = {p % 29: sh for p, sh in anchor_shifts(conv).items()}
    top = []
    for word in FIVE:
        if conv == "std":
            gs = [ord(ch) - 65 for ch in word]
        else:
            gs = [KRY.index(ch) for ch in word]
        dec = decrypt_with(base, gs, conv)
        sc = score(dec)
        top.append((sc, word, dec))
    top.sort(reverse=True)
    print(f"\n[{conv}] top 5 of {len(FIVE)} words:")
    for sc, word, dec in top[:5]:
        gap_txt = "".join(dec[p-1] for p in GAP_POS)
        print(f"  {word:<8} score={sc:.3f} gap->'{gap_txt}'  {dec[:40]}...")
    best.append((conv, top[0]))

print("\nnote: the 82 non-gap letters are FIXED garbage for every word")
print("(IZARNQAP... etc.), so scores cap out ~0.15 no matter the word -")
print("the gap cannot resurrect a dead mechanism.")
print("\nDONE.")
