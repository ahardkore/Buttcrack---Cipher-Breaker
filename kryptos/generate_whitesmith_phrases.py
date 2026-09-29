import itertools

# Build rich, grammatically valid combinations of whitesmith/needle-making sentences:
subjects = ["HE", "THE WHITESMITH", "THE MASTER", "I", "WE"]
verbs1 = [
    "TOOK UP", "HEATED", "PLACED", "LAID", "STRUCK", "PULLED", "DREW", "HELD",
    "GRASPED", "WITHDREW", "CLEANED", "FILED", "CUT", "BEAT", "HAMMERED", "PIERCED"
]
adjectives = [
    "", "GLOWING ", "HOT ", "WHITE ", "FINE ", "THIN ", "SOFT ", "HARD ",
    "TINY ", "ROUND ", "SHARP ", "SMOOTH ", "SLENDER ", "COLD "
]
nouns1 = [
    "WIRE", "IRON", "STEEL", "METAL", "ROD", "NEEDLE", "TOOL", "DRAWPLATE",
    "CHISEL", "PUNCH", "FILE", "HAMMER", "TONGS", "COALS", "HEARTH", "ANVIL"
]

connectors = [
    " AND ", " TO ", " WITH ", " FROM ", " INTO ", " UPON ", " THROUGH ", " BEFORE "
]

actions2 = [
    "DRAW IT THROUGH THE HOLE", "PULL IT THROUGH THE PLATE", "DRAW THE WIRE THROUGH",
    "THE FIRST HOLE OF THE PLATE", "EACH HOLE WAS SMALLER", "GRADUATED HOLES",
    "PUNCHED WITH GRADUATED HOLES", "UNTIL IT WAS THIN", "UNTIL IT WAS AS FINE",
    "AS FINE AS A HAIR", "FINE ENOUGH TO SPLIT A HAIR", "PIERCE THE EYE",
    "FORM THE EYE OF THE NEEDLE", "WITH A TINY PUNCH", "SHARPEN THE POINT",
    "ON THE WHETSTONE", "QUENCH IT IN WATER", "TEMPER IT IN THE FLAME",
    "HARDEN THE STEEL", "COOL IT IN THE TROUGH", "HANDED IT TO ME",
    "THIS IS HOW THE NEEDLE", "TO READ ANY KNOT", "READ THE SECRET OF THE KNOT",
    "INSCRIBED UPON ITS THREAD", "THE LOST ARCHIVE OF PELLEGRIN",
    "TREATISE ON TEXTILES", "STUDY UNDER ME FOR TEN YEARS"
]

phrases = set()

# Pattern 1: Direct sentences
p1_templates = [
    "HE DREW THE {adj}WIRE THROUGH THE {plate}",
    "HE PULLED THE {adj}WIRE THROUGH THE {plate}",
    "THROUGH THE FIRST HOLE OF THE {plate}",
    "THROUGH EACH GRADUATED HOLE OF THE {plate}",
    "EACH HOLE WAS SMALLER THAN THE {prev}",
    "UNTIL THE WIRE WAS AS FINE AS {comp}",
    "UNTIL THE WIRE WAS THIN ENOUGH TO {purpose}",
    "HE HEATED THE {adj}IRON IN THE {hearth}",
    "HE PLACED THE {adj}METAL ON THE {anvil}",
    "WITH THE HEAVY HAMMER HE STRUCK THE {metal}",
    "HE HAMMERED THE {adj}ROD INTO A THIN {wire}",
    "HE TAPERED THE END OF THE {adj}WIRE",
    "SO THAT IT WOULD FIT THROUGH THE {hole}",
    "HE GREASED THE IRON PLATE WITH {fat}",
    "AND PULLED THE WIRE WITH ALL HIS {strength}",
    "AGAIN AND AGAIN HE DREW THE {wire}",
    "HE ANNEALED THE WIRE IN THE {hearth}",
    "TO SOFTEN THE METAL BEFORE {drawing}",
    "THEN HE CUT THE WIRE INTO {lengths}",
    "WITH A SHARP CHISEL HE CUT THE {wire}",
    "HE FLATTENED ONE END ON THE {anvil}",
    "WITH A TINY PUNCH HE PIERCED THE {eye}",
    "HE PUNCHED THE EYE OF THE {needle}",
    "HE FILED THE EYE SMOOTH WITH A {file}",
    "HE SHARPENED THE OTHER END ON A {stone}",
    "UNTIL THE POINT WAS SHARP ENOUGH TO {pierce}",
    "TO SPLIT A HAIR OR PIERCE {glass}",
    "HE HEATED THE NEEDLE ONCE MORE IN THE {hearth}",
    "AND PLUNGED IT INTO COLD {liquid}",
    "TO HARDEN THE STEEL OF THE {needle}",
    "THEN HE TEMPERED IT IN THE {smoke}",
    "HE SMILED AND HANDED THE NEEDLE TO {me}",
    "THIS IS THE FIRST NEEDLE OF YOUR {making}",
    "NOW TAKE THE NEEDLE AND BEGIN TO {unravel}",
    "TO READ THE LETTERS ON THE {knot}",
    "UN AGO TANTO SOTTILE DA LEGGERE {nodo}",
    "A NEEDLE FINE ENOUGH TO READ ANY {knot}",
    "THE SECRET LIES IN THE LOST {archive}",
    "IN THE TREATISE ON TEXTILES BY {pellegrin}",
    "FRANCISQUE PELLEGRIN WROTE OF A {needle}"
]

