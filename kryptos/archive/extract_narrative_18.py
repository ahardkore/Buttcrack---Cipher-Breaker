"""
  ARCHIVED 2026-10-02 — SUPERSEDED / CONTAINS REFUTED TEXTS. DO NOT SUBMIT ANYTHING FROM THIS FILE.

  The PK4/PK5/PK7 'plaintexts' in early-session artifacts like this one were
  candidate narratives, NOT verified solutions.  The verified solutions are in
  kryptos/pk_verified_solutions.json (round-trip verified against the official
  ciphertexts by verify_pk_constructions.py) and are rendered for submission in
  kryptos/PARADIGM_KRYPTOS_FINAL_SUBMISSIONS.md.

  Correct PK4 plaintext (first 40 chars): TWOYEARSINTHENEEDLESTRAILLEDMETOACRAFTSM...
"""

import json, math, time

with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

with open("pk_verified_solutions.json") as f:
    sols = json.load(f)

# Extract all rolling 18-char substrings
phrases18 = set()
for k, v in sols.items():
    pt = v.get("plaintext", "")
    for i in range(len(pt) - 17):
        phrases18.add(pt[i:i+18])

# Also add phrases from the narrative
more_pts = [
    "THESTRINGSMEASURETWOFURLONGS",
    "WEEXAMINEDTHEFIBERSUNDERTHELENS",
    "HEPOINTEDTOTHEHEARTHANDSAIDTHATTHEWORKCOULDONLYBEGINWHENTHEFIREREACHEDITSPROPERHEATWITHLONGTONGSHEHELDTHESTEELINTOCOALSTHATGLOWEDWHITEINTHEBELLOWSWARNINGMETHATONEMOMENTOFTEMPERINGCANDESTROYYEARSOFLABOUR",
    "ATLASTTHEWORKWASGOINGTOPROVEANEEDLEFROMTHERESIDUEOFHISPRATICE",
    "THEWHITESMITHSWORKSHOP",
    "THEOLDTOOLSOFHISTRADE",
    "ANINTERLOCKINGGRIDOFCOORDINATES",
    "ACCESSIONLOGITEMEIGHT",
    "INVESTIGATIONLOGITEM"
]
for pt in more_pts:
    for i in range(len(pt) - 17):
        phrases18.add(pt[i:i+18])

print(f"Extracted {len(phrases18)} candidate 18-character narrative phrases.")

# Save to candidate_narrative_18.txt
with open("candidate_narrative_18.txt", "w") as f:
    for p in sorted(phrases18):
        f.write(p + "\n")
print("Saved candidate_narrative_18.txt")
