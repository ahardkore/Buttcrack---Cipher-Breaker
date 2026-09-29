#!/usr/bin/env python3
"""Kryptos intentional-error analysis: do the misspellings point at K4?"""

K1PT = ("BETWEENSUBTLESHADINGANDTHEABSENCEOFLIGHTLIES"
        "THENUANCEOFIQLUSION")                      # as carved
K2PT = ("ITWASTOTALLYINVISIBLEHOWSTHATPOSSIBLETHEYUSEDTHEEARTHSMAGNETICFIELDX"
        "THEINFORMATIONWASGATHEREDANDTRANSMITTEDUNDERGRUUNDTOANUNKNOWNLOCATIONX"
        "DOESLANGLEYKNOWABOUTTHISTHEYSHOULDITSBURIEDOUTTHERESOMEWHEREX"
        "WHOKNOWSTHEEXACTLOCATIONONLYWWTHISWASHISLASTMESSAGEX"
        "THIRTYEIGHTDEGREESFIFTYSEVENMINUTESSIXPOINTFIVESECONDSNORTH"
        "SEVENTYSEVENDEGREESEIGHTMINUTESFORTYFOURSECONDSWESTXLAYERTWO")
K3PT = ("SLOWLYDESPARATLYSLOWLYTHEREMAINSOFPASSAGEDEBRISTHATENCUMBEREDTHE"
        "LOWERPARTOFTHEDOORWAYWASREMOVEDWITHTREMBLINGHANDSIMADEATINYBREACH"
        "INTHEUPPERLEFTHANDCORNERANDTHENWIDENINGTHEHOLEALITTLEIINSERTEDTHE"
        "CANDLEANDPEEREDINTHEHOTAIRESCAPINGFROMTHECHAMBERCAUSEDTHEFLAMETO"
        "FLICKERBUTPRESENTLYDETAILSOFTHEROOMWITHINEMERGEDFROMTHEMISTX"
        "CANYOUSEEANYTHINGQ")
K4CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
        "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCH = {}
for start, word in ((22, "EAST"), (26, "NORTHEAST"), (64, "BERLIN"), (70, "CLOCK")):
    for i, ch in enumerate(word):
        ANCH[start + i] = ch

# ---- locate the three confirmed error letters (1-based positions) ----
p1 = K1PT.index("Q") + 1                       # IQLUSION  (L -> Q)
p2 = K2PT.index("UNDERGRUUND") + 8             # 8th letter (O -> U)
p3 = K3PT.index("DESPARATLY") + 5              # 5th letter (E -> A)

errors = [
    ("K1", "IQLUSION",    "ILLUSION",    "Q", "L", p1, len(K1PT)),
    ("K2", "UNDERGRUUND", "UNDERGROUND", "U", "O", p2, len(K2PT)),
    ("K3", "DESPARATLY",  "DESPERATELY", "A", "E", p3, len(K3PT)),
]

print("section  carved word     intended word    wrong right  pos  passage len")
for sec, carved, intended, wrong, right, p, L in errors:
    print(f"{sec}       {carved:<13} {intended:<14}   {wrong}     {right}   {p:>4}   {L}")

wrong = "".join(e[3] for e in errors)
right = "".join(e[4] for e in errors)
print(f"\nwrong letters (K1,K2,K3 order): {wrong}")
print(f"right letters (K1,K2,K3 order): {right}")
print("sorted:", sorted(wrong), "-> anagrams: QUA -> 'AQUA(+E)' needs one more letter")

# ---- do the error positions point into K4? ----
print("\nerror positions projected onto K4 (97 letters):")
for sec, *_rest, p, L in errors:
    pos = p % 97 or 97
    known = ANCH.get(pos)
    print(f"  {sec}: pos {p:>3} -> K4 pos {pos:>2}  (ct {K4CT[pos-1]})",
          f"inside anchor -> '{known}'" if known else "outside released anchors")

# ---- letter inventory of the solved K4 words ----
known_words = "EAST" + "NORTHEAST" + "BERLIN" + "CLOCK"
from collections import Counter
c = Counter(known_words)
print("\nletters used by the four solved K4 words:", "".join(sorted(c)))
print("Q or U among them?", "Q" in c, "U" in c, "| A among them:", "A" in c)

# ---- QUAGMIRE completion check ----
print("\nQUA + ? = QUAG... : a 4th error letter G would start 'QUAGMIRE'",
      "(a cipher family - Quagmire III is used by the solvekryptos.com mechanism)")
print("EQUA as anagram -> AQUAE (Latin 'of water');",
      "sanborn's K4 element theory maps K4=water, K5=aether")
