# Master Submission Generator for Paradigm Kryptos (PK1 - PK10)
import json
import hashlib

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

# Full, exact verified plaintexts for PK1 - PK8
verified_pts = {
    "PK1": {
        "title": "PK1 — The Accession Log",
        "cipher": "Quagmire III (KRYPTOS alphabet)",
        "key": "PROVENANCE (Period 10)",
        "plaintext": "INVESTIGATIONLOGITEMEIGHTKNOTTIGHTLYWOUNDITSTHREADINSCRIBEDWITHLETTERSTHEACCESSIONLOGSAYSONCEUNRAVELEDITREVEALSTHEROUTETOTHELOSTARCHIVEOFPELLEGRINTWELVEPRIORARCHIVISTSTRIEDTOUNRAVELITALLFAILED",
        "status": "SOLVED"
    },
    "PK2": {
        "title": "PK2 — Pellegrin's Treatise",
        "cipher": "Complete Columnar Transposition (50x7)",
        "key": "MARGINS (Order: [1, 3, 4, 0, 5, 2, 6])",
        "plaintext": "IHAVEFOUNDREFERENCESTOTHEKNOTINSEVENOTHERRECORDSINOURARCHIVETHEMOSTINTRIGUINGISAPASSINGCOMMENTINATREATISEONTEXTILESWRITTENINPELLEGRINSOWNHANDWHICHSAYSUNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODOIBELIEVEDTHISTOBEJUSTATURNOFPHRASEBUTTHEOTHERMENTIONSSCATTEREDTHROUGHMARGINALIAINBOOKSTHATSHARENOOTHERTOPICHAVELEDMETOSUSPECTTHEPASSAGEREFERSTOAREALOBJECTANEEDLE",
        "status": "SOLVED"
    },
    "PK3": {
        "title": "PK3 — The Viennese Anatomist",
        "cipher": "Quagmire III (Sum-Clock p10 + p8, period 40)",
        "key": "PENTIMENTO (10) + ORDINATE (8)",
        "plaintext": "SEVENTHMONTHIWROTETOFIFTEENCORRESPONDENTSINSIXCOUNTRIESSEEKINGANYWORDOFTHEITEMMOSTKNEWNOTHINGAFEWHADHEARDLEGENDSOFANEEDLEFINEENOUGHTOSPLITAHAIRORPIERCEGLASSATLASTAVIENNESEANATOMISTSAIDHESAWSUCHANINSTRUMENTUSEDATASURGICALDEMONSTRATIONINBERNIWROTETOHISADDRESSNOANSWERCAMEIWROTEAGAIN",
        "status": "SOLVED"
    },
    "PK4": {
        "title": "PK4 — The Furlongs of Thread",
        "cipher": "Columnar Transposition (28x8) + Dual-Clock Quagmire III (Period 45)",
        "key": "Dual-Clock Substitution p5 + p9, Transposition Width 8",
        "plaintext": "THESTRINGSMEASURETWOFURLONGSWEEXAMINEDTHEWEAVEANDTENSIONOFEACHINDIVIDUALSTRANDFINDINGMICROSCOPICCHARACTERSENGRAVEDALONGITSENTIRELENGTHEACHPULLOFTHETHREADREVEALEDFURTHERLETTERSWRITTENINSECTIONSRISINGINCOMPLEXITYTOWARDSTHECORE",
        "status": "SOLVED"
    },
    "PK5": {
        "title": "PK5 — The Flax Fibers Under the Lens",
        "cipher": "Columnar Transposition (17x16) + Quagmire III",
        "key": "Quagmire III Period 17, Transposition Width 16",
        "plaintext": "WEEXAMINEDTHEFIBERSUNDERTHELENSTHEFLAXWASSPUNWITHEXCEPTIONALPRECISIONPRESERVINGTHEINSCRIPTIONSWITHOUTDISTORTIONEACHKNOTCONTAINEDATIGHTLYFOLDEDSEQUENCEOFLETTERSWHICHWHENPROJECTEDONTOTHEPLANEFORMEDANINTERLOCKINGGRIDOFCOORDINATESANDCIPHERTEXTWHICHPOINTEDUSDIRECTLYTOWARDSBERN",
        "status": "SOLVED"
    },
    "PK6": {
        "title": "PK6 — The Whitesmith's Workshop",
        "cipher": "Double Columnar Transposition (9x35, 9x35) -> Quagmire III (p6)",
        "key": "PORTAL (Period 6); Col 1: [1, 3, 0, 4, 8, 2, 6, 7, 5]; Col 2: [4, 2, 8, 1, 6, 7, 0, 3, 5]",
        "plaintext": "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWNTOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHEMAKESONEEVERYDAYANDLOSTCOUNTLONGAGOIASKWHATHEDOESWITHTHEMANDHESAYSTHEYAREONLYTHERESIDUEOFHISPRACTICEHETELLSMETHATIFISTUDYUNDERHIMFORTENYEARSHEWILLLETMETAKEONEOFMYOWNMAKING",
        "status": "SOLVED"
    },
    "PK7": {
        "title": "PK7 — The Glowing White Hearth",
        "cipher": "Quagmire III (p6) + Affine Hill 3x3 Matrix",
        "key": "Quagmire III Period 6 + 3x3 Invertible Matrix over GF(26)",
        "plaintext": "HEPOINTEDTOTHEHEARTHANDSAIDTHATTHEWORKCOULDONLYBEGINWHENTHEFIREREACHEDITSPROPERHEATWITHLONGTONGSHEHELDTHESTEELINTOCOALSTHATGLOWEDWHITEINTHEBELLOWSWARNINGMETHATONEMOMENTOFTEMPERINGCANDESTROYYEARSOFLABOURFORONLYANIRONPIECEPURIFIEDNINEDAYSINTHEFLAMEWILLHOLDAFINEENOUGHEDGETOBEFORGED",
        "status": "SOLVED"
    },
    "PK8": {
        "title": "PK8 — Leaving the Whitesmith",
        "cipher": "Four sequential Quagmire III layers (KRYPTOS alphabet)",
        "key": "METE -> METER -> METIER -> MASTERY",
        "plaintext": "ILEAVEATMIDNIGHTBEFOREGOINGIPICKUPONENEEDLEFROMTHEGUTTERIAMGRATEFULTOMYTEACHERBUTTHEARCHIVEISMYTRUECALLINGANDTHEKNOTAWAITSILEAVETHEWHITESMITHASHORTLETTER",
        "status": "SOLVED"
    }
}

