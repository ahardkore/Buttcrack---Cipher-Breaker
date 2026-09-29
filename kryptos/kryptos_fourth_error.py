#!/usr/bin/env python3
"""PART 1: K2 decrypted with the missing 'S' restored.
   PART 2: every letter A-Z tried as the hypothetical FOURTH intentional
   error letter:
     (a) each QUA-? word -> keyed plaintext/ciphertext alphabets for a
         Quagmire-III-style model; period-consistency vs the 24 confirmed
         K4 letters;
     (b) each QUA-? word used directly as the repeating KEY, under every
         alphabet convention (standard, KRYPTOS, keyed-word) - a full
         decryption attempt on all 97 letters."""

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

K2_CT = ("VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKK?DQMCPFQZDQMMIAGPFXHQRLG"
         "TIMVMZJANQLVKQEDAGDVFRPJUNGEUNAQZGZLECGYUXUEENJTBJLBQCRTBJDFHRR"
         "YIZETKZEMVDUFKSJHKFWHKUWQLSZFTIHHDDDUVH?DWKBFUFPWNTDFIYCUQZEREE"
         "VLDKFEZMOQQJLTTUGSYQPFEUNLAVIDXFLGGTEZ?FKZBSFDQVGOGIPUFXHHDRKFF"
         "HQNTGPUAECNUVPDJMQCLQUMUNEDFQELZZVRRGKFFVOEEXBDMVPNFQXEZLGREDNQ"
         "FMPNZGLFLPMRJQYALMGNUVPDXVKPDQUMEBEDMHDAFMJGZNUPLGEWJLLAETG")
KEY2 = "ABSCISSA"

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
         "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCHORS = {**{22+i: c for i, c in enumerate("EAST")},
           **{26+i: c for i, c in enumerate("NORTHEAST")},
           **{64+i: c for i, c in enumerate("BERLIN")},
           **{70+i: c for i, c in enumerate("CLOCK")}}
RECON = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
         "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")

def keyed(word):
    seen, out = set(), []
    for ch in word.upper():
        if ch.isalpha() and ch not in seen:
            seen.add(ch); out.append(ch)
    return "".join(out) + "".join(ch for ch in STD if ch not in seen)

def quag_dec(ct, key, p_alph, c_alph, k_alph):
    """idx_c(c) = idx_p(p) + idx_k(keyletter) mod 26. '?' passes through."""
    out, ki = [], 0
    for c in ct:
        if not c.isalpha():
            out.append(c); continue
        sh = k_alph.index(key[ki % len(key)].upper())
        out.append(p_alph[(c_alph.index(c) - sh) % 26])
        ki += 1
    return "".join(out)

BIGRAMS = list(set(("TH HE IN ER AN RE ON AT ND ST ES EN OF TE ED OR TI HI "
                    "AS TO AL AR BE EA EE HA IS IT LE ME NG NT OU RA SE VE "
                    "WA").split()))

def english_score(text):
    t = "".join(ch for ch in text if ch.isalpha())
    if len(t) < 10:
        return 0.0
    bg = [t[i:i+2] for i in range(len(t) - 1)]
    return sum(b in BIGRAMS for b in bg) / len(bg)

# ================= PART 1 ================================================
print("=" * 72)
print("PART 1 - K2 with the missing 'S' restored after ciphertext letter 361")
print("=" * 72)
restored = K2_CT[:364] + "S" + K2_CT[364:]
full = quag_dec(restored, KEY2, KRY, KRY, KRY)
print()
for i in range(0, len(full), 74):
    print(" ", full[i:i+74])
readable = full.replace("X", " X ")
print("\nreadable:")
for i in range(0, len(readable), 78):
    print(" ", readable[i:i+78])
print("\nletter count:", sum(ch.isalpha() for ch in full),
      "| ending:", full[-13:])

# ================= PART 2 ================================================
print()
print("=" * 72)
print("PART 2 - every letter A-Z as the FOURTH error letter (Q-U-A-?)")
print("=" * 72)

