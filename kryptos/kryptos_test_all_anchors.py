#!/usr/bin/env python3
"""KRYPTOS EXHAUSTIVE ANCHOR WORD TESTER
Tests every English word in words_alpha.txt (370,105 words) as a potential
anchor word across all positions in K4 under all surviving cipher models.
"""

import sys

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4_CT = "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"

# Artist-confirmed anchors
ANCHORS = {
    22: "E", 23: "A", 24: "S", 25: "T",
    26: "N", 27: "O", 28: "R", 29: "T", 30: "H", 31: "E", 32: "A", 33: "S", 34: "T",
    64: "B", 65: "E", 66: "R", 67: "L", 68: "I", 69: "N",
    70: "C", 71: "L", 72: "O", 73: "C", 74: "K"
}

# 1. Load dictionary
print("Loading dictionary...")
with open("words_alpha.txt") as f:
    words = [line.strip().upper() for line in f if len(line.strip()) >= 4]

print(f"Loaded {len(words)} English words of length >= 4.")

# 2. Test English words embedded in the forced 82 letters of Period 29
def check_embedded_words(forced_str, name):
    print(f"\nScanning forced text of {name} for real English words (length >= 4):")
    found = []
    # Replace dots with spaces
    chunks = forced_str.replace(".", " ").split()
    for chunk in chunks:
        for i in range(len(chunk)):
            for j in range(i + 4, len(chunk) + 1):
                sub = chunk[i:j]
                if sub in words and sub not in ["EAST", "NORTHEAST", "BERLIN", "CLOCK"]:
                    found.append((sub, i, j))
    print(f"  Found {len(found)} English words: {found[:20]}")
    return found

# 3. Exhaustive Crib-Dragging against Surviving Periods (27, 28, 29)
def test_all_words_as_anchors(period, conv="std"):
    alpha = STD if conv == "std" else KRY
    known = {}
    for pos, pt_char in ANCHORS.items():
        r = (pos - 1) % period
        sh = (alpha.index(K4_CT[pos - 1]) - alpha.index(pt_char)) % 26
        known[r] = sh
    
    missing = [r for r in range(period) if r not in known]
    print(f"\nExhaustive Crib-Drag for Period {period} ({conv}): {len(known)}/{period} residues fixed, {len(missing)} free")
    
    # Check every word of length 4..15 at every valid position
    valid_anchor_placements = []
    
    # Precompute shifts for all ct positions
    for w in words:
        w_len = len(w)
        if w_len > 15: continue # anchor words are typically <= 15
        
        for start_pos in range(1, 97 - w_len + 2):
            end_pos = start_pos + w_len - 1
            # Avoid overwriting the confirmed anchors (22-34 and 64-74)
            if not (end_pos < 22 or (start_pos > 34 and end_pos < 64) or start_pos > 74):
                continue
            
            # Check consistency with known residues
            consistent = True
            new_residues = {}
            for idx, ch in enumerate(w):
                pos = start_pos + idx
                r = (pos - 1) % period
                c = K4_CT[pos - 1]
                req_sh = (alpha.index(c) - alpha.index(ch)) % 26
                
                if r in known:
                    if known[r] != req_sh:
                        consistent = False
                        break
                elif r in new_residues:
                    if new_residues[r] != req_sh:
                        consistent = False
                        break
                else:
                    new_residues[r] = req_sh
            
            if consistent:
                valid_anchor_placements.append((w, start_pos, len(new_residues)))
                
    print(f"  Total valid anchor placements found: {len(valid_anchor_placements)}")
    return valid_anchor_placements

if __name__ == "__main__":
    # Test embedded words in forced text
    K4_STD_FORCED = "IZARVCDQWWOBNBBL.....EASTNORTHEASTCZYJFMZCBFE.....SYLJRBKCQGDFCBERLINCLOCK.....WIKAAGIMOFKAVSQEQG"
    K4_KRY_FORCED = "KSARNQAPBZDBKZEL.....EASTNORTHEASTQGUZOUAFZFE.....PSOZQUGDMGKFSBERLINCLOCK.....WQULCKEPJFYANKCAYF"
    check_embedded_words(K4_STD_FORCED, "Period 29 Standard")
    check_embedded_words(K4_KRY_FORCED, "Period 29 Tableau")
    
    # Run exhaustive crib drag for Period 29
    hits_std = test_all_words_as_anchors(29, "std")
    hits_kry = test_all_words_as_anchors(29, "kry")
