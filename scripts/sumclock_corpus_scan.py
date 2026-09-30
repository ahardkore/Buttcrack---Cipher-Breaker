#!/usr/bin/env python3
"""Scan a text corpus for the plaintext of a sum-clock ciphertext.

When you suspect a message's plaintext is a passage you can obtain -- a
quotation, a standard form of words, a page of a known book -- this tests that
suspicion directly instead of guessing cribs. It needs no key and does no
search: a sum-clock keystream is killed by a short linear operator, so

    L(plaintext) == L(ciphertext)

is a condition every candidate window must satisfy, checkable in four
operations. The true window satisfies every constraint; a wrong one satisfies
about one in twenty-six.

    python3 scripts/sumclock_corpus_scan.py PK8 --periods 4,5,6,7 book.txt ...

Measured at about 3.4 million letters a second, so a full-length book is a
second or two and being wrong about the book costs nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock, alphabet_for  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ciphertext", help="a name from kryptos/pk_all_ciphertexts.json, or a file")
    parser.add_argument("corpus", nargs="+", help="text files to scan")
    parser.add_argument("--periods", default="4,5,6,7", help="wheel periods (default 4,5,6,7)")
    parser.add_argument("--min-hits", type=int, default=12)
    parser.add_argument("--partial", action="store_true",
                        help="report the longest run of satisfied constraints instead of "
                             "requiring a whole-window match — use this when the plaintext "
                             "may quote only part of a passage, or the corpus is OCR")
    args = parser.parse_args()

    corpus_path = ROOT / "kryptos" / "pk_all_ciphertexts.json"
    known = json.loads(corpus_path.read_text()) if corpus_path.exists() else {}
    if args.ciphertext in known:
        ciphertext = known[args.ciphertext]
    else:
        ciphertext = Path(args.ciphertext).read_text()

    periods = [int(p) for p in args.periods.split(",")]
    cipher = SumClock()
    taps = sorted(cipher.annihilator(periods).items())
    print(f"wheel periods {periods}: annihilator taps {taps}")

    total = 0
    found = 0
    for name, alphabet in (("kryptos", KRYPTOS_ALPHABET), ("plain", alphabet_for("plain"))):
        for path in args.corpus:
            text = Path(path).read_text(errors="ignore")
            letters = sum(1 for c in text.upper() if "A" <= c <= "Z")
            total += letters
            if args.partial:
                results = cipher.scan_corpus_partial(
                    ciphertext, text, periods, alphabet, report_from=args.min_hits
                )
                for position, run, offset, window in results[:5]:
                    found += 1
                    print(f"\nHIT  {path}  position {position}  alphabet {name}  "
                          f"run of {run} consecutive constraints from offset {offset}")
                    print(f"     {window}")
                if not results:
                    print(f"  (no run of {args.min_hits}+ constraints; chance gives about 4)")
                continue
            for position, hits, window in cipher.scan_corpus(
                ciphertext, text, periods, alphabet, min_hits=args.min_hits
            ):
                found += 1
                print(f"\nHIT  {path}  position {position}  alphabet {name}  "
                      f"{hits} constraints satisfied")
                print(f"     {window}")
            print(f"scanned {path} ({name}): {letters:,} letters")
    print(f"\n{total:,} letters scanned, {found} candidate passage(s)")
    if not found:
        print("No window of this corpus can be the plaintext under that wheel shape. "
              "That rules the corpus out; it does not rule out the cipher.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
