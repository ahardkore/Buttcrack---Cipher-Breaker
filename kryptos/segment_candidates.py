import re, sys

# Load dictionary
with open("all_words.txt") as f:
    words = set(line.strip().upper() for line in f if len(line.strip()) >= 2)

print(f"Loaded {len(words)} English words.")

candidates = [
    ("Joint-20K Best (-5.2647)", "JVRMBLARDADEFUNCTORDQBOOMRBETHSKWJERSOISEARVEMYLAILEBOTHEEDAMESQUNGLAYIMELIFORESSESTIAAUONEASTYMARINPRAYIALMIRLOFATSEREDCISANTIDBYOUSCHESALSOMYR"),
    ("Joint-10K Best (-5.3277)", "PORDWINLYSHASSAMOONANISDAMYGONLYDEADWHODEMYBEGAIMMEONSHOWRGDOWSSHEADITHOURORWHEFABEANARYAFFLAMIWAPUULMASSWHOUTASTHYESNOUFWAREOFCETFQLTFEDWSTARGR"),
    ("Ultra-18x8 Seed (-5.3743)", "OJYWEVEXEMSORIESATTEAMEDFAJORWALENTSEEVETEARESHFEECESIMUNTSWETRODTESIHEBOAROWDENOEAEKSSETENTTZXVDGAMITEFLEDOOEDPEDSSIPLYIENDESHEEPDRANTENLYSOEXE"),
]

def find_all_words(text, min_len=3):
    found = []
    for i in range(len(text)):
        for l in range(min_len, min(15, len(text) - i + 1)):
            w = text[i:i+l]
            if w in words:
                found.append((i, i+l, w))
    return found

def greedy_segment(text):
    n = len(text)
    dp = [(-999999, []) for _ in range(n + 1)]
    dp[0] = (0, [])
    for i in range(n):
        if dp[i][0] == -999999:
            continue
        cur_sc, cur_toks = dp[i]
        # Option 1: single char
        if cur_sc - 8 > dp[i+1][0]:
            dp[i+1] = (cur_sc - 8, cur_toks + [text[i].lower()])
        # Option 2: dictionary word
        for l in range(2, min(16, n - i + 1)):
            w = text[i:i+l]
            if w in words:
                word_sc = cur_sc + (l * l)
                if word_sc > dp[i+l][0]:
                    dp[i+l] = (word_sc, cur_toks + [w])
    return dp[n]

for label, pt in candidates:
    print("=" * 80)
    print(f"CANDIDATE: {label}")
    print(f"Plaintext: {pt}")
    all_w = find_all_words(pt, min_len=4)
    print(f"\nAll words of length >= 4 ({len(all_w)} found):")
    # Group by unique words
    unique_words = sorted(list(set(w for _, _, w in all_w)), key=lambda x: -len(x))
    print(", ".join(unique_words[:30]))
    
    score, seg = greedy_segment(pt)
    print(f"\nGreedy Word Segmentation (Coverage Score: {score}):")
    print(" ".join(seg))
    print()
