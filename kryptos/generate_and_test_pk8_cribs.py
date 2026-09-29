import sys
import numpy as np

# We generate templates for 18-letter openers
# Subject, Verb, Object, Preposition, etc.
subjects = [
    "HE", "THE MASTER", "THE WHITESMITH", "THE OLD MAN", "MY MASTER",
    "WHEN THE FIRE", "WHEN THE COALS", "AS THE COALS", "AT LAST THE FIRE",
    "AT LAST THE WORK", "NOW THE FIRE", "NOW THE WORK", "I WATCHED AS HE",
    "I WATCHED HIM", "HE TOLD ME TO", "HE SHOWED ME", "THE CRUCIBLE",
    "THE SILVER", "THE IRON", "WITH THE TONGS HE", "FROM THE HEARTH HE",
    "ONTO THE ANVIL HE", "OVER THE COALS HE", "THE HEAT OF THE"
]

verbs = [
    "TOOK UP", "TOOK", "PLACED", "PUT", "HELD", "DREW", "STRUCK", "TURNED TO",
    "STEPPED TO", "LAID", "POURED", "MELTED", "HEATED", "CAST", "WAS", "WERE",
    "REACHED", "TURNED", "GLOWED", "BEGAN", "BEGAN TO", "COULD", "SET"
]

objects = [
    "THE CRUCIBLE", "THE TONGS", "THE HAMMER", "THE SILVER", "THE IRON",
    "THE METAL", "THE WIRE", "THE DIE", "THE NEEDLE", "THE ANVIL", "THE HEARTH",
    "THE FORGE", "THE COALS", "THE FIRE", "THE FLAME", "WHITE", "HOT", "READY",
    "LIT", "HIS TOOLS", "A PIECE OF", "A SMALL", "A ROUND"
]

preps = [
    "INTO THE FIRE", "INTO THE HEARTH", "INTO THE COALS", "UPON THE HEARTH",
    "UPON THE ANVIL", "UPON THE COALS", "OVER THE FIRE", "OVER THE COALS",
    "WITH THE TONGS", "WITH THE HAMMER", "WITH A HAMMER", "WITH CARE",
    "IN HIS HANDS", "IN THE CRUCIBLE", "AND BEGAN", "AND SAID", "AND TOLD ME",
    "BEFORE THE", "UNTIL IT", "UNTIL THEY", "TO THE ANVIL", "FROM THE FIRE"
]

# Write all 18-letter phrases formed by combinations
seen = set()

def clean(s):
    return ''.join(c for c in s.upper() if c.isalpha())

# Templates
phrases = []

# Template 1: Subj + Verb + Obj
for s in ["HE", "THE MASTER", "THE WHITESMITH", "THE OLD MAN", "MY MASTER"]:
    for v in ["TOOK UP", "TOOK", "PLACED", "PUT", "HELD", "DREW", "STRUCK", "TURNED TO", "STEPPED TO", "LAID", "POURED", "MELTED", "HEATED", "CAST", "SET"]:
        for o in ["THE CRUCIBLE", "THE TONGS", "THE HAMMER", "THE SILVER", "THE IRON", "THE METAL", "THE WIRE", "THE DIE", "THE NEEDLE", "THE ANVIL", "THE HEARTH", "A PIECE OF IRON", "A PIECE OF SILVER", "THE SMALL CRUCIBLE", "THE LONG TONGS", "THE HEAVY HAMMER"]:
            for p in ["IN THE FIRE", "IN THE COALS", "UPON THE ANVIL", "UPON THE HEARTH", "WITH THE TONGS", "INTO THE COALS", "OVER THE FIRE", "AND BEGAN TO", "AND SAID THAT", "UNTIL IT GLOWED"]:
                txt = clean(f"{s} {v} {o} {p}")
                if len(txt) >= 18:
                    c18 = txt[:18]
                    if c18 not in seen:
                        seen.add(c18)
                        phrases.append(c18)

# Template 2: When / As / At last / Now + Subj + Verb + Adj
for opener in ["WHEN THE COALS", "WHEN THE FIRE", "AS THE COALS", "AS THE FIRE", "AT LAST THE FIRE", "AT LAST THE WORK", "NOW THE FIRE", "NOW THE WORK", "NOW THE COALS", "ONCE THE COALS", "ONCE THE FIRE"]:
    for v in ["WERE", "WAS", "TURNED", "GLOWED", "REACHED", "GREW", "BECAME", "HAD REACHED"]:
        for adj in ["WHITE", "HOT", "READY", "PROPER HEAT", "WHITE HOT", "ENOUGH HEAT", "LIT"]:
            for cont in ["HE TOOK THE TONGS", "HE PLACED THE", "HE TOOK UP THE", "HE PUT THE", "HE TURNED TO", "THE WORK BEGAN", "THE MASTER TOOK", "HE REACHED FOR", "THE CRUCIBLE WAS"]:
                txt = clean(f"{opener} {v} {adj} {cont}")
                if len(txt) >= 18:
                    c18 = txt[:18]
                    if c18 not in seen:
                        seen.add(c18)
                        phrases.append(c18)

# Template 3: 1st person
for opener in ["I WATCHED AS HE", "I WATCHED HIM", "HE TOLD ME TO", "HE SHOWED ME HOW", "HE SAID TO ME"]:
    for v in ["TOOK", "TAKE", "PLACED", "PLACE", "PUT", "HOLD", "HELD", "BLOW", "DRAW", "STRIKE"]:
        for o in ["THE CRUCIBLE", "THE TONGS", "THE HAMMER", "THE SILVER", "THE IRON", "THE WIRE", "THE DIE"]:
            for p in ["INTO THE FIRE", "UPON THE ANVIL", "OVER THE COALS", "AND WORK", "AND BEGIN"]:
                txt = clean(f"{opener} {v} {o} {p}")
                if len(txt) >= 18:
                    c18 = txt[:18]
                    if c18 not in seen:
                        seen.add(c18)
                        phrases.append(c18)

# Template 4: Tools/Objects
for o in ["THE CRUCIBLE WAS", "THE SILVER WAS", "THE IRON WAS", "THE TONGS WERE", "THE HEAT OF THE", "THE SOUND OF THE", "FROM THE HEARTH HE", "ONTO THE ANVIL HE", "WITH THE TONGS HE"]:
    for v in ["PLACED IN THE", "PUT INTO THE", "HEATED UNTIL", "MELTED IN THE", "STRUCK WITH THE", "DRAWN THROUGH THE", "HELD OVER THE", "TAKEN FROM THE"]:
        for cont in ["FIRE", "COALS", "HEARTH", "ANVIL", "FORGE", "DIE", "WATER"]:
            txt = clean(f"{o} {v} {cont} AND THEN")
            if len(txt) >= 18:
                c18 = txt[:18]
                if c18 not in seen:
                    seen.add(c18)
                    phrases.append(c18)

print(f"Generated {len(phrases)} unique 18-letter narrative candidate cribs.")
with open("pk8_narrative_cribs.txt", "w") as f:
    for p in phrases:
        f.write(p + "\n")
