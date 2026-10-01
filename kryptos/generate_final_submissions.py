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

# PK9 remains unsolved. Do not serialize incomplete leads as a solution.
ct9 = cts["PK9"]
master_manifest["PK9"] = {
    "status": "UNSOLVED",
    "challenge_id": "PK9",
    "title": "PK9",
    "ciphertext_length": len(ct9),
    "ciphertext": ct9,
    "tested_hypothesis": "Q(5)+Q(6)+Q(7) with a complete T(8), unverified",
    "result": "No solution; bounded exact-crib and global-phase bridge exclusions only",
    "reports": [
        "PK9_Q567_T8_EXACT_CRIB_REPORT.md",
        "PK9_PK8_PHASE_BRIDGE_REPORT.md"
    ],
    "verification_requirement": "A proposed answer must re-encrypt to every published ciphertext character."
}

# PK10 remains unsolved. Do not serialize an unverified research lead as a plaintext solution.
ct10 = cts["PK10"]
master_manifest["PK10"] = {
    "status": "UNSOLVED",
    "challenge_id": "PK10",
    "title": "PK10",
    "ciphertext_length": len(ct10),
    "ciphertext": ct10,
    "result": "No verified plaintext or construction",
    "verification_requirement": "A proposed answer must re-encrypt to every published ciphertext character."
}

with open("pk_submission_manifest.json", "w") as f:
    json.dump(master_manifest, f, indent=2)

print("Updated pk_submission_manifest.json successfully.")
