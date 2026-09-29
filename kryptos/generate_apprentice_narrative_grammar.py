import sys

# Combinatorial generator of 18-character candidate prefixes for PK8
# Based on Dan Robinson's narrative voice continuing PK7:
# PK7: "...warning me that one moment of tempering can destroy years of labour"

openers = [
    # Pronoun / subject starts
    "I ", "HE ", "THEN HE ", "AND THEN HE ", "AT LAST HE ", "WITH CARE HE ",
    "WITH LONG TONGS HE ", "WITH STEADY HANDS HE ", "THE MASTER ", "THE WHITESMITH ",
    "NOW HE ", "NEXT HE ", "FOR HOURS HE ", "FOR DAYS HE ", "EACH DAY HE ",
    "EVERY DAY HE ", "EACH MORNING HE ", "WHEN THE STEEL ", "WHEN THE IRON ",
    "AS THE METAL ", "AS THE COALS ", "WHILE THE STEEL ", "BEFORE THE FIRE ",
    "ONCE THE METAL ", "ONLY WHEN THE ", "FOR ONLY THE ", "TO FORGE THE ",
    "TO MAKE THE ", "TO TEMPER THE ", "DRAWING THE ", "STRIKING THE ",
    "LIFTING THE ", "PLACING THE ", "WATCHING THE ", "HE TOLD ME ", "HE SHOWED ME ",
    "HE TAUGHT ME ", "HE HANDED ME ", "HE BADE ME ", "HE WARNED ME ",
    "I WATCHED AS HE ", "I WATCHED HIM ", "I TOOK THE ", "I HELD THE ",
    "I STRUCK THE ", "I BLEW THE ", "I TENDED THE ", "I PUMPED THE ",
    "DAY AFTER DAY I ", "FOR TEN YEARS I ", "IN HIS SHOP I ", "AT THE ANVIL I ",
    "AT THE HEARTH I ", "FROM THE HEARTH HE ", "OUT OF THE FIRE HE ",
    "FROM THE COALS HE ", "INTO THE WATER HE ", "INTO THE OIL HE ",
    "UPON THE ANVIL HE ", "THROUGH THE PLATE HE ", "THROUGH THE DRAWPLATE ",
    "THE FIRST STEP WAS ", "THE NEXT STEP WAS ", "THE SECRET WAS ",
    "THE WORK REQUIRED ", "EACH PIECE OF ", "EVERY NEEDLE ", "A FINE NEEDLE ",
    "THE SMALLEST NEEDLE ", "THE PERFECT NEEDLE ", "THE TIP MUST ",
    "THE EYE MUST ", "THE WIRE MUST ", "THE STEEL MUST ", "THE IRON MUST "
]

verbs = [
    "DREW ", "HELD ", "TOOK ", "STRUCK ", "PLACED ", "LIFTED ", "PULLED ",
    "QUENCHED ", "COOLED ", "HAMMERED ", "BEAT ", "FORGED ", "SHAPED ",
    "HEATED ", "REMOVED ", "LAID ", "CARRIED ", "TURNED ", "RUBBED ",
    "COATED ", "OILED ", "DIPPED ", "PLUNGED ", "DROPPED ", "THRUST ",
    "PASSED ", "RAN ", "SLID ", "FORCED ", "SMOOTHED ", "FILED ",
    "GROUND ", "POLISHED ", "SHARPENED ", "PIERCED ", "BORED ",
    "CUT ", "TESTED ", "PROVED ", "EXAMINED ", "MEASURED ", "WEIGHED ",
    "WATCHED ", "KEPT ", "LEFT ", "ALLOWED ", "BEGAN ", "CEASED "
]

objects = [
    "THE STEEL ", "THE IRON ", "THE METAL ", "THE WIRE ", "THE ROD ",
    "THE NEEDLE ", "THE BLANK ", "THE TIP ", "THE POINT ", "THE EYE ",
    "THE PIECE ", "THE TONGS ", "THE HAMMER ", "THE ANVIL ", "THE PLATE ",
    "THE DRAWPLATE ", "THE HEARTH ", "THE COALS ", "THE FIRE ", "THE FLAME ",
    "THE BELLOWS ", "THE WATER ", "THE OIL ", "THE FAT ", "THE TALLOW ",
    "THE ASHES ", "THE SLAG ", "THE CRUCIBLE ", "EACH WIRE ", "EVERY PIECE ",
    "A SLENDER WIRE ", "A THIN ROD ", "A SINGLE HAIR ", "HIS HAMMER ",
    "HIS TONGS ", "HIS HAND ", "MY HAND "
]