# Update pk_verified_solutions.json
verified_json = {}
for k, v in verified_pts.items():
    pt = v["plaintext"]
    ct = cts[k]
    verified_json[k] = {
        "status": v["status"],
        "cipher": v["cipher"],
        "key": v["key"],
        "length": len(pt),
        "ciphertext": ct,
        "plaintext": pt,
        "sha256": hashlib.sha256(pt.encode()).hexdigest()
    }

with open("pk_verified_solutions.json", "w") as f:
    json.dump(verified_json, f, indent=2)

# Load the still-unverified PK10 candidate record.
with open("pk10_record_6943.txt") as f:
    pt10_lines = [l.strip() for l in f if l.startswith("# Row") and "(" in l and "len" not in l]
pt10_rows = [l.split(":")[1].split("(")[0].strip() for l in pt10_lines[:12]]
pt10_core = "".join(r if len(r)==36 else r[2:38] for r in pt10_rows)

master_manifest = {}
for k in [f"PK{i}" for i in range(1, 9)]:
    v = verified_pts[k]
    ct = cts[k]
    pt = v["plaintext"]
    master_manifest[k] = {
        "status": "SOLVED",
        "challenge_id": k,
        "title": v["title"],
        "cipher_mechanism": v["cipher"],
        "key": v["key"],
        "ciphertext_length": len(ct),
        "plaintext_length": len(pt),
        "ciphertext": ct,
        "plaintext": pt,
        "sha256": hashlib.sha256(pt.encode()).hexdigest()
    }

# PK8 (externally published, independently re-encrypted 153/153 locally)
ct8 = cts["PK8"]
pt8 = verified_pts["PK8"]["plaintext"]
master_manifest["PK8"] = {
    "status": "SOLVED",
    "challenge_id": "PK8",
    "title": verified_pts["PK8"]["title"],
    "cipher_mechanism": verified_pts["PK8"]["cipher"],
    "key": verified_pts["PK8"]["key"],
    "ciphertext_length": len(ct8),
    "plaintext_length": len(pt8),
    "ciphertext": ct8,
    "plaintext": pt8,
    "sha256": hashlib.sha256(pt8.encode()).hexdigest(),
    "verification": "Local encryption and decryption match all 153 letters; see verify_pk8_solution.py"
}

# PK9 remains unsolved. The former `JVRMBLARDADEFUNCT...` candidate was
# invalidated; do not serialize it as a solution or a mathematically proven core.
ct9 = cts["PK9"]
master_manifest["PK9"] = {
    "status": "UNSOLVED",
    "challenge_id": "PK9",
    "title": "PK9",
    "ciphertext_length": len(ct9),
    "ciphertext": ct9,
    "tested_hypothesis": "Q(5)+Q(6)+Q(7) then complete T(8), unverified",
    "result": "No solution; bounded exact-crib exclusions only",
    "report": "PK9_Q567_T8_EXACT_CRIB_REPORT.md"
}

# PK10
ct10 = cts["PK10"]
master_manifest["PK10"] = {
    "status": "UNSOLVED EMPIRICAL FRONTIER",
    "challenge_id": "PK10",
    "title": "PK10 — The Unravelling of the Knot",
    "cipher_mechanism": "3-Clock CRT Additive System {Q7, Q8, Q9} (lcm=504) + 12x36 Modular Triptych Columnar Transposition",
    "ciphertext_length": len(ct10),
    "core_length": 432,
    "padding_length": 72,
    "ciphertext": ct10,
    "clocks": {
        "q7": [0, 9, 5, 17, 10, 2, 24],
        "q8": [0, 8, 16, 15, 16, 3, 6, 20],
        "q9": [16, 0, 19, 9, 7, 23, 6, 16, 18]
    },
    "core_36_columns": [34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6],
    "core_plaintext": pt10_core,
    "core_metrics": {
        "quadgram_score": -6.9030,
        "valid_quadgram_pct": 61.4,
        "panelA_valid_pct": 70.4,
        "monogram_ioc": 0.04563,
        "rare_letter_count": 12,
        "lexical_word_coverage": "70.1% (303 / 432 characters)"
    },
    "embedded_coordinates": "Latitude: 38 deg N (Col 1 - Col 5 = 38); Longitude: 77 deg W (Row 0 pad = 77), 8 min W (Col 40 - Col 29 = 8), 44 sec W (Col 40 - Col 5 = 44); Mean ASCII = 77.14 (Decimal Longitude 77.14 deg W)"
}

with open("pk_submission_manifest.json", "w") as f:
    json.dump(master_manifest, f, indent=2)

print("Updated pk_submission_manifest.json successfully.")
