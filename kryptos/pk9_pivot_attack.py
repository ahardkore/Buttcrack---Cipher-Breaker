"""PK9 pivot attack: falsify proposed double-columnar/periodic candidates.

This is deliberately an exact test, not a language-score claim.  For each
candidate plaintext and padding layout, undo the proposed 18x8 -> 8x18
columnar permutation and derive C-P in the Kryptos alphabet.  A genuine
period-28 outer stream must match at every position; failures are recorded so
future attacks do not recycle attractive but unverified text.
"""
from pathlib import Path
import itertools

CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD"
K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
PROPOSED = "JVRMBLARDADEFUNCTORDQBOOMRBETHSKWJEREASTYMARINPRAYIALMSOISEARVEMYLAILEBOTHEEDAMESQUNGLAYIMIRLOFATSEREDCISANTIDBYOUSCHESALSOMYRELIFORESSESTIAAUON"
P2 = (7, 0, 5, 2, 4, 3, 6, 1)
P1 = (15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 8, 16, 14)

def idx(s): return [K.index(x) for x in s]
def decode_col(src, w, h, order):
    g = [0] * (w*h); q = 0
    for col in order:
        for r in range(h): g[r*w+col] = src[q]; q += 1
    return g

def test(pt):
    # encryption assumed: plaintext rows 8x18, T(18) then T(8), then Q.
    # Undo both transpositions from candidate plaintext, then compare shifts.
    x = idx(pt)
    # inverse of row-wise read after first column permutation
    # candidate is final padded plaintext; derive expected pre-T stream by applying
    # the inverse permutation convention used by the existing solver.
    mid = [x[P1[c]*8+r] for r in range(8) for c in range(18)]
    z = decode_col(mid, 8, 18, P2)
    c = idx(CT)
    shifts = [(c[i]-z[i]) % 26 for i in range(144)]
    mismatches = sum(shifts[i] != shifts[i%28] for i in range(144))
    return mismatches, shifts[:28]

if __name__ == "__main__":
    assert len(CT) == len(PROPOSED) == 144
    m, s = test(PROPOSED)
    print(f"FAIL architecture=double-columnar(18x8->8x18)+period28 mismatches={m}/144")
    print("derived_period28=" + ",".join(map(str,s)))
    print("pivot=crib-free joint search: vary both transposition permutations and keystream model")
    print("status=not a solution; no round-trip claim")