preps = [
    "FROM THE FIRE ", "FROM THE COALS ", "FROM THE HEARTH ", "FROM THE FLAME ",
    "INTO THE WATER ", "INTO THE OIL ", "INTO THE TROUGH ", "INTO THE ASHES ",
    "INTO THE COALS ", "INTO THE FLAME ", "UPON THE ANVIL ", "ON THE ANVIL ",
    "ON THE HORN ", "AGAINST THE STONE ", "UNDER THE HAMMER ", "WITH THE TONGS ",
    "WITH THE HAMMER ", "WITH A LIGHT BLOW ", "WITH HEAVY BLOWS ", "WITH STEADY HANDS ",
    "THROUGH THE HOLE ", "THROUGH THE PLATE ", "THROUGH THE DRAWPLATE ",
    "ACROSS THE SURFACE ", "ALONG THE EDGE ", "TO THE ANVIL ", "TO THE TROUGH ",
    "UNTIL IT GLOWED ", "UNTIL IT TURNED ", "UNTIL IT COOLED ", "UNTIL IT WAS ",
    "WHILE IT WAS RED ", "WHILE IT WAS HOT ", "WHILE THE METAL ",
    "BEFORE IT COOLED ", "AS IT GLOWED ", "AND BEGAN TO ", "AND STRUCK IT ",
    "AND DREW IT ", "AND HAMMERED IT ", "AND PLUNGED IT ", "AND QUENCHED IT "
]

tails = [
    "AGAIN ", "ONCE ", "TWICE ", "THRICE ", "SLOWLY ", "GENTLY ",
    "QUICKLY ", "DEFTLY ", "EVENLY ", "CLEANLY ", "SMOOTHLY ", "IN SILENCE ",
    "WITHOUT PAUSE ", "WITHOUT A SOUND ", "WITHOUT FEAR ", "DAY AND NIGHT ",
    "TIME AND AGAIN ", "TO DRAW IT FINE ", "TO MAKE IT SHARP ", "TO SHAPE THE EYE ",
    "TO SPLIT A HAIR ", "TO READ THE KNOT ", "FOR PELLEGRIN ", "IN THE FLAME ",
    "ON THE HORN ", "OF THE ANVIL ", "IN THE SHOP ", "AT THE FORGE "
]

phrases = set()

# Pattern 1: Opener + Verb + Object
for op in openers:
    for vb in verbs:
        p = (op + vb).replace(" ", "")
        if len(p) >= 18:
            phrases.add(p[:18])
        else:
            for ob in objects:
                p2 = (op + vb + ob).replace(" ", "")
                if len(p2) >= 18:
                    phrases.add(p2[:18])
                else:
                    for pr in preps:
                        p3 = (op + vb + ob + pr).replace(" ", "")
                        if len(p3) >= 18:
                            phrases.add(p3[:18])

# Pattern 2: Opener + Prep + Verb + Object
for op in ["THEN ", "AND ", "NEXT ", "NOW ", "HE ", "I "]:
    for pr in preps:
        for vb in verbs:
            p = (op + pr + vb).replace(" ", "")
            if len(p) >= 18:
                phrases.add(p[:18])
            else:
                for ob in objects:
                    p2 = (op + pr + vb + ob).replace(" ", "")
                    if len(p2) >= 18:
                        phrases.add(p2[:18])

# Pattern 3: Subject + Verb + Object + Prep + Tail
for s in ["HE ", "I ", "THE MASTER ", "THE WHITESMITH "]:
    for vb in verbs:
        for ob in objects:
            p = (s + vb + ob).replace(" ", "")
            if len(p) >= 18:
                phrases.add(p[:18])
            else:
                for pr in preps:
                    p2 = (s + vb + ob + pr).replace(" ", "")
                    if len(p2) >= 18:
                        phrases.add(p2[:18])

print(f"Generated {len(phrases)} unique 18-character narrative candidates.")

with open("apprentice_phrases_18.txt", "w") as f:
    for p in sorted(phrases):
        f.write(p + "\n")