QUA_COMPLETIONS = {
    "A": [], "B": [], "C": [], "D": ["QUAD"], "E": ["EQUA"], "F": ["QUAFF"],
    "G": ["QUAGMIRE"], "H": ["QUAHOG"], "I": ["QUAIL"], "J": [], "K": ["QUAKE"],
    "L": ["QUALITY", "QUALM"], "M": [], "N": ["QUANTITY"], "O": [], "P": [],
    "Q": [], "R": ["QUARRY", "QUARTZ"], "S": ["QUASAR", "QUASH"],
    "T": ["QUATREFOIL"], "U": [], "V": ["QUAVER"], "W": [], "X": [],
    "Y": ["QUAY"], "Z": [],
}
WORDS = sorted({w for ws in QUA_COMPLETIONS.values() for w in ws}
               | {"AQUA", "AQUAE"})
print("\ncompletions of Q-U-A-? that form real words:")
for ch in STD:
    ws = QUA_COMPLETIONS[ch]
    print(f"  {ch}: {', '.join(ws) if ws else '-'}")
print("  (also testing anagrams/prepends: AQUA, AQUAE)")

alphabets = {"STD": STD, "KRYPTOS": KRY, **{w: keyed(w) for w in WORDS}}

# ---- (a) period-consistency over keyed-alphabet pairs -------------------
print("\n(a) Quagmire alphabet pairs consistent with the 24 anchor letters")
print("    (smallest non-contradicted period, residues covered / period):")
pair_hits = []
for pn, pa in alphabets.items():
    for cn, ca in alphabets.items():
        shifts = {p: (ca.index(K4_CT[p-1]) - pa.index(ANCHORS[p])) % 26
                  for p in ANCHORS}
        best = None
        for L in range(1, 49):
            seen, ok = {}, True
            for p, sh in shifts.items():
                r = p % L
                if r in seen and seen[r] != sh:
                    ok = False; break
                seen[r] = sh
            if ok:
                best = (L, len(seen)); break
        if best and best[0] <= 26:
            pair_hits.append((best[0], best[1], pn, cn))
if pair_hits:
    for L, cov, pn, cn in sorted(pair_hits)[:15]:
        print(f"    pt-alph={pn:<10} ct-alph={cn:<10} period={L:>2} "
              f"residues known={cov}/{L}")
else:
    print("    NONE. No keyed-alphabet pairing admits a repeating period <= 26.")
    print("    (KRYPTOS/KRYPTOS control: first non-contradicted periods are")
    print("     27, 28, 29 with only 24 residues known -> partial keys only.)")

# ---- (b) QUA-? words as the repeating KEY -------------------------------
print("\n(b) each candidate word used as the repeating key, all alphabet")
print("    conventions for plaintext / ciphertext / key indexing:")
board = []
for word in WORDS:
    for pn, pa in (("STD", STD), ("KRYPTOS", KRY), (word, keyed(word))):
        for cn, ca in (("STD", STD), ("KRYPTOS", KRY), (word, keyed(word))):
            for kn, ka in (("STD", STD), ("KRYPTOS", KRY), (word, keyed(word))):
                # anchor check first
                ok = all((ca.index(K4_CT[p-1]) - pa.index(ANCHORS[p])
                          - ka.index(word[(p-1) % len(word)])) % 26 == 0
                         for p in ANCHORS)
                if not ok:
                    continue
                dec = quag_dec(K4_CT, word, pa, ca, ka)
                board.append((english_score(dec), word, pn, cn, kn, dec))
if board:
    board.sort(reverse=True)
    print("    anchor-consistent keyword decryptions found:")
    for sc, word, pn, cn, kn, dec in board[:5]:
        print(f"    key={word:<10} P:{pn:<9} C:{cn:<9} K:{kn:<9} "
              f"score={sc:.3f}\n        {dec}")
else:
    print("    NONE of the candidate words works as the repeating key under")
    print("    any alphabet convention (all fail the 24 anchor letters).")

# ---- any English-looking output anywhere? --------------------------------
best_all = board[0] if board else None
print("\nLacy reconstruction reproduced by any config:",
      bool(board) and any(b[5] == RECON for b in board))
print("\nDONE.")
