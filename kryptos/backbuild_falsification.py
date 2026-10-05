#!/usr/bin/env python3
"""KRYPTOS K4 — CAN WE BACK-BUILD A CIPHER TO PROVE THE PLAINTEXT?

Short answer: no, and this script shows why in two independent ways.

PART 1 — the architecture is falsified, not merely unproven.
    The proposed mechanism (a substitution "card" per lane, indexed by the
    physical helper letter, plus a one-bit gate) imposes constraints that do
    not depend on which plaintext you choose. Wherever two positions share a
    lane AND a helper letter they share a card value, so their shifts may
    differ by at most the gate: -1, 0, or +1.

    There are 15 such forced pairs. Our plaintext satisfies 1. Random strings
    average 1.73. The architecture does not merely fail to prove the
    plaintext -- the plaintext actively contradicts the architecture.

PART 2 — even a back-build that DID fit would prove nothing.
    Any plaintext can be fitted by widening the mechanism. The question is
    whether the mechanism costs fewer bits to describe than the thing it
    explains. It does not, by a wide margin. A model more expensive than its
    output is a restatement of the data, not an explanation of it.

Run:  python3 kryptos/backbuild_falsification.py
"""

from __future__ import annotations

import math
import random
import statistics
import string

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

K4_PT = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
         "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")

HELPER_T = ("WXZK"
            "YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR"
            "ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY"
            "_ABCDEFGHIJKLMNOPQRSTUVWXYZABCD")

#: 24 of 97 letters are artist-confirmed; the rest were chosen by the author
#: of the reconstruction.
ANCHOR_POSITIONS = set(range(21, 34)) | set(range(63, 74))
FREE_POSITIONS = [i for i in range(97) if i not in ANCHOR_POSITIONS]

TRIALS = 100_000


def lane(i: int) -> int:
    """Physical row: 25, 26, 27, 28 -> 0, 1, 2, 3."""
    return 0 if i < 4 else 1 if i < 35 else 2 if i < 66 else 3


def shifts(plaintext: str) -> list[int]:
    return [(ord(c) - ord(p)) % 26 for c, p in zip(K4_CT, plaintext)]


def forced_pairs() -> list[tuple[int, int]]:
    """Position pairs sharing a lane and a helper letter -> same card value."""
    groups: dict[tuple[int, str], list[int]] = {}
    for i in range(97):
        if HELPER_T[i].isalpha():
            groups.setdefault((lane(i), HELPER_T[i]), []).append(i)
    return [(g[a], g[b])
            for g in groups.values() if len(g) > 1
            for a in range(len(g)) for b in range(a + 1, len(g))]


def met(plaintext: str, pairs: list[tuple[int, int]]) -> int:
    r = shifts(plaintext)
    return sum(1 for i, j in pairs if (r[i] - r[j]) % 26 in (0, 1, 25))


def part1() -> None:
    print("=" * 78)
    print(" PART 1  Is the proposed architecture even consistent with our plaintext?")
    print("=" * 78)
    pairs = forced_pairs()
    n = len(pairs)
    ours = met(K4_PT, pairs)

    print(f"\n  Forced constraint pairs implied by the card-plus-gate design: {n}")
    print("  (same lane + same helper letter => same card value => shifts differ by <=1)\n")

    rng = random.Random(1990)
    scores = [met("".join(rng.choice(string.ascii_uppercase) for _ in range(97)), pairs)
              for _ in range(TRIALS)]

    print(f"  {'our claimed K4 plaintext':<36} {ours:>3}/{n}")
    print(f"  {'random strings, mean':<36} {statistics.mean(scores):>6.2f}/{n}")
    print(f"  {'random strings, best of ' + f'{TRIALS:,}':<36} {max(scores):>3}/{n}")

    better = sum(1 for s in scores if s >= ours) / TRIALS
    print(f"\n  Random strings scoring at least as well as ours: {better:.1%}")
    print(f"  Per-pair rate -- chance 3/26 = {3/26:.3f}, ours = {ours/n:.3f}")
    print("\n  -> Our plaintext performs WORSE than chance against the very architecture")
    print("     that was invented to explain it. The card-plus-gate model is falsified,")
    print("     not merely unproven. No back-build of that shape exists.")


