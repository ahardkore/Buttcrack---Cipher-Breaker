#!/usr/bin/env python3
"""TESTING HISTORICAL ESPIONAGE CIPHER WORDS, CRYPTONYMS, AND NAMES
Tests:
1. George Washington's Culper Spy Ring (names, locations, code words).
2. CIA Cryptonyms (KUBARK, MKULTRA, TPAJAX, etc.).
3. Historical War / Intelligence keywords (Venona, Confederate, OSS).
4. Ed Scheidt / CIA Cryptographic Center terminology.
5. Cold War Berlin espionage operations (Bridge of Spies, Teufelsberg, etc.).
"""

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"

ANCHORS = {
    22: "E", 23: "A", 24: "S", 25: "T",
    26: "N", 27: "O", 28: "R", 29: "T", 30: "H", 31: "E", 32: "A", 33: "S", 34: "T",
    64: "B", 65: "E", 66: "R", 67: "L", 68: "I", 69: "N",
    70: "C", 71: "L", 72: "O", 73: "C", 74: "K"
}

historical_cipher_words = [
    # Culper Spy Ring
    "CULPER", "CULPERRING", "SAMUELCULPER", "TALLMADGE", "BENJAMINTALLMADGE",
    "WOODHULL", "ABRAHAMWOODHULL", "TOWNSEND", "ROBERTTOWNSEND", "AUSTINROE",
    "CALEBBREWSTER", "BREWSTER", "SETAUKET", "JAMESRIVINGTON", "RIVINGTON",
    "AGENTSEVENONEONE", "AGENTSEVENTWOTWO", "SEVENONEONE", "SEVENTWOTWO",
    "SYMPATHETICSTAIN", "WHITEINK", "CODEBOOK", "SEVENSIXTHREE",

    # CIA Cryptonyms
    "KUBARK", "KUTUBE", "MKULTRA", "MKNAOMI", "MKSEARCH", "ZRRIFLE", "ZRRUBY",
    "TPAJAX", "PBSUCCESS", "PBFORTUNE", "AELADLE", "AEFOXTROT", "AMTHUG",
    "QJWIN", "LCFLAG", "KUCAGE", "KUDOVE",

    # OSS & Early American Intelligence
    "OSS", "OFFICEOFSTRATEGICSERVICES", "WILDMAN", "WILDMASS", "WILDDONOVAN",
    "WILLIAMDONOVAN", "INTREPID", "WILLIAMSTEPHENSON", "NATHANHALE",

    # Cold War Berlin & Spy Exchange
    "TEUFELSBERG", "GLIENICKE", "BRIDGEOFSPIES", "MARKUSWOLF", "MISHA",
    "CHECKPOINTCHARLIE", "FRIEDRICHSTRASSE", "POTSDAMERPLATZ", "STASIMUSEUM",
    "HAUSDESLEHRERS", "RUDOLFABEL", "FRANCISGARYPOWERS", "U2INCIDENT",

    # Codebreaking & Signal Intelligence
    "VENONA", "BLETCHLEY", "ARLINGTONHALL", "BLACKCHAMBER", "HERBERTYARDLEY",
    "YARDLEY", "FRIEDMAN", "WILLIAMFRIEDMAN", "ELIZABETHFRIEDMAN",

    # Sanborn / Scheidt Project Names
    "EDWARDSCHEIDT", "SCHEIDT", "JIMSANBORN", "HERBERTJAMES", "KRYPTOS",
    "CENTRALINTELLIGENCE", "LANGLEYVIRGINIA", "FAIRFAXCOUNTY", "MCLEAN"
]

print("=" * 80)
print("TESTING HISTORICAL ESPIONAGE CIPHER WORDS & NAMES AS KEYS (K4)")
print("=" * 80)
print(f"Total candidate keywords tested: {len(historical_cipher_words)}")

modes = ["std_vig", "kry_vig", "std_beau", "kry_beau", "std_var", "kry_var"]

def decrypt(ct, key, mode):
    pt = []
    alpha = STD if "std" in mode else KRY
    for i, c in enumerate(ct):
        k = key[i % len(key)]
        if "vig" in mode:
            p = alpha[(alpha.index(c) - alpha.index(k)) % 26]
        elif "beau" in mode:
            p = alpha[(alpha.index(k) - alpha.index(c)) % 26]
        elif "var" in mode:
            p = alpha[(alpha.index(c) + alpha.index(k)) % 26]
        pt.append(p)
    return "".join(pt)

hits = []
for kw in historical_cipher_words:
    clean_kw = "".join(c for c in kw.upper() if c in STD)
    if not clean_kw: continue
    for m in modes:
        dec = decrypt(K4_CT, clean_kw, m)
        matches = sum(dec[pos - 1] == exp for pos, exp in ANCHORS.items())
        if matches >= 3:
            hits.append((matches, clean_kw, m, dec[:35]))

hits.sort(reverse=True)
print(f"\nTop results against the 24 confirmed anchors (out of {len(historical_cipher_words) * len(modes)} trials):")
for matches, kw, m, sample in hits[:25]:
    print(f"  Matches: {matches:2d}/24 | Key: {kw:<24} | Mode: {m:<10} | Sample: {sample}...")

if not hits or hits[0][0] < 24:
    print("\nCONCLUSION: No historical intelligence keyword or Culper Ring name unlocks")
    print("the 24 confirmed anchors under polyalphabetic substitution.")
