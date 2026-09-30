#!/usr/bin/env python3
"""Acceptance harness for claimed solutions to PK8 / PK9 / PK10.

The manuscript's retraction said it plainly: *fix in advance what would count
as a solution, and prefer tests a wrong answer cannot pass.*  This is that
test.  A claim passes only if ALL of the following hold:

1. **Reproduction (mechanical).**  Re-encrypting the claimed plaintext with
   the claimed family/key reproduces the canonical ciphertext exactly
   (kryptos/pk_all_ciphertexts.json, or ``--ciphertext``).  No exceptions:
   a score is not a decryption.
2. **English band.**  Quadgram log-probability per character within
   [--ENGLISH_HI, --ENGLISH_LO] (measured: railway-window English -4.05,
   documentation prose about -4.2; the retracted PK9 reading was -5.25).
3. **Dictionary coverage.**  At least 85% of letters tillable by dictionary
   words; the longest run outside any word must not exceed 12 letters --
   the test `SKWJER` and `QUNGLAYIM` fail.
4. **Non-degeneracy.**  Distinct-quadgram ratio reasonable for the length
   and no long homopolymer runs -- blocks tuning to the scorer.

Self-check (``--selftest``): synthetic instances with known keys must PASS,
a wrong-key decryption must FAIL, and the retracted PK9 reading (embedded
below) must FAIL.  If the harness ever accepts one of those, the harness,
not the puzzle, is broken.

Claim file format (JSON)::

    {
      "puzzle": "PK9",
      "plaintext": "SOMELETTERS...",
      "family": "double_columnar_28",
      "alphabet": "kryptos",            // or "az"
      "p1": [17 ints], "p2": [8 ints], "shifts": [28 ints]
    }

For "sum_clock" claims: ``"periods": [4,5,6,7], "wheels": [[...], ...]``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402

AZ_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ENGLISH_LO, ENGLISH_HI = -4.55, -3.80  # measured band; see docstring item 2
COVERAGE_MIN = 0.85
GAP_MAX = 12

#: The retracted PK9 "solution" quoted in the manuscript's retraction; the
#: harness must reject it in --selftest.
RETRACTED_PK9 = (
    "LARDADEFUNCTORDQBOOMRBETHSKWJEREASTYMARINPRAYIALMSOISEAR"
    "VEMYLAILEBOTHHEEDTHEDAMESQUENCHLAYIMIRLOFATSEAREDCISANDI"
    "DBYUSCHESALSOMYRELIEFORESSESTIA"
)


def alphabet_for(name: str) -> str:
    if name == "kryptos":
        return KRYPTOS_ALPHABET
    if name == "az":
        return AZ_ALPHABET
    raise SystemExit(f"unknown alphabet {name!r}")


def encrypt_claim(claim: dict) -> str:
    """Re-encrypt the claimed plaintext under the claimed key/model."""
    alphabet = alphabet_for(claim.get("alphabet", "kryptos"))
    index = {c: i for i, c in enumerate(alphabet)}
    try:
        plain = [index[c] for c in claim["plaintext"]]
    except KeyError as exc:
        raise SystemExit(f"plaintext letter {exc} is not in the {alphabet[:6]}... alphabet") from exc

    family = claim["family"]
    if family == "sum_clock":
        sc = SumClock()
        return sc.encrypt(
            claim["plaintext"],
            {"alphabet": claim.get("alphabet", "kryptos"),
             "periods": [int(p) for p in claim["periods"]],
             "wheels": [[int(v) for v in w] for w in claim["wheels"]]},
        )
    if family == "double_columnar_28":
        p1, p2, shifts = claim["p1"], claim["p2"], claim["shifts"]
        w1, w2 = len(p1), len(p2)
        n = len(plain)
        if n % w1 or n % w2:
            raise SystemExit("length must be a multiple of both widths")
        h1, h2 = n // w1, n // w2
        # forward transpositions: write rows, read permuted columns
        mid = [plain[r * w1 + p1[c]] for c in range(w1) for r in range(h1)]
        z = [mid[r * w2 + p2[c]] for c in range(w2) for r in range(h2)]
        return "".join(alphabet[(z[t] + shifts[t % 28]) % 26] for t in range(n))
    if family == "clock_grid":
        periods = [int(p) for p in claim["periods"]]
        wheels = [[int(v) for v in w] for w in claim["wheels"]]
        z = [(plain[t] + sum(w[t % len(w)] for w in wheels)) % 26 for t in range(len(plain))]
        if claim.get("grid"):
            gw = len(claim["grid"])
            n = len(z)
            if n % gw:
                raise SystemExit("grid width must divide the length")
            gh = n // gw
            z = [z[r * gw + claim["grid"][c]] for c in range(gw) for r in range(gh)]
        return "".join(alphabet[v] for v in z)
    raise SystemExit(f"unknown family {family!r}")


def canonical_ciphertext(puzzle: str) -> str:
    data = json.loads((ROOT / "kryptos/pk_all_ciphertexts.json").read_text())
    if puzzle not in data:
        raise SystemExit(f"unknown puzzle {puzzle!r}; known: {sorted(data)}")
    return data[puzzle]


def load_words() -> tuple[set[str], float]:
    raw = json.loads(gzip.open(ROOT / "buttcrack/data/english_words.json.gz", "rt").read())
    words = {w.upper(): v for w, v in raw.items() if w.isalpha()}
    top = max(math.log10(v) for v in words.values())
    return set(words), top


def word_coverage(text: str, words: set[str], max_len: int = 15) -> tuple[float, int]:
    """Greedy-DP: fraction of letters coverable by dictionary words, and the
    longest stretch left uncovered.  Tiling, not substring counting: a word
    only counts if it fits a consistent segmentation."""
    n = len(text)
    # dp[i] = max covered letters in text[:i]; backpointers for gap length
    dp = [0] * (n + 1)
    cover = [False] * n  # mark covered positions for gap analysis
    for i in range(1, n + 1):
        best = dp[i - 1]  # leave text[i-1] uncovered
        for ln in range(3, min(max_len, i) + 1):
            if text[i - ln : i] in words:
                best = max(best, dp[i - ln] + ln)
        dp[i] = best
    # reconstruct coverage
    i = n
    while i > 0:
        if dp[i] == dp[i - 1]:
            i -= 1
            continue
        for ln in range(3, min(max_len, i) + 1):
            if text[i - ln : i] in words and dp[i - ln] + ln == dp[i]:
                for j in range(i - ln, i):
                    cover[j] = True
                i -= ln
                break
        else:  # pragma: no cover - defensive
            i -= 1
    longest_gap = 0
    run = 0
    for c in cover:
        run = 0 if c else run + 1
        longest_gap = max(longest_gap, run)
    return dp[n] / max(n, 1), longest_gap


def degeneracy_flags(text: str) -> list[str]:
    flags = []
    quads = {text[i : i + 4] for i in range(len(text) - 3)}
    distinct_ratio = len(quads) / max(len(text) - 3, 1)
    if distinct_ratio < 0.55:
        flags.append(f"low quadgram diversity ({distinct_ratio:.2f})")
    run = 1
    for a, b in zip(text, text[1:]):
        run = run + 1 if a == b else 1
        if run > 4:
            flags.append(f"homopolymer run of {run}")
            break
    return flags


def verdicts(claim: dict) -> dict:
    model = get_model()
    text = "".join(c for c in claim["plaintext"].upper() if c.isalpha())
    out: dict = {"puzzle": claim.get("puzzle", "?"), "length": len(text), "checks": {}}

    ct_expected = claim.get("ciphertext") or canonical_ciphertext(claim["puzzle"])
    rebuilt = encrypt_claim(claim)
    out["checks"]["reproduction"] = rebuilt == ct_expected

    fit = model.ngram_score(text, 4)
    out["quadgram_per_char"] = round(fit, 4)
    out["checks"]["english_band"] = ENGLISH_LO <= fit <= ENGLISH_HI

    words, _top = load_words()
    cov, gap = word_coverage(text, words)
    out["word_coverage"] = round(cov, 4)
    out["longest_gap"] = gap
    out["checks"]["coverage"] = cov >= COVERAGE_MIN and gap <= GAP_MAX

    flags = degeneracy_flags(text)
    out["degeneracy_flags"] = flags
    out["checks"]["non_degenerate"] = not flags

    out["solved"] = all(out["checks"].values())
    return out


def selftest() -> int:
    import random

    rng = random.Random(1)
    ok = True

    # 1. a synthetic sum_clock claim with the true key must pass
    plain = (
        "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAY"
        "EXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKMUT"
    )
    periods = [4, 5, 6, 7]
    wheels = [[rng.randrange(26) for _ in range(p)] for p in periods]
    sc = SumClock()
    ct = sc.encrypt(plain, {"alphabet": "kryptos", "periods": periods, "wheels": wheels})
    claim = {"puzzle": "SYN", "plaintext": plain, "family": "sum_clock", "periods": periods,
             "wheels": wheels, "ciphertext": ct}
    v = verdicts(claim)
    print("true-key synthetic passes:", v["solved"], json.dumps(v["checks"]))
    ok &= v["solved"]

    # 2. the same claim with a wrong key must fail reproduction
    bad = dict(claim)
    bad = {**claim, "wheels": [[(x + 1) % 26 for x in w] for w in wheels]}
    v2 = verdicts(bad)
    print("wrong-key synthetic passes:", v2["solved"], json.dumps(v2["checks"]))
    ok &= not v2["solved"]

    # 3. the retracted PK9 reading must fail the language gates (identity N/A)
    retracted_claim = {"puzzle": "PK9", "plaintext": RETRACTED_PK9, "family": "sum_clock",
                       "periods": [4], "wheels": [[0] * 4], "ciphertext": "X" * len(RETRACTED_PK9)}
    v3 = verdicts(retracted_claim)
    print("retracted PK9 reading passes:", v3["solved"],
          f"(fit {v3['quadgram_per_char']}, cov {v3['word_coverage']}, gap {v3['longest_gap']})")
    ok &= not v3["solved"]

    print("SELFTEST:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("claim", nargs="?", help="JSON claim file (or '-' for stdin)")
    ap.add_argument("--ciphertext", help="override the canonical ciphertext")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.claim:
        ap.error("a claim file is required unless --selftest")
    raw = sys.stdin.read() if args.claim == "-" else Path(args.claim).read_text()
    claim = json.loads(raw)
    if args.ciphertext:
        claim["ciphertext"] = args.ciphertext
    out = verdicts(claim)
    print(json.dumps(out, indent=2))
    return 0 if out["solved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
