"""Import practicalcryptography-format n-gram tables as packaged language models.

Buttcrack ships letter n-gram tables for six languages.  The English model is
built from PyPI sources by ``build_language_model.py``; the other five
(french, german, italian, latin, spanish) are imported from the n-gram count
files published by James Lyons at practicalcryptography.com (counts distilled
from Wortschatz corpora), in the plain ``GRAM COUNT`` text format::

    THAT 17822
    THER 17557
    ...

Usage::

    # directory holding {language}_{bigrams,trigrams,quadgrams}.txt
    python3 scripts/import_ngram_tables.py /path/to/ngram/files

What it does
------------
* re-exports each table gzipped into ``buttcrack/data/`` (bigrams and
  trigrams are kept because the model falls back to them on very short text,
  and bigrams feed the per-language letter distribution used by chi-squared);
* verifies every gram is A-Z and every count is a positive integer, dropping
  anything that is not (the German source, for instance, carries umlaut grams
  that the A-Z cipher pipeline could never match);
* measures each table's self-entropy and derives the fitness thresholds for
  :mod:`buttcrack.lang` (see the calibration note in that module), writing the
  numbers into ``model_meta.json`` next to the English build's provenance so
  the thresholds in the code can be checked against the data that produced
  them.

The files this script consumes are the set attached to the feature request:
english/french/german/italian/latin/spanish monograms..quadgrams plus English
quintgrams/hexagrams (from the mirror at github.com/0xdiid/buttcrack, MIT).
Only bigrams/trigrams/quadgrams of the five non-English languages are shipped:
English keeps its larger, dictionary-equipped model, and the higher English
orders are unused because every scoring threshold in the codebase is measured
at order 4.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "buttcrack" / "data"

ORDERS = {"bigrams": 2, "trigrams": 3, "quadgrams": 4}
LANGUAGES = ("french", "german", "italian", "latin", "spanish")

#: The fitness ramp thresholds are derived from each table's self-entropy
#: H = sum p*log10(p), using the relationship measured on the shipped English
#: model (H = -4.161; measured FITNESS_GOOD = -4.30, i.e. GOOD = H - 0.14, and
#: a good-to-bad spread of 1.90 -- see buttcrack/lang.py and
#: scripts/calibrate_scoring.py).  Measured against real text samples in six
#: languages, these thresholds put native text at 0.8-1.0 confidence and
#: foreign text below 0.6, which is what the solver's SOLVED bar needs.
GOOD_MARGIN = 0.14
SPREAD = 1.90


def read_table(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    dropped = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            gram, _, count = line.partition(" ")
            count = count.strip()
            if not gram or not count.isdigit() or not all("A" <= c <= "Z" for c in gram):
                dropped += 1
                continue
            counts[gram] = int(count)
    if dropped:
        print(f"  dropped {dropped} non-A-Z or malformed lines from {path.name}")
    return counts


def self_entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    return sum((c / total) * math.log10(c / total) for c in counts.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="directory of {language}_{order}grams.txt files")
    parser.add_argument("--dry-run", action="store_true", help="measure only; write nothing")
    args = parser.parse_args()

    meta_path = DATA / "model_meta.json"
    meta = json.loads(meta_path.read_text())
    languages_meta = dict(meta.get("languages", {}))

    for language in LANGUAGES:
        entry: dict = {
            "generator": "scripts/import_ngram_tables.py",
            "source": (
                "n-gram counts from practicalcryptography.com (James Lyons), "
                "Wortschatz corpora, via the github.com/0xdiid/buttcrack mirror (MIT)"
            ),
        }
        for name, _order in ORDERS.items():
            path = args.source / f"{language}_{name}.txt"
            if not path.is_file():
                print(f"{language}: missing {path}", file=sys.stderr)
                return 1
            counts = read_table(path)
            if not counts:
                print(f"{language}: {path} yielded no usable counts", file=sys.stderr)
                return 1
            total = sum(counts.values())
            entry[f"{name[:-1]}s_distinct"] = len(counts)
            entry[f"{name[:-1]}s_total"] = total
            if not args.dry_run:
                out = DATA / f"{language}_{name}.txt.gz"
                with gzip.open(out, "wt", encoding="ascii", compresslevel=9) as fh:
                    for gram, count in counts.items():
                        fh.write(f"{gram} {count}\n")
            if name == "quadgrams":
                entropy = self_entropy(counts)
                good = entropy - GOOD_MARGIN
                entry["quadgram_self_entropy"] = round(entropy, 3)
                entry["fitness_good"] = round(good, 2)
                entry["fitness_bad"] = round(good - SPREAD, 2)
                print(
                    f"{language:8s} {name}: {len(counts):6d} grams, total {total:11,d}, "
                    f"H={entropy:.3f} -> fitness ramp [{good:.2f}, {good - SPREAD:.2f}]"
                )
        languages_meta[language] = entry

    if not args.dry_run:
        meta["languages"] = languages_meta
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
        print(f"updated {meta_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
