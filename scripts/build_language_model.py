#!/usr/bin/env python3
"""Build the English statistical language model shipped with Buttcrack.

Buttcrack scores candidate plaintexts with letter n-gram statistics.  Good
statistics are the difference between "cracks in two seconds" and "cracks by
luck", so this script derives them from real usage data instead of guessing.

Sources (both fetched from PyPI, both permissively licensed -- see NOTICE):

* ``wordsegment`` (Apache-2.0) ships Peter Norvig's unigram/bigram frequency
  lists, which are derived from the Google Web 1T corpus.  ~333k words with
  counts and ~286k word bigrams with counts.
* ``pyspellchecker`` (MIT) ships a word -> frequency dictionary used to build
  the dictionary scorer.

Method
------
A letter n-gram model built by counting inside isolated words is useless for
cryptanalysis, because ciphertext is usually stripped of spaces: most of the
interesting n-grams straddle word boundaries.  So instead of counting words in
isolation we synthesise a corpus:

1. Keep the most frequent alphabetic words (default: count >= 50_000).
2. Build a word-bigram successor table for the head vocabulary so that common
   transitions ("of" -> "the", "in" -> "a") occur at realistic rates.
3. Sample ``--words`` words from a Markov chain that follows the bigram table
   with probability ``--bigram-p`` and the unigram distribution otherwise.
4. Strip spaces, uppercase, and count letter 2/3/4-grams over the stream.

The result is an i.i.d.-word-with-bigram-correction model of continuous
English letters -- exactly the distribution classical cryptanalysis assumes.

Usage
-----
    python3 scripts/build_language_model.py --fetch      # download sources
    python3 scripts/build_language_model.py --source /tmp/langsrc
    python3 scripts/build_language_model.py --words 6000000 --order 5

Output: ``buttcrack/data/english_ngrams_*.txt.gz`` + ``english_words.json.gz``
+ ``model_meta.json``.  Deterministic for a fixed ``--seed``.
"""

from __future__ import annotations

import argparse
import bisect
import gzip
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from itertools import accumulate
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "buttcrack" / "data"

SOURCE_PACKAGES = {
    "wordsegment": "wordsegment==1.3.1",
    "pyspellchecker": "pyspellchecker==0.9.0",
}


