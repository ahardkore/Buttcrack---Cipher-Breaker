#!/usr/bin/env python3
"""Exhaustive test of every letter A-Z as the missing K2 ciphertext letter.

Sanborn (April 2006): one ciphertext letter was omitted from K2, turning the
intended ending '...WEST X LAYER TWO' into the desynced '...WESTIDBYROWS'.
Here we try ALL 26 letters at ALL possible positions and keep only insertions
whose decryption matches the corrected plaintext exactly.
"""

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

def vig_dec(ct, key, alpha=ALPH):
    out, ki = [], 0
    for c in ct:
        if not c.isalpha():
            out.append(c)
            continue
        shift = alpha.index(key[ki % len(key)])
        out.append(alpha[(alpha.index(c) - shift) % 26])
        ki += 1
    return "".join(out)

K2_CT = ("VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKK?DQMCPFQZDQMMIAGPFXHQRLG"
         "TIMVMZJANQLVKQEDAGDVFRPJUNGEUNAQZGZLECGYUXUEENJTBJLBQCRTBJDFHRR"
         "YIZETKZEMVDUFKSJHKFWHKUWQLSZFTIHHDDDUVH?DWKBFUFPWNTDFIYCUQZEREE"
         "VLDKFEZMOQQJLTTUGSYQPFEUNLAVIDXFLGGTEZ?FKZBSFDQVGOGIPUFXHHDRKFF"
         "HQNTGPUAECNUVPDJMQCLQUMUNEDFQELZZVRRGKFFVOEEXBDMVPNFQXEZLGREDNQ"
         "FMPNZGLFLPMRJQYALMGNUVPDXVKPDQUMEBEDMHDAFMJGZNUPLGEWJLLAETG")
EXPECTED = ("ITWASTOTALLYINVISIBLEHOWSTHATPOSSIBLE?THEYUSEDTHEEARTHSMAGNETICFIELDX"
            "THEINFORMATIONWASGATHEREDANDTRANSMITTEDUNDERGRUUNDTOANUNKNOWNLOCATIONX"
            "DOESLANGLEYKNOWABOUTTHIS?THEYSHOULDITSBURIEDOUTTHERESOMEWHEREX"
            "WHOKNOWSTHEEXACTLOCATION?ONLYWWTHISWASHISLASTMESSAGEX"
            "THIRTYEIGHTDEGREESFIFTYSEVENMINUTESSIXPOINTFIVESECONDSNORTH"
            "SEVENTYSEVENDEGREESEIGHTMINUTESFORTYFOURSECONDSWESTXLAYERTWO")
exp_clean = EXPECTED.replace("?", "")
KEY = "ABSCISSA"

# ---- locate the desync point -------------------------------------------
dec0 = vig_dec(K2_CT, KEY)
dec_clean = dec0.replace("?", "")
common = 0
while common < len(dec_clean) and dec_clean[common] == exp_clean[common]:
    common += 1
print(f"sculpture decrypts correctly for the first {common} letters,")
print(f"then '{dec_clean[common:common+9]}' instead of '{exp_clean[common:common+9]}'")

# gap = right after the `common`-th ciphertext LETTER (1-based letter count)
gap = None
cnt = 0
for idx, ch in enumerate(K2_CT):
    if ch.isalpha():
        cnt += 1
        if cnt == common:
            gap = idx + 1          # insertion index in the full string
            break
print(f"-> missing letter belongs after ciphertext letter #{common} "
      f"(string index {gap}, between '...{K2_CT[gap-4:gap]}' and '{K2_CT[gap:gap+4]}...')\n")

# ---- TEST 1: all 26 letters at the known gap ---------------------------
print("TEST 1 - every letter A-Z inserted at the gap:")
print("letter  decrypted tail (positions ~354-370)        verdict")
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    cand = K2_CT[:gap] + ch + K2_CT[gap:]
    d = vig_dec(cand, KEY).replace("?", "")
    ok = d == exp_clean
    print(f"  {ch}     ...{d[common-8:common+10]:<38} {'<== FULL RESTORATION' if ok else ''}")

# ---- TEST 2: blind search - every position x every letter --------------
print("\nTEST 2 - BLIND search: 26 letters x every insertion position "
      f"({len(K2_CT)+1} slots = {(len(K2_CT)+1)*26} trials)")
hits = []
for p in range(len(K2_CT) + 1):
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        cand = K2_CT[:p] + ch + K2_CT[p:]
        if vig_dec(cand, KEY).replace("?", "") == exp_clean:
            hits.append((p, ch))
print("exact full-match hits:", hits)

# ---- what MUST the missing letter be? (independent derivation) ----------
kidx = common % len(KEY)                 # key letters consumed so far
k = KEY[kidx]
need = ALPH[(ALPH.index("X") + ALPH.index(k)) % 26]
print(f"\nIndependent derivation: plaintext char #{common+1} is 'X', key letter "
      f"#{common+1} is '{k}' -> missing ciphertext letter MUST be '{need}'.")

# ---- implication for the Q-U-A error-letter theory ----------------------
print("\nError-theory check: missing letter =", need)
print("QUA + S -> 'QUAS'? completes QUAGMIRE?", need == "G",
      "| completes AQUA/EQUA?", need == "E")
