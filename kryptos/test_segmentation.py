with open("all_words.txt") as f:
    words = set(w.strip().upper() for w in f if len(w.strip()) >= 2 and w.strip().isalpha())

print(f"Loaded {len(words)} dictionary words.")

def can_segment(s):
    n = len(s)
    dp = [False] * (n + 1)
    dp[0] = True
    for i in range(1, n + 1):
        for j in range(max(0, i - 12), i):
            if dp[j] and s[j:i] in words:
                dp[i] = True
                break
    return dp[n]

def get_segments(s):
    n = len(s)
    dp = [None] * (n + 1)
    dp[0] = []
    for i in range(1, n + 1):
        for j in range(max(0, i - 12), i):
            if dp[j] is not None and s[j:i] in words:
                dp[i] = dp[j] + [s[j:i]]
                break
    return dp[n]

# Test on a few test sentences:
print("Test 'ANSWERUNTIL':", get_segments("ANSWERUNTIL"))
print("Test 'PERFORATED':", get_segments("PERFORATED"))
print("Test 'RETAKEN':", get_segments("RETAKEN"))