fillers = {
    "adj": ["", "THIN ", "FINE ", "HOT ", "GLOWING ", "SOFT "],
    "plate": ["DRAWPLATE", "IRON PLATE", "PLATE"],
    "prev": ["LAST", "PREVIOUS", "FIRST"],
    "comp": ["A HAIR", "SILK THREAD", "THREAD", "A SINGLE HAIR"],
    "purpose": ["SPLIT A HAIR", "PIERCE GLASS", "READ THE KNOT"],
    "hearth": ["HEARTH", "FIRE", "COALS", "FLAME"],
    "anvil": ["ANVIL", "STONE BLOCK", "IRON BLOCK"],
    "metal": ["IRON", "STEEL", "WIRE", "METAL"],
    "wire": ["WIRE", "ROD", "THREAD", "STRAND"],
    "hole": ["HOLE", "FIRST HOLE", "SMALLEST HOLE"],
    "fat": ["TALLOW", "OIL", "GREASE", "FAT"],
    "strength": ["MIGHT", "STRENGTH", "POWER"],
    "drawing": ["DRAWING", "PULLING", "THE NEXT HOLE"],
    "lengths": ["SHORT LENGTHS", "EQUAL LENGTHS", "PIECES"],
    "eye": ["EYE", "TINY EYE", "HOLE"],
    "needle": ["NEEDLE", "FIRST NEEDLE", "FINE NEEDLE"],
    "file": ["FINE FILE", "NEEDLE FILE", "SMALL FILE"],
    "stone": ["WHETSTONE", "GRINDSTONE", "STONE"],
    "pierce": ["SPLIT A HAIR", "PIERCE GLASS", "SEW SILK"],
    "glass": ["GLASS", "A HAIR", "THIN SILK"],
    "liquid": ["WATER", "OIL", "BRINE"],
    "smoke": ["SMOKE", "FLAME", "COALS", "FIRE"],
    "me": ["ME", "THE ARCHIVIST", "MY HAND"],
    "making": ["MAKING", "OWN MAKING", "HANDS"],
    "unravel": ["UNRAVEL THE KNOT", "READ THE THREAD", "WORK"],
    "knot": ["KNOT", "THREAD", "WOUND KNOT"],
    "nodo": ["QUALUNQUE NODO", "OGNI NODO"],
    "archive": ["ARCHIVE OF PELLEGRIN", "ARCHIVE", "BOOK"],
    "pellegrin": ["PELLEGRIN", "FRANCISQUE PELLEGRIN"]
}

for t in p1_templates:
    # find all {keys} in template
    keys = [k for k in fillers if "{" + k + "}" in t]
    val_lists = [fillers[k] for k in keys]
    for comb in itertools.product(*val_lists):
        s = t
        for k, v in zip(keys, comb):
            s = s.replace("{" + k + "}", v)
        clean = "".join(c for c in s.upper() if c.isalpha())
        if len(clean) >= 14:
            # slice into windows of length 14, 16, 18, 20
            for wlen in [14, 15, 16, 17, 18]:
                for st in range(len(clean) - wlen + 1):
                    phrases.add(clean[st : st + wlen])

print(f"Generated {len(phrases)} unique candidate crib windows.")

with open("/home/user/whitesmith_cribs.txt", "w") as f:
    for p in sorted(phrases):
        f.write(p + "\n")

print("Saved to /home/user/whitesmith_cribs.txt")
