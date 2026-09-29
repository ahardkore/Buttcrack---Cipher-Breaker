import re

files = [
    "candidate_running_keys.txt",
    "theophilus_hendrie.txt",
    "theophilus_book3_english.txt"
]

all_text = ""
for fn in files:
    try:
        with open(fn) as f:
            all_text += " " + f.read().upper()
    except Exception:
        pass

# Extract sentences / clauses
clauses = re.split(r'[\.\,\;\:\n\r\t]+', all_text)
phrases = set()

# Narrative crafted cribs
crafted = [
    "THELOSTARCHIVEOFPELLEGRIN",
    "ARCHIVEOFPELLEGRIN",
    "THEFINALUNRAVELLINGOFTHEKNOT",
    "UNRAVELLINGOFTHEKNOT",
    "THEKNOTWASATLASTUNRAVELED",
    "THEINSCRIBEDTHREADREVEALED",
    "ONCEUNRAVELEDITREVEALSTHEROUTE",
    "ONCEUNRAVELEDITREVEALS",
    "REVEALSTHEROUTETOTHELOSTARCHIVE",
    "THEROUTETOTHELOSTARCHIVE",
    "THELOSTARCHIVEISFOUND",
    "THELOSTARCHIVEISOPENED",
    "WITHITSSLENDERPOINTIUNRAVELED",
    "WITHITSSLENDERPOINT",
    "SLENDERPOINTIUNRAVELED",
    "THEREALOBJECTWASANEEDLE",
    "THEREALOBJECTANEEDLE",
    "ANEEDLEFINEASAHAIROFPURESILVER",
    "FINEASAHAIROFPURESILVER",
    "ACURVEDSILVERNEEDLEFINEASHAIR",
    "INTHEMUNICIPALLIBRARYOFBERN",
    "INTHEDISSECTINGTHEATERATBERN",
    "THEDISSECTINGTHEATERATBERN",
    "INTHEDISSECTINGTHEATER",
    "INTHELOCKEDCHESTINTHETHEATER",
    "INTHELOCKEDCHESTATBERN",
    "APASSAGEINLATINENGRAVEDUPON",
    "APASSAGEINLATINENGRAVED",
    "THEWHITESMITHWORKSHOPISFILLED",
    "THEWORKCOULDONLYBEGINWHENTHE",
    "THEFIREREACHEDITSPROPERHEAT",
    "THESTEELINTOCOALSTHATGLOWED",
    "THATGLOWEDWHITEINTHEBELLOWS",
    "ONEMOMENTOFTEMPERINGCANDESTROY",
    "YEARSOFLABOURANDPRACTICE",
    "ATLASTTHEFIREWASLITANDTHE",
    "THEBELLOWSSANGASCOALSTURNED",
    "THECOALSTURNEDWHITEINTHE",
    "THEMASTERPIECEWASCOMPLETED",
    "THEMASTERPIECEISCOMPLETED",
    "THEFINALMASTERPIECEISFINISHED",
    "THEFINALMASTERPIECEWASFINISHED",
    "THELATITUDEANDLONGITUDEOF",
    "LATITUDEANDLONGITUDEOF",
    "THECOORDINATESOFTHEARCHIVE",
    "THECOORDINATESAREFORTYSEVEN",
    "FIFTYTWODGREESNORTHANDFOUR",
    "UNDERNEATHTHEFOUNDATIONSTONE",
    "BENEATHTHEFOUNDATIONSTONE",
    "INTHEFOUNDATIONSTONEATBERN",
    "THECOMPASSROSEISHEREATBERN"
]

for c in crafted:
    clean = "".join(ch for ch in c.upper() if 'A' <= ch <= 'Z')
    if len(clean) >= 22:
        phrases.add(clean[:22])

for c in clauses:
    clean = "".join(ch for ch in c.upper() if 'A' <= ch <= 'Z')
    if len(clean) >= 22:
        # Take rolling 22-character windows
        for i in range(0, min(len(clean) - 21, 60), 5):
            phrases.add(clean[i:i+22])

print(f"Total candidate 22-character cribs extracted: {len(phrases)}")

with open("pk10_cribs_22.txt", "w") as f:
    for p in sorted(phrases):
        f.write(p + "\n")
