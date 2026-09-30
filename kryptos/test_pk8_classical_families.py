# Comprehensive Test of Classical Cipher Families on PK8 (N = 153)
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY"
N = len(PK8_CT) # 153 = 9 x 17

print("==========================================================================================")
print("             PK8 (153 CHARS = 9 x 17) CLASSICAL CIPHER FAMILIES TEST                      ")
print("==========================================================================================\n")

# 1. Folded IoC Scan across all periods 2..50
print("--- 1. Folded IoC for Periods 2..50 ---")
top_periods = []
for p in range(2, 51):
    slices = [PK8_CT[i::p] for i in range(p)]
    iocs = []
    for s in slices:
        if len(s) > 1:
            c = Counter(s)
            ioc = sum(v*(v-1) for v in c.values()) / (len(s)*(len(s)-1))
            iocs.append(ioc)
    avg_ioc = sum(iocs) / len(iocs)
    top_periods.append((avg_ioc, p))

top_periods.sort(reverse=True)
for ioc, p in top_periods[:10]:
    print(f"  Period {p:2d}: Average Slice IoC = {ioc:.5f}")

# 2. Check Factor Geometries for Transposition
print("\n--- 2. Transposition Factor Widths (153 = 9 x 17 = 17 x 9) ---")
# If it is a pure transposition, the monogram IoC of the raw ciphertext is:
c_raw = Counter(PK8_CT)
ioc_raw = sum(v*(v-1) for v in c_raw.values()) / (N * (N - 1))
print(f"Raw PK8 Monogram IoC: {ioc_raw:.5f}")
print("If PK8 were pure transposition with no substitution, IoC would be ~0.0667 (English).")
print(f"Since raw IoC is {ioc_raw:.5f} (near random 0.0385), PK8 MUST have a polyalphabetic substitution layer!\n")

# 3. Check Running Key from PK1-PK7
print("--- 3. Testing Running Key from PK1-PK7 Verified Plaintexts ---")
pk_pts = [
    "INVESTIGATIONLOGITEMEIGHTKNOTTIGHTLYWOUNDITSTHREADINSCRIBEDWITHLETTERSTHEACCESSIONLOGSAYSONCEUNRAVELEDITREVEALSTHEROUTETOTHELOSTARCHIVEOFPELLEGRINTWELVEPRIORARCHIVISTSTRIEDTOUNRAVELITALLFAILED",
    "IHAVEFOUNDREFERENCESTOTHEKNOTINSEVENOTHERRECORDSINOURARCHIVETHEMOSTINTRIGUINGISAPASSINGCOMMENTINATREATISEONTEXTILESWRITTENINPELLEGRINSOWNHANDWHICHSAYSUNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODOIBELIEVEDTHISTOBEJUSTATURNOFPHRASEBUTTHEOTHERMENTIONSSCATTEREDTHROUGHMARGINALIAINBOOKSTHATSHARENOOTHERTOPICHAVELEDMETOSUSPECTTHEPASSAGEREFERSTOAREALOBJECTANEEDLE",
    "SEVENTHMONTHIWROTETOFIFTEENCORRESPONDENTSINSIXCOUNTRIESSEEKINGANYWORDOFTHEITEMMOSTKNEWNOTHINGAFEWHADHEARDLEGENDSOFANEEDLEFINEENOUGHTOSPLITAHAIRORPIERCEGLASSATLASTAVIENNESEANATOMISTSAIDHESAWSUCHANINSTRUMENTUSEDATASURGICALDEMONSTRATIONINBERNIWROTETOHISADDRESSNOANSWERCAMEIWROTEAGAIN",
    "THESTRINGSMEASURETWOFURLONGSWEEXAMINEDTHEWEAVEANDTENSIONOFEACHINDIVIDUALSTRANDFINDINGMICROSCOPICCHARACTERSENGRAVEDALONGITSENTIRELENGTHEACHPULLOFTHETHREADREVEALEDFURTHERLETTERSWRITTENINSECTIONS",
    "WEEXAMINEDTHEFIBERSUNDERTHELENSTHEFLAXWASSPUNWITHEXCEPTIONALPRECISIONPRESERVINGTHEINSCRIPTIONSWITHOUTDISTORTIONEACHKNOTCONTAINEDATIGHTLYFOLDEDSEQUENCEOFLETTERSWHICHWHENPROJECTEDONTOTHEPLANEFORMED",
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWNTOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHEMAKESONEEVERYDAYANDLOSTCOUNTLONGAGOIASKWHATHE",
    "THREEWEEKSINWERISEBEFORETHESUNANDEACHNEEDLEISDONEBYNOONTHEWHITESMITHSHOWSMEHISTECHNIQUEFORPURIFYINGHISMETALBEFOREDRAWINGITINTOAFINEWIREHEHASMEREPEATTHESAMESTEPFOURTIMESWITHSLIGHTVARIATIONSSTILL"
]

full_story = "".join(pk_pts)
print(f"Total compiled PK1-PK7 narrative length: {len(full_story)} characters.")

best_rk_ioc = 0.0
best_rk_pos = 0
best_rk_mode = ""

for pos in range(len(full_story) - N + 1):
    stream = full_story[pos : pos + N]
    # Vigenere Kryptos
    pt_kr_v = "".join(KRYPTOS[(KRYPTOS.index(PK8_CT[i]) - KRYPTOS.index(stream[i]) + 26) % 26] for i in range(N))
    c = Counter(pt_kr_v)
    ioc = sum(v*(v-1) for v in c.values()) / (N * (N - 1))
    if ioc > best_rk_ioc:
        best_rk_ioc = ioc
        best_rk_pos = pos
        best_rk_mode = "Kr Vig"
        
    # Beaufort Kryptos
    pt_kr_b = "".join(KRYPTOS[(KRYPTOS.index(stream[i]) - KRYPTOS.index(PK8_CT[i]) + 26) % 26] for i in range(N))
    c = Counter(pt_kr_b)
    ioc = sum(v*(v-1) for v in c.values()) / (N * (N - 1))
    if ioc > best_rk_ioc:
        best_rk_ioc = ioc
        best_rk_pos = pos
        best_rk_mode = "Kr Beau"

print(f"Best Running Key from Narrative: IoC = {best_rk_ioc:.5f} (Mode: {best_rk_mode}, Pos: {best_rk_pos})")
