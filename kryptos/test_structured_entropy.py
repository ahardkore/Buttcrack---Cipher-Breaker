ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
q7_base = [0, 2, 9, 23, 23, 6, 20]

# 1. Test arithmetic progression / LCG: q[i] = (a * i + b) mod 26
print("--- 1. Testing LCG / Affine: q[i] = (a * i + b) mod 26 ---")
for a in range(26):
    for b in range(26):
        cand = [(a * i + b) % 26 for i in range(7)]
        diff = [(cand[i] - q7_base[i]) % 26 for i in range(7)]
        if len(set(diff)) == 1:
            print(f"Affine match! a={a}, b={b}, const_shift={diff[0]}")

# 2. Check if differences match any 7-gram in Kryptos texts or Theophilus
k1_pt = "BETWEENSUBTLESHADINGANDTHEABSENCEOFLIGHTLIESTHENUANCEOFIQLUSION"
k2_pt = "ITWASTOTALLYINVISIBLEHOWSTHATPOSSIBLETHEYUSEDTHEEARTHSMAGNETICFIELDXTHEINFORMATIONWASGATHEREDANDTRANSMITTEDUNDERGRUUNDTOANUNKNOWNLOCATIONXDOESLANGLEYKNOWABOUTTHISTHEYSHOULDITSBURIEDOUTTHERESOMEWHEREXWHOKNOWSTHEEXACTLOCATIONONLYWWTHISWASHISLASTMESSAGEXTHIRTYEIGHTDEGREESFIFTYSEVENMINUTESSIXPOINTFIVESECONDSNORTHSEVENTYSEVEMDEGREESEIGHTMINUTESFORTYFOURSECONDSWESTIDBYROWS"
k3_pt = "SLOWLYDESPARATLYSLOWLYREMAINSASSAGEDEBRISTHATENCUMBEREDTHELOWERPARTOFTHEDOORWAYWASREMOVEDWITHTREMBLEINGHANDSIMADEATINYBREACHINTHEUPPERLEFTHANDCORNERANDTHENWIDENINGTHEHOLEALITTLEIINSERTEDTHECANDLEANDPEEREDINTHETSHWOTAIRSCONTAININGTOTOALLEYEDISPLACEDCANDLEFLAMEANDREVEALEDTHECHASMCLOSURESCATTYPICSGANGWAYSANDCHAMBERSEVERYWHERETHESPARKLEOFMETAL"

texts = {
    "K1_PT": k1_pt,
    "K2_PT": k2_pt,
    "K3_PT": k3_pt,
}

# Add Theophilus text
with open("theophilus_hendrie.txt", "r", errors="ignore") as f:
    theo = "".join(c.upper() for c in f.read() if c.isalpha())
texts["THEOPHILUS"] = theo[:50000]

print("\n--- 2. Testing Substring in Corpora ---")
for name, txt in texts.items():
    txt_kr = [ALPH.index(c) for c in txt if c in ALPH]
    txt_std = [ord(c) - ord('A') for c in txt if c.isalpha()]
    
    # Check Kr
    for i in range(len(txt_kr) - 7):
        sub = txt_kr[i:i+7]
        diff = [(sub[j] - q7_base[j]) % 26 for j in range(7)]
        if len(set(diff)) == 1:
            print(f"MATCH in {name} (Kryptos alph) at pos {i}: {txt[i:i+7]} (shift={diff[0]})")
            
    # Check Std
    for i in range(len(txt_std) - 7):
        sub = txt_std[i:i+7]
        diff = [(sub[j] - q7_base[j]) % 26 for j in range(7)]
        if len(set(diff)) == 1:
            print(f"MATCH in {name} (Std alph) at pos {i}: {txt[i:i+7]} (shift={diff[0]})")

