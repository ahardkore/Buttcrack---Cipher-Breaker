import re

with open("theophilus_hendrie.txt") as f:
    text = f.read().upper()

clean = re.sub(r'[^A-Z]', '', text)

# Find repeated or salient phrases of length 21 and 24
print("Extracting candidate 21-letter and 24-letter phrases from Theophilus...")

# Look for titles and chapter headings
headings = re.findall(r'CHAPTER\s+[IVXLCDM]+\.?\s*\n+([^\n]+)', text)
for h in headings:
    h_clean = re.sub(r'[^A-Z]', '', h)
    if len(h_clean) in [21, 24, 7, 8, 9, 12, 14, 18, 28]:
        print(f"Heading (len {len(h_clean)}): {h_clean} ({h.strip()})")

# Check Kryptos canonical phrases
kryptos_phrases = [
    "BETWEENSUBTLESHADING", # 20
    "ANDTHEABSENCEOFLIGHT", # 20
    "LIESTHENUANCEOFIQLUS", # 20
    "ITWASTOTALLYINVISIBLE", # 21!
    "HOWSTHATPOSSIBLETHEY", # 20
    "USEDTHEEARTHSMAGNETI", # 20
    "CFIELDTHEINFORMATION", # 20
    "SLOWLYDESPARATLYSLOW", # 20
    "LYTHEREMAINSOFPASSAG", # 20
    "EDEBRISTHATENCUMBERE", # 20
    "DTHELOWERPARTOFTHE",   # 18
    "EASTNORTHEASTBERLINCL", # 21!
    "NORTHEASTBERLINCLOCK",  # 20
    "WILLIAMWEBSTERDIRECT",  # 20
    "CENTRALINTELLIGENCEAG", # 21!
]

print("\nKryptos phrases of length 21:")
for p in kryptos_phrases:
    if len(p) == 21:
        print(f"  {p}")
