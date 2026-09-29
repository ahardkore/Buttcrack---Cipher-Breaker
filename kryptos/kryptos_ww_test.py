#!/usr/bin/env python3
"""Does the 'WW' clue (William Webster) help crack K4?
   1) Webster-related words as tableau-Vigenere keys on K4.
   2) Crib-drag: WEBSTER / WILLIAM / WW placed at every position of the K4
      plaintext, checked for consistency with the anchor-derived keystream
      under the only surviving periods (27, 28, 29) - filling key gaps and
      decrypting when possible."""

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
         "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCHORS = {**{22+i: c for i, c in enumerate("EAST")},
           **{26+i: c for i, c in enumerate("NORTHEAST")},
           **{64+i: c for i, c in enumerate("BERLIN")},
           **{70+i: c for i, c in enumerate("CLOCK")}}

def vig_dec(ct, key, alpha=KRY):
    out, ki = [], 0
    for c in ct:
        if not c.isalpha():
            out.append(c); continue
        out.append(alpha[(alpha.index(c) - alpha.index(key[ki % len(key)])) % 26])
        ki += 1
    return "".join(out)

print("=" * 72)
print("1) Webster-related candidate keys on K4 (sculpture tableau Vigenere)")
print("=" * 72)
for key in ["WW", "WEBSTER", "WILLIAM", "WILLIAMWEBSTER", "WILLIAMHWEBSTER",
            "ONLYWW", "WWEBSTER", "DIRECTORWEBSTER", "LANGLEY"]:
    print(f"  key {key:<16} -> {vig_dec(K4_CT, key)[:40]}...")

print()
print("=" * 72)
print("2) Crib-drag WEBSTER/WILLIAM/WW under the surviving periods")
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

BIGRAMS = list(set(("TH HE IN ER AN RE ON AT ND ST ES EN OF TE ED OR TI HI "
                    "AS TO AL AR BE EA EE HA IS IT LE ME NG NT OU RA SE VE WA").split()))

def score(t):
    t = "".join(ch for ch in t if ch.isalpha())
    bg = [t[i:i+2] for i in range(len(t) - 1)]
    return sum(b in BIGRAMS for b in bg) / len(bg) if bg else 0

for conv in ("std", "tableau"):
    shifts = anchor_shifts(conv)
    print(f"\n--- convention: {conv} ---")
    for L in (27, 28, 29):
        known = {}
        for p, sh in shifts.items():
            r = p % L
            if r in known:
                assert known[r] == sh
            known[r] = sh
        missing = sorted(r for r in range(L) if r not in known)
        print(f"period {L}: {len(missing)} unknown key residues {missing}")
        for crib in ("WEBSTER", "WILLIAM", "WILLIAMWEBSTER", "WW",
                     "ONLYWW", "WILLIAMHWEBSTER"):
            hits = []
            for start in range(1, 98 - len(crib) + 1):
                cand = dict(known)
                ok = True
                for i, ch in enumerate(crib):
                    p = start + i
                    if conv == "std":
                        sh = (ord(K4_CT[p-1]) - ord(ch)) % 26
                    else:
                        sh = (KRY.index(K4_CT[p-1]) - KRY.index(ch)) % 26
                    r = p % L
                    if r in cand:
                        if cand[r] != sh:
                            ok = False; break
                    else:
                        cand[r] = sh
                if ok:
                    hits.append((start, len(cand)))
            if hits:
                full = [(s, cov) for s, cov in hits if cov == L]
                print(f"  crib {crib:<16}: {len(hits)} consistent placements "
                      f"({hits[0][0]}..{hits[-1][0]}), {len(full)} fill the full key")
                for s, _ in full[:3]:
                    keymap = {}
                    for i, ch in enumerate(crib):
                        p = s + i
                        sh = ((ord(K4_CT[p-1]) - ord(ch)) if conv == "std"
                              else (KRY.index(K4_CT[p-1]) - KRY.index(ch))) % 26
                        keymap[p % L] = sh
                    for r, sh in shifts.items():
                        keymap[r % L] = sh
                    dec = []
                    for i, c in enumerate(K4_CT):
                        r = (i + 1) % L
                        sh = keymap.get(r)
                        if sh is None:
                            dec.append(".")
                        elif conv == "std":
                            dec.append(chr((ord(c) - 65 - sh) % 26 + 65))
                        else:
                            dec.append(KRY[(KRY.index(c) - sh) % 26])
                    dec = "".join(dec)
                    print(f"     placement {s:>2}: {dec}  (score {score(dec):.3f})")
            else:
                print(f"  crib {crib:<16}: NO consistent placement")
print("\nDONE.")