# --------------------------------------------------------------------------- #
# source acquisition
# --------------------------------------------------------------------------- #
def fetch_sources(dest: Path) -> Path:
    """Download the source wheels from PyPI and extract the data files."""
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, "-m", "pip", "download", "--no-deps", "-d", tmp]
        cmd += list(SOURCE_PACKAGES.values())
        print("$", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
        for wheel in sorted(Path(tmp).glob("*.whl")):
            print(f"  unpacking {wheel.name}")
            with zipfile.ZipFile(wheel) as zf:
                for member in zf.namelist():
                    base = os.path.basename(member)
                    if base in {"unigrams.txt", "bigrams.txt", "en.json.gz"}:
                        with zf.open(member) as src, open(dest / base, "wb") as out:
                            shutil.copyfileobj(src, out)
                        print(f"    -> {base}")
    missing = [f for f in ("unigrams.txt", "bigrams.txt", "en.json.gz") if not (dest / f).exists()]
    if missing:
        raise SystemExit(f"missing source files after fetch: {missing}")
    return dest


# --------------------------------------------------------------------------- #
# vocabulary
# --------------------------------------------------------------------------- #
def load_unigrams(path: Path, min_count: int, max_words: int) -> list[tuple[str, int]]:
    """Return [(word, count)] for clean lowercase alphabetic words."""
    entries: list[tuple[str, int]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            word = parts[0].strip()
            try:
                freq = int(parts[1])
            except ValueError:
                continue
            if freq < min_count:
                continue
            if not (1 <= len(word) <= 16):
                continue
            if not word.isalpha() or not word.islower() or not word.isascii():
                continue
            entries.append((word, freq))
    entries.sort(key=lambda kv: kv[1], reverse=True)
    return entries[:max_words]


def load_bigrams(
    path: Path, ranked_vocab: list[str], head_limit: int, per_word: int
) -> dict[str, list[tuple[str, int]]]:
    """Successor table: word -> [(next_word, count)] for the head vocabulary.

    ``ranked_vocab`` is frequency-ordered; only its first ``head_limit`` words
    get a successor table (they cover the overwhelming majority of transitions).
    """
    vocab = set(ranked_vocab)
    heads = set(ranked_vocab[:head_limit]) if head_limit else vocab
    raw: dict[str, list[tuple[str, int]]] = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            phrase, count_s = parts
            try:
                count = int(count_s)
            except ValueError:
                continue
            words = phrase.split()
            if len(words) != 2:
                continue
            a, b = words[0].lower(), words[1].lower()
            if a not in heads or b not in vocab or a == b:
                continue
            raw[a].append((b, count))
    table: dict[str, list[tuple[str, int]]] = {}
    for word, succ in raw.items():
        succ.sort(key=lambda kv: kv[1], reverse=True)
        table[word] = succ[:per_word]
    return table


# --------------------------------------------------------------------------- #
# corpus synthesis
# --------------------------------------------------------------------------- #
class _Sampler:
    """Fast weighted sampler using bisect over a cumulative distribution."""

    __slots__ = ("items", "cum", "total", "_rand")

    def __init__(self, items: list[str], weights: list[float], rng: random.Random):
        self.items = items
        total = float(sum(weights))
        self.cum = list(accumulate(weights))
        self.total = total
        self._rand = rng.random

    def choice(self) -> str:
        return self.items[bisect.bisect_left(self.cum, self._rand() * self.total)]


def synthesise_corpus(
    unigrams: list[tuple[str, int]],
    bigrams: dict[str, list[tuple[str, int]]],
    n_words: int,
    bigram_p: float,
    seed: int,
    progress: bool = True,
) -> str:
    """Generate a pseudo-corpus of ``n_words`` English words."""
    rng = random.Random(seed)
    words = [w for w, _ in unigrams]
    weights = [float(c) for _, c in unigrams]
    uni = _Sampler(words, weights, rng)
    succ_samplers = {
        head: _Sampler([w for w, _ in succ], [float(c) for _, c in succ], rng)
        for head, succ in bigrams.items()
    }
    out: list[str] = []
    append = out.append
    cur = uni.choice()
    append(cur)
    rand = rng.random
    started = time.time()
    for i in range(n_words):
        sampler = succ_samplers.get(cur)
        if sampler is not None and rand() < bigram_p:
            cur = sampler.choice()
        else:
            cur = uni.choice()
        append(cur)
        if progress and i and i % 500_000 == 0:
            rate = i / max(time.time() - started, 1e-9)
            print(f"    sampled {i:,} words ({rate:,.0f} words/s)", flush=True)
    return " ".join(out)


def count_ngrams(stream: str, order: int) -> dict[int, dict[str, int]]:
    """Count letter n-grams for every order in 2..order over ``stream``.

    Only the highest order is counted by scanning the stream; the lower orders
    are derived from it by marginalisation (a trigram's count is the sum of the
    counts of the quadgrams that start with it).  Deriving is exact up to the
    final ``order - n`` positions of the stream and costs a third of the time.
    """
    buf = stream.encode("ascii")
    length = len(buf)
    top: dict[bytes, int] = defaultdict(int)
    for i in range(length - order + 1):
        top[buf[i : i + order]] += 1
    counts: dict[int, dict[str, int]] = {order: {k.decode(): v for k, v in top.items()}}
    for n in range(order - 1, 1, -1):
        derived: dict[str, int] = defaultdict(int)
        for gram, count in counts[n + 1].items():
            derived[gram[:n]] += count
        counts[n] = dict(derived)
    return {n: counts[n] for n in sorted(counts)}


# --------------------------------------------------------------------------- #
# writers
# --------------------------------------------------------------------------- #
def write_ngrams(path: Path, counts: dict[str, int]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    with gzip.open(path, "wt", encoding="ascii", compresslevel=9) as fh:
        for gram, count in items:
            fh.write(f"{gram} {count}\n")
    return len(items)


def write_dictionary(path: Path, freq: dict[str, int]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(freq, fh, separators=(",", ":"), sort_keys=True)
    return len(freq)


def build_dictionary(en_json: Path, unigrams: list[tuple[str, int]], max_words: int) -> dict[str, int]:
    """Merge pyspellchecker's dictionary with the corpus unigram counts."""
    with gzip.open(en_json, "rt", encoding="utf-8") as fh:
        raw = json.load(fh)
    merged: dict[str, int] = {}
    for word, count in raw.items():
        w = word.lower()
        # Single letters are kept on purpose: the Viterbi segmentation needs
        # "a" and "i" as legal words or it mangles every sentence.
        if not (1 <= len(w) <= 24) or not w.isalpha() or not w.isascii():
            continue
        merged[w] = max(int(count), 1)
    for word, count in unigrams:
        merged[word] = max(merged.get(word, 0), count)
    ranked = sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))[:max_words]
    return dict(ranked)


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, help="directory holding unigrams.txt, bigrams.txt, en.json.gz")
    ap.add_argument("--fetch", action="store_true", help="download sources from PyPI into --source (or a temp dir)")
    ap.add_argument("--out", type=Path, default=DATA_DIR, help="output directory (default: buttcrack/data)")
    ap.add_argument("--words", type=int, default=5_000_000, help="words to sample into the synthetic corpus")
    ap.add_argument("--order", type=int, default=4, help="highest n-gram order to count (default 4)")
    ap.add_argument("--min-count", type=int, default=50_000, help="minimum unigram corpus count to keep")
    ap.add_argument("--max-words", type=int, default=150_000, help="vocabulary ceiling")
    ap.add_argument("--bigram-p", type=float, default=0.5, help="probability of following the word-bigram table")
    ap.add_argument("--head-limit", type=int, default=20_000, help="bigram successor tables for the N most common words")
    ap.add_argument("--per-word", type=int, default=64, help="successors to keep per head word")
    ap.add_argument("--dict-words", type=int, default=80_000, help="dictionary size to ship")
    ap.add_argument("--seed", type=int, default=20260923, help="RNG seed (deterministic output)")
    args = ap.parse_args(argv)

    source = args.source
    if args.fetch or source is None:
        target = source or Path(tempfile.mkdtemp(prefix="buttcrack-langsrc-"))
        print(f"[1/5] fetching sources into {target}")
        source = fetch_sources(target)
    else:
        print(f"[1/5] using sources in {source}")

    print("[2/5] loading vocabulary")
    unigrams = load_unigrams(source / "unigrams.txt", args.min_count, args.max_words)
    bigrams = load_bigrams(source / "bigrams.txt", [w for w, _ in unigrams], args.head_limit, args.per_word)
    print(f"    {len(unigrams):,} words, {len(bigrams):,} bigram successor tables")

    print(f"[3/5] synthesising corpus ({args.words:,} words, seed={args.seed})")
    t0 = time.time()
    corpus = synthesise_corpus(unigrams, bigrams, args.words, args.bigram_p, args.seed)
    stream = corpus.replace(" ", "").upper()
    print(f"    {len(stream):,} letters in {time.time() - t0:.1f}s")

    print(f"[4/5] counting n-grams up to order {args.order}")
    t0 = time.time()
    counts = count_ngrams(stream, args.order)
    args.out.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "generator": "scripts/build_language_model.py",
        "seed": args.seed,
        "sampled_words": args.words,
        "letters": len(stream),
        "bigram_p": args.bigram_p,
        "vocab_size": len(unigrams),
        "min_count": args.min_count,
        "sources": {
            "wordsegment": "1.3.1 (Apache-2.0) -- Norvig unigram/bigram lists",
            "pyspellchecker": "0.9.0 (MIT) -- word frequency dictionary",
        },
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "build_seconds": {},
    }
    for n, table in sorted(counts.items()):
        name = args.out / f"english_{_order_name(n)}.txt.gz"
        distinct = write_ngrams(name, table)
        total = sum(table.values())
        meta[f"{_order_name(n)}_distinct"] = distinct
        meta[f"{_order_name(n)}_total"] = total
        top = ", ".join(g for g, _ in sorted(table.items(), key=lambda kv: -kv[1])[:8])
        print(f"    order {n}: {distinct:,} distinct / {total:,} total  top: {top}")
        print(f"      -> {name} ({name.stat().st_size / 1024:.0f} KiB)")
    meta["build_seconds"]["ngrams"] = round(time.time() - t0, 1)

    print("[5/5] writing dictionary")
    dictionary = build_dictionary(source / "en.json.gz", unigrams, args.dict_words)
    dict_path = args.out / "english_words.json.gz"
    write_dictionary(dict_path, dictionary)
    meta["dictionary_words"] = len(dictionary)
    print(f"    {len(dictionary):,} words -> {dict_path} ({dict_path.stat().st_size / 1024:.0f} KiB)")

    with open(args.out / "model_meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("done.")
    return 0


def _order_name(n: int) -> str:
    return {2: "bigrams", 3: "trigrams", 4: "quadgrams", 5: "pentagrams", 6: "hexagrams"}.get(n, f"{n}grams")


if __name__ == "__main__":
    raise SystemExit(main())