def part2() -> None:
    print()
    print("=" * 78)
    print(" PART 2  Suppose we widen the mechanism until it does fit. What is proved?")
    print("=" * 78)

    bits_per_letter = math.log2(26)

    print("\n  Any plaintext can be fitted by allowing one free shift per position.")
    print("  Demonstration -- back-build a per-position keystream for a silly plaintext:\n")

    joke = "MYHOVERCRAFTISFULLOFEELSANDTHEWEASELHASEATENTHETRANSMITTERPLEASESENDBISCUITSANDAMAPOFBERLINATONCEX"[:97]
    for label, pt in (("our claimed plaintext", K4_PT), ("a deliberate absurdity", joke)):
        key = [(ord(K4_CT[i]) - ord(pt[i])) % 26 for i in range(97)]
        rebuilt = "".join(chr((ord(pt[i]) - 65 + key[i]) % 26 + 65) for i in range(97))
        print(f"    {label:<24} forward re-encryption matches K4: {rebuilt == K4_CT}  (97/97)")

    print("\n  Both 'verify' perfectly. A method that certifies every answer certifies none.\n")

    print("  MDL accounting -- what a model costs versus what it explains:\n")
    model_costs = [
        ("per-position keystream (the trivial back-build)", 97 * bits_per_letter),
        ("4 helper cards (4 x 26 entries) + 97 gate bits", 4 * 26 * bits_per_letter + 97),
    ]
    explained = [
        ("the 73 non-anchor letters, uniform over 26", len(FREE_POSITIONS) * bits_per_letter),
        ("the 73 non-anchor letters, English ~1.5 b/char", len(FREE_POSITIONS) * 1.5),
    ]
    for label, bits in model_costs:
        print(f"    cost to specify   {label:<48} {bits:>7.0f} bits")
    print()
    for label, bits in explained:
        print(f"    content explained {label:<48} {bits:>7.0f} bits")

    cheapest = min(b for _, b in model_costs)
    dearest = max(b for _, b in explained)
    print(f"\n  Cheapest model {cheapest:.0f} bits vs most generous content estimate {dearest:.0f} bits.")
    print(f"  Net compression: {dearest - cheapest:+.0f} bits.")
    print("\n  -> Negative. The mechanism is more expensive to state than the plaintext it")
    print("     recovers, so it carries no explanatory content. This is the formal version")
    print("     of 'you can always back-build a cipher'.")


def part3() -> None:
    print()
    print("=" * 78)
    print(" WHAT WOULD ACTUALLY CONSTITUTE PROOF")
    print("=" * 78)
    print("""
  A back-build proves something only if the mechanism is pinned down WITHOUT
  reference to the plaintext. Concretely, all three must hold:

    1. Every constant -- cards, gate map, lane assignment, traversal order --
       is derived from public data only: the sculpture's geometry, the carved
       tableau, Sanborn's published clues. No value fitted to the output.
    2. The full specification is published and timestamped BEFORE the decode
       is run, so the degrees of freedom cannot be adjusted afterwards.
    3. Run forward from ciphertext alone, it emits readable English, and the
       four artist-confirmed anchors fall out unforced at 22-25, 26-34,
       64-69, 70-74 having never been used as inputs.

  Condition 3 is the one that carries the evidence: 24 anchor letters landing
  correctly by accident is roughly 26^-24, about 1 in 10^34. A mechanism that
  achieves that without being told the anchors has genuinely proved itself.

  The existing model fails condition 1 -- its cards are back-solved from the
  plaintext -- which is exactly why it can reproduce 97/97 and still mean
  nothing. And per Part 1, the published card-plus-gate shape is contradicted
  by the plaintext outright.

  The two honest routes forward:
    (a) Derive the cards from the sculpture alone, publish, then decode blind.
    (b) Submit the string to Paradigm's portal and record the answer.

  Only (b) is available today, and it returns one bit: yes or no.
""")


if __name__ == "__main__":
    print("KRYPTOS K4 — BACK-BUILD FALSIFICATION\n")
    part1()
    part2()
    part3()
