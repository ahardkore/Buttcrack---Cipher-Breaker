#!/usr/bin/env python3
"""Can the K2 coordinates (38deg 57min 6.5sec N / 77deg 8min 44sec W) encode
   a letter? Battery of standard numeric->letter schemes + position-index
   readings into the Kryptos texts."""

LAT = [38, 57, 6.5]
LON = [77, 8, 44]
K4 = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
      "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

def a1z26(n):  # 1..26 -> A..Z
    return chr(64 + int(n)) if 1 <= n <= 26 else None

def mod26_A1(n):
    r = int(round(n)) % 26
    return chr(64 + r) if r else "Z"

def mod26_A0(n):
    return chr(65 + int(round(n)) % 26)

def digital_root(n):
    n = int(round(n))
    while n > 26:
        n = sum(int(d) for d in str(n))
    return a1z26(n) if 1 <= n <= 26 else None

def digits(n):  # split into single digits
    return [int(d) for d in str(int(round(n)))]

print("=" * 72)
print("COORDINATES: 38deg 57min 6.5sec N / 77deg 8min 44sec W")
print("=" * 72)
seqs = {
    "deg-min-sec order (38,57,6.5,77,8,44)": LAT + LON,
    "lat only (38,57,6.5)": LAT,
    "lon only (77,8,44)": LON,
}
schemes = {
    "A1Z26 (only if 1..26)": a1z26,
    "mod 26 (A=1)": mod26_A1,
    "mod 26 (A=0)": mod26_A0,
    "digital root": digital_root,
}
for name, seq in seqs.items():
    print(f"\n{name}:")
    for sname, f in schemes.items():
        out = [f(n) for n in seq]
        print(f"  {sname:<22}: {' '.join(o if o else '?' for o in out)}")

print("\ndigit-pair readings of the raw strings '385765' / '77844':")
for s in ("385765", "77844", "38576577844"):
    pairs = [s[i:i+2] for i in range(0, len(s) - 1, 2)]
    print(f"  '{s}' -> pairs {pairs} ->",
          " ".join(a1z26(int(p)) or "?" for p in pairs))

print("\nsums: lat =", sum(LAT), " lon =", sum(LON), " total =", sum(LAT + LON))
for v in (sum(LAT), sum(LON), sum(LAT + LON)):
    print(f"  {v}: mod26(A=1)={mod26_A1(v)} mod26(A=0)={mod26_A0(v)}")

print("\n6.5 seconds x 2 =", 6.5 * 2, "->", a1z26(13), "(M)")

# ---- position-index readings -------------------------------------------
print("\n" + "=" * 72)
print("COORDINATES AS POSITIONS INTO TEXTS")
print("=" * 72)
nums = [38, 57, 65, 77, 8, 44]   # 6.5 read as 65 too
print("K4 is only 97 letters; positions 8,38,44,57,65,77 exist:")
print("  order (38,57,65,77,8,44)  ->", "".join(K4[n-1] for n in nums))
print("  order (8,38,44,57,65,77)  ->", "".join(K4[n-1] for n in sorted(nums)))
print("  reversed                  ->", "".join(K4[n-1] for n in nums[::-1]))

# ---- which letters would each scheme give? verdict ----------------------
print("\n" + "=" * 72)
print("VERDICT CHECK: does any scheme single out one letter?")
print("=" * 72)
results = {}
for n in LAT + LON:
    for sname, f in schemes.items():
        results.setdefault(sname, []).append(f(n))
for sname, letters in results.items():
    print(f"  {sname:<22}: {letters}")
print("\n(target letters from other threads: Q,U,A / S / G / E / X)")
