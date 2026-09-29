import math
from collections import Counter

PK9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
N = len(PK9)

def ioc(s):
    n = len(s)
    if n <= 1: return 0.0
    c = Counter(s)
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1))

def avg_slice_ioc(text, p):
    slices = [text[i::p] for i in range(p)]
    iocs = [ioc(s) for s in slices if len(s) > 1]
    return sum(iocs) / len(iocs) if iocs else 0.0

def autocorr(text, lag):
    matches = sum(1 for i in range(len(text) - lag) if text[i] == text[i + lag])
    return matches / (len(text) - lag)

print(f"PK9 Length: {N}")
print(f"Overall IoC: {ioc(PK9):.5f}")

print("\n--- Autocorrelation Peaks (Lags 1 to 72) ---")
autocorrs = [(lag, autocorr(PK9, lag)) for lag in range(1, 73)]
autocorrs.sort(key=lambda x: x[1], reverse=True)
for lag, val in autocorrs[:15]:
    print(f"Lag {lag:2d}: {val:.5f} (factor of 144: {144 % lag == 0})")

print("\n--- Slice IoC by Period (1 to 40) ---")
iocs = [(p, avg_slice_ioc(PK9, p)) for p in range(1, 41)]
iocs.sort(key=lambda x: x[1], reverse=True)
for p, val in iocs[:15]:
    print(f"Period {p:2d}: {val:.5f} (144 % p == {144 % p})")
