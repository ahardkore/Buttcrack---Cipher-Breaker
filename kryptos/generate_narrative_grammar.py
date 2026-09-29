import itertools, re

def build_grammar():
    phrases = set()

    # Grammar 1: [PREP] [TIME] [SUBJ] [VERB] [OBJ]
    preps1 = ["AFTER", "FOR", "DURING", "THROUGH", "AT THE END OF", "BEFORE"]
    times1 = [
        "NINE DAYS", "NINE DAYS IN THE FLAME", "NINE DAYS OF PURIFYING", "NINE DAYS AND NIGHTS",
        "NINE DAYS OF WAITING", "THE NINE DAYS", "THE NINE DAYS OF FLAME", "THE NINE DAYS IN THE COALS",
        "TEN YEARS", "TEN YEARS OF APPRENTICESHIP", "TEN YEARS OF STUDY", "TEN YEARS IN HIS SHOP",
        "MANY DAYS", "THREE DAYS", "SEVEN DAYS", "HOURS OF WORK", "DAYS OF LABOUR"
    ]
    subjs1 = ["HE", "I", "WE", "THE SMITH", "THE MASTER", "THE WHITESMITH", "MY MASTER"]
    verbs1 = [
        "TOOK", "DREW", "PULLED", "HELD", "PLACED", "LAID", "STRUCK", "BEGAN", "STARTED",
        "WAITED", "WATCHED", "TENDED", "KEPT", "REMOVED", "LIFTED", "CARRIED"
    ]
    objs1 = [
        "THE STEEL", "THE IRON", "THE METAL", "THE PURIFIED STEEL", "THE PURIFIED IRON",
        "THE GLOWING STEEL", "THE WHITE STEEL", "THE WIRE", "THE TONGS", "THE HAMMER",
        "TO WORK", "TO FORGE", "TO DRAW", "HIS WORK", "THE TASK", "OUR WORK"
    ]

    for p, t, s, v in itertools.product(preps1, times1, subjs1, verbs1):
        for o in objs1:
            phrases.add(f"{p} {t} {s} {v} {o}")

    # Grammar 2: [WHEN] [TIME/STATE] [SUBJ] [VERB]
    when_leads = [
        "WHEN NINE DAYS HAD PASSED", "WHEN THE NINE DAYS HAD PASSED", "WHEN THE NINE DAYS WERE OVER",
        "WHEN THE NINE DAYS WERE ENDED", "WHEN THE NINE DAYS WERE COMPLETED", "WHEN THE STEEL WAS PURIFIED",
        "WHEN THE METAL WAS PURIFIED", "WHEN THE STEEL WAS READY", "WHEN THE IRON WAS READY",
        "WHEN THE FIRE WAS READY", "WHEN THE COALS WERE WHITE", "WHEN THE PROPER HEAT WAS REACHED",
        "WHEN AT LAST THE STEEL WAS READY", "WHEN AT LAST THE WORK BEGAN", "ONCE THE NINE DAYS HAD PASSED",
        "ONCE THE STEEL WAS PURIFIED", "ONCE THE METAL WAS READY", "ONCE THE FIRE REACHED WHITE HEAT"
    ]
    for w, s, v in itertools.product(when_leads, subjs1, verbs1):
        for o in objs1:
            phrases.add(f"{w} {s} {v} {o}")

    # Grammar 3: [SUBJ] [VERB] [OBJ] [PREP] [LOC/INSTR]
    verbs_direct = [
        "DREW", "PULLED", "TOOK", "LIFTED", "WITHDREW", "REMOVED", "CARRIED"
    ]
    objs_direct = [
        "THE STEEL", "THE IRON", "THE METAL", "THE PURIFIED STEEL", "THE PURIFIED METAL",
        "THE GLOWING STEEL", "THE GLOWING IRON", "THE WHITE HOT STEEL", "THE PIECE OF STEEL",
        "THE ROD OF STEEL", "THE SLENDER STEEL"
    ]
    preps_from = [
        "FROM THE HEARTH", "FROM THE FIRE", "FROM THE FLAME", "FROM THE WHITE COALS",
        "FROM THE GLOWING COALS", "FROM THE COALS OF THE FORGE", "OUT OF THE FLAME",
        "OUT OF THE WHITE HEAT", "OUT OF THE HEARTH", "WITH LONG TONGS", "WITH HIS TONGS"
    ]
    conts = [
        "AND LAID IT UPON THE ANVIL", "AND PLACED IT ON THE ANVIL", "AND SET IT UPON THE ANVIL",
        "AND STRUCK IT WITH HIS HAMMER", "AND BEGAN TO BEAT IT", "AND BEGAN TO DRAW THE WIRE",
        "AND HELD IT TO THE LIGHT", "AND QUENCHED IT IN WATER", "AND COOLED IT IN WATER"
    ]
    for s, v, o, p in itertools.product(subjs1, verbs_direct, objs_direct, preps_from):
        phrases.add(f"{s} {v} {o} {p}")
        for c in conts[:4]:
            phrases.add(f"{s} {v} {o} {p} {c}")

    # Grammar 4: [PREP_INSTR] [SUBJ] [VERB] [OBJ]
    prep_instr = [
        "WITH LONG TONGS", "WITH HIS TONGS", "WITH THE TONGS", "WITH SLENDER TONGS",
        "WITH A HEAVY HAMMER", "WITH HIS HAMMER", "WITH THE HAMMER", "WITH SLENDER HAMMER",
        "UPON THE ANVIL", "UPON THE FACE OF THE ANVIL", "ON THE ANVIL", "AT THE ANVIL",
        "AT THE FORGE", "BY THE HEARTH", "IN THE WHITE HEAT"
    ]
    for p, s, v, o in itertools.product(prep_instr, subjs1, verbs_direct, objs_direct):
        phrases.add(f"{p} {s} {v} {o}")

    # Grammar 5: Striking / Forging / Needle drawing
    forge_starts = [
        "EACH BLOW OF THE HAMMER", "EACH STRIKE OF THE HAMMER", "EACH STROKE OF THE HAMMER",
        "BLOW AFTER BLOW", "WITH EACH BLOW OF HIS HAMMER", "UNDER THE HEAVY BLOWS",
        "HE STRUCK THE GLOWING STEEL", "HE BEAT THE PURIFIED STEEL", "HE HAMMERED THE HOT METAL",
        "HE DREW THE WIRE THROUGH THE DRAWPLATE", "HE DREW THE STEEL THROUGH THE DIE",
        "HE PULLED THE WIRE THROUGH THE DIE", "THROUGH THE FIRST HOLE OF THE DRAWPLATE",
        "THROUGH SMALLER AND SMALLER HOLES", "THROUGH GRADUATED HOLES HE DREW",
        "HE FLATTENED THE HEAD OF THE NEEDLE", "HE PUNCHED THE EYE OF THE NEEDLE",
        "WITH A SLENDER PUNCH HE PIERCED THE EYE", "WITH A FINE CHISEL HE CUT THE WIRE"
    ]
    forge_ends = [
        "UNTIL IT WAS THIN", "UNTIL IT WAS A FINE WIRE", "TO MAKE A FINE NEEDLE",
        "INTO A SLENDER THREAD", "INTO A FINE NEEDLE", "AS FINE AS A HAIR",
        "FINE ENOUGH TO SPLIT A HAIR", "TO READ ANY KNOT", "OF HIS OWN MAKING"
    ]
    for fs in forge_starts:
        for fe in forge_ends:
            phrases.add(f"{fs} {fe}")

    # Clean and extract 18-char prefixes
    cleaned = set()
    for ph in phrases:
        s = re.sub(r'[^A-Z]', '', ph.upper())
        if len(s) >= 18:
            cleaned.add(s[:18])

    return cleaned

cribs = build_grammar()
print(f"Total unique 18-character grammatical candidates: {len(cribs)}")

with open("pk8_grammar_cribs.txt", "w") as f:
    for c in sorted(cribs):
        f.write(c + "\n")

print("Saved to pk8_grammar_cribs.txt")
