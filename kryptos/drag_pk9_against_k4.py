# Exhaustive Cross-Cipher Crib Dragging: PK9 Core Plaintext vs K4 (N = 97)
import math
from collections import Counter

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
print("==========================================================================================")
print("             PK9 CORE PLAINTEXT VS K4 (97 CHARACTERS) CRIB DRAG                           ")
print("==========================================================================================\n")
print(f"K4 Ciphertext (N = {len(K4_CT)}): {K4_CT}")

pk9_core = "LARDADEFUNCTORDQBOOMRBETHSKWJEREASTYMARINPRAYIALMSOISEARVEMYLAILEBOTHEEDAMESQUNGLAYIMIRLOFATSEREDCISANTIDBYOUSCHESALSOMYRELIFORESSESTIA"
print(f"PK9 Core Plaintext (N = {len(pk9_core)}): {pk9_core}\n")

# Confirmed K4 anchors:
# Pos 22..25: EAST (CT: FLRV)
# Pos 26..34: NORTHEAST (CT: QQPRNGKSS)
# Pos 64..69: BERLIN (CT: NYPVTT)
# Pos 70..74: CLOCK (CT: MZFPK)

print("--- 1. Evaluating PK9 Core as a Running Key against K4 across all Offsets ---")
best_ioc_std = 0.0
best_ioc_kr = 0.0
best_off_std = 0
best_off_kr = 0

for offset in range(len(pk9_core)):
    # Standard alphabet
    pt_std_vig = []
    pt_std_beau = []
    # Kryptos alphabet
    pt_kr_vig = []
    pt_kr_beau = []
    
    for i in range(len(K4_CT)):
        kchar = pk9_core[(i + offset) % len(pk9_core)]
        
        # Standard
        c_std = ord(K4_CT[i]) - ord("A")
        k_std = ord(kchar) - ord("A")
        pt_std_vig.append(STANDARD[(c_std - k_std + 26) % 26])
        pt_std_beau.append(STANDARD[(k_std - c_std + 26) % 26])
        
        # Kryptos
        c_kr = KRYPTOS.index(K4_CT[i])
        k_kr = KRYPTOS.index(kchar)
        pt_kr_vig.append(KRYPTOS[(c_kr - k_kr + 26) % 26])
        pt_kr_beau.append(KRYPTOS[(k_kr - c_kr + 26) % 26])
        
    for name, stream in [("Std Vig", "".join(pt_std_vig)), ("Std Beau", "".join(pt_std_beau))]:
        c = Counter(stream)
        ioc = sum(v*(v-1) for v in c.values()) / (len(stream)*(len(stream)-1))
        if ioc > best_ioc_std:
            best_ioc_std = ioc
            best_off_std = (offset, name)
            
    for name, stream in [("Kr Vig", "".join(pt_kr_vig)), ("Kr Beau", "".join(pt_kr_beau))]:
        c = Counter(stream)
        ioc = sum(v*(v-1) for v in c.values()) / (len(stream)*(len(stream)-1))
        if ioc > best_ioc_kr:
            best_ioc_kr = ioc
            best_off_kr = (offset, name)

print(f"Best Standard Running Key: IoC = {best_ioc_std:.5f} (Offset {best_off_std[0]}, Mode: {best_off_std[1]})")
print(f"Best Kryptos Running Key:  IoC = {best_ioc_kr:.5f} (Offset {best_off_kr[0]}, Mode: {best_off_kr[1]})\n")

# 2. Crib Dragging of PK9 Phrases across K4
print("--- 2. Dragging Individual PK9 Words / Phrases across K4 ---")
cribs = [
    "LARD", "DEFUNCT", "BOOM", "SKEWER", "SKWJER", "EAST", "MARIN",
    "PRAY", "ALMS", "SEAR", "DAMES", "QUENCH", "FAT", "SERED", "RELIEF",
    "ORES", "SESTIA"
]

print("Scanning for positions where a PK9 crib produces an English key fragment on K4:")
valid_key_fragments = []
for crib in cribs:
    L = len(crib)
    for pos in range(len(K4_CT) - L + 1):
        # Derive key fragment: key = CT - PT
        key_std = "".join(STANDARD[(ord(K4_CT[pos+k]) - ord(crib[k]) + 26) % 26] for k in range(L))
        key_kr  = "".join(KRYPTOS[(KRYPTOS.index(K4_CT[pos+k]) - KRYPTOS.index(crib[k]) + 26) % 26] for k in range(L))
        
        # Check if key fragment is formable or meaningful
        for kw in ["KRYPTOS", "SANBORN", "SCHEIDT", "BERLIN", "CLOCK", "EAST", "NORTH"]:
            if kw in key_std or kw in key_kr:
                valid_key_fragments.append((crib, pos, kw, "direct"))
            if kw[:L] == key_std or kw[:L] == key_kr:
                valid_key_fragments.append((crib, pos, kw, "prefix"))

print(f"Meaningful key fragment intersections found: {len(valid_key_fragments)}")
if valid_key_fragments:
    for f in valid_key_fragments[:15]:
        print(f"  Crib \"{f[0]}\" at K4 pos {f[1]}: generates key matching \"{f[2]}\" ({f[3]})")
else:
    print("  No direct dictionary keyword overlaps detected between PK9 cribs and K4 ciphertext.")

# 3. EAST Anchor Consistency Check
print("\n--- 3. EAST Anchor Consistency Check ---")
print("In K4: Pos 22..25 is \"FLRV\" -> Decrypts to \"EAST\"")
k4_east_ct = K4_CT[22:26]
key_east_std = "".join(STANDARD[(ord(k4_east_ct[k]) - ord("EAST"[k]) + 26) % 26] for k in range(4))
key_east_kr  = "".join(KRYPTOS[(KRYPTOS.index(k4_east_ct[k]) - KRYPTOS.index("EAST"[k]) + 26) % 26] for k in range(4))
print(f"K4 EAST Key (Standard): {key_east_std}")
print(f"K4 EAST Key (Kryptos):  {key_east_kr}")

# Does this key fragment appear in PK9?
print(f"Does key \"{key_east_std}\" appear in PK9? {key_east_std in pk9_core}")
print(f"Does key \"{key_east_kr}\" appear in PK9? {key_east_kr in pk9_core}")
