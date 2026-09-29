import subprocess

domain_words = [
    # Craft & Needlemaking
    "NEEDLEMAKING", "THREADMAKING", "METALWORKING", "GOLDSMITHING", "LOCKSMITHING",
    "PATTERNMAKER", "BELLOWSMAKER", "THIMBLEMAKER", "SCISSORSMITH", "SHOEINGSMITH",
    "ELECTROPLATE", "COUNTERPUNCH", "LEATHERCRAFT", "SILVERWORKER", "SILVERBEATER",
    "GROUNDNEEDLE", "RUBBINGSTONE", "TEMPEREDNESS", "IRONHANDEDLY", "FORGEABILITY",
    # Theophilus Latin & English
    "CONSTRUCTION", "INSTRUMENTUM", "ORGANARIUMMS", "DISPOSITIONE", "FABRICATIONE",
    "TEMPERAMENTO", "PURIFICATURR", "EXPERIENCING", "TRANSLUCENCE",
    # Pellegrin
    "LAFLEURDELAS", "POURTRAICTUR", "MORESQUESPAT", "TEXTILESTREA", "PELLEGRINSOW",
    "ARABICQUETAL", "QUALUNQUENOD", "TANTOSOTTILE",
    # Kryptos & Intelligence
    "INTELLIGENCE", "TRANSMISSION", "COORDINATION", "AUTHENTICITY", "UNDERGROUNDS",
    "INVESTIGATOR", "CRYPTOGRAPHY", "DECIPHERMENT", "PALIMPSESTIC", "ABSCISSAFORM",
    "ARCHIVISTLOG", "ACCESSIONLOG"
]

print(f"Total domain keywords: {len(domain_words)}")
# Test all pairs
pairs = []
for w1 in domain_words:
    for w2 in domain_words:
        pairs.append((w1, w2))

print(f"Total pairs: {len(pairs)}")

# Write to a file and compile fast test
with open("domain_pairs.txt", "w") as f:
    for w1, w2 in pairs:
        f.write(f"{w1} {w2}\n")

