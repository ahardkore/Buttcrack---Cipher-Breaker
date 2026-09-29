#!/usr/bin/env python3
"""PARADIGM KRYPTOS CTF - ADVANCED ATTACK SUITE FOR PK9 & PK10
Tools for structural periodicity mapping, matrix factoring, and state-machine search.
"""

import json
from collections import Counter
import math

with open("pk_all_ciphertexts.json") as f:
    cts = json.load(f)

ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def compute_ioc(text):
    n = len(text)
    if n <= 1:
        return 0.0
    cnt = Counter(text)
    return sum(c * (c - 1) for c in cnt.values()) / (n * (n - 1))

def autocorrelation(text, max_lag=50):
    n = len(text)
    lags = {}
    for lag in range(1, min(max_lag + 1, n)):
        matches = sum(1 for i in range(n - lag) if text[i] == text[i + lag])
        expected = (n - lag) / 26.0
        lags[lag] = matches / expected
    return lags

print("=" * 70)
print("PK9 (144 characters) STRUCTURAL PROFILE")
print("=" * 70)
pk9 = cts["PK9"]
print(f"Overall IoC: {compute_ioc(pk9):.5f}")
pk9_lags = autocorrelation(pk9, 35)
print("Autocorrelation peaks (> 1.3x expected):")
for lag, ratio in sorted(pk9_lags.items(), key=lambda x: x[1], reverse=True)[:8]:
    if ratio > 1.2:
        print(f"  Lag {lag:2d}: {ratio:.2f}x expected (matches: {int(ratio * (len(pk9)-lag)/26)})")

print("\n" + "=" * 70)
print("PK10 (504 characters) STRUCTURAL PROFILE")
print("=" * 70)
pk10 = cts["PK10"]
print(f"Overall IoC: {compute_ioc(pk10):.5f}")
pk10_lags = autocorrelation(pk10, 45)
print("Autocorrelation peaks (> 1.3x expected):")
for lag, ratio in sorted(pk10_lags.items(), key=lambda x: x[1], reverse=True)[:8]:
    if ratio > 1.2:
        print(f"  Lag {lag:2d}: {ratio:.2f}x expected")
