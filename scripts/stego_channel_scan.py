#!/usr/bin/env python3
"""Scan a text file for covert channels that the cipher solvers cannot see.

``buttcrack`` attacks ciphers: it assumes every character is ciphertext and tries
to undo a mapping.  A large class of puzzles instead hides its payload *around*
the characters -- in the leading whitespace, in letter case, in word lengths, in a
property of each letter (parity, alphabet half, vowel/consonant) -- while the
visible characters are filler that looks like random noise.  For those puzzles a
substitution solver reports "not broken" and a human is left staring at gibberish.

This script does the complement: it measures whether the visible text carries any
language at all, then tries the standard covert channels and *scores* every
candidate with the package's own language model, so a real payload stands out and
coincidences do not.  It is read-only and has no dependencies beyond the package.

Usage::

    python3 scripts/stego_channel_scan.py ciphertext.txt
    python3 scripts/stego_channel_scan.py ciphertext.txt --threshold -5.0

What it reports
---------------
* raw file facts: size, non-ASCII code points, tabs, trailing spaces, doubled
  spaces, line/word geometry, the indent alphabet;
* randomness battery on the letter stream: index of coincidence, differential IC
  at every lag (a peak means a key that repeats at that period), monogram and
  digram chi-squared against Monte-Carlo baselines, trigram multiplicity against
  a Poisson expectation, worst column IC inside 5-letter groups and lines;
* "is there any language here": best n-gram fitness over every contiguous window
  under all 26 Caesar shifts and Atbash, so a plaintext buried in filler -- or a
  shifted one -- is not missed;
* whitespace channel: every standard reading of the leading-indent values
  (octal triples, packed 3-bit in all phases and directions, nibbles, all 254
  two-class symbol splits, Baconian, base-8 big integers read from either end,
  Morse, letter-at-indent selections);
* letter-property channels: bit planes, alphabet half, parity, vowel, per
  position in the 5-letter groups, and whether the indent correlates with any
  simple statistic of its line.

A candidate is only reported as a hit when its language fitness clears
``--threshold``; everything else is summarised as "best score, still random".
Exit status is 0 when something was found, 1 when nothing was.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from buttcrack.lang import LanguageModel  # noqa: E402
from buttcrack.text import index_of_coincidence, letters_only  # noqa: E402

PRINTABLE = set(range(32, 127)) | {9, 10, 13}
CIPHER_LINE = re.compile(r"[A-Z]{2,}")
MORSE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
}


# ---------------------------------------------------------------- utilities ---
def printable_ratio(data: bytes) -> float:
    return sum(1 for b in data if b in PRINTABLE) / len(data) if data else 0.0


def unpack(bits: list[int], width: int, phase: int = 0) -> list[int]:
    """Pack bit lists MSB-first into ``width``-bit integers."""
    bits = bits[phase:]
    out = []
    for i in range(0, len(bits) - width + 1, width):
        value = 0
        for bit in bits[i : i + width]:
            value = (value << 1) | bit
        out.append(value)
    return out


def to_bytes(bits: list[int]) -> bytes:
    return bytes(unpack(bits, 8))


def bigint_bytes(digits: str, base: int) -> bytes:
    value = int(digits, base) if digits else 0
    return value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""


class Scanner:
    """Collects channel candidates and keeps the best-scoring ones."""

    def __init__(self, model: LanguageModel, threshold: float, keep: int = 6) -> None:
        self.model = model
        self.threshold = threshold
        self.best: list[tuple[float, str, str]] = []
        self.hits: list[tuple[str, str]] = []
        self.keep = keep
        self.tested = Counter()

    # ---- reporting -----------------------------------------------------
    def section(self, title: str) -> None:
        print(f"\n{title}\n{'-' * len(title)}")

    def note(self, text: str) -> None:
        print(f"  {text}")

    # ---- candidate gate ------------------------------------------------
    def offer(self, channel: str, payload: str, *, letters_only_payload: bool = False) -> None:
        """Score one decoded candidate; record it if it clears the threshold."""
        text = letters_only(payload) if letters_only_payload else payload
        letters = letters_only(text)
        if len(letters) < 24:
            return
        self.tested[channel.split()[0]] += 1
        if not letters_only_payload:
            if printable_ratio(text.encode("latin-1", "replace")) < 0.9:
                return
        score = self.model.fitness(letters)
        if len(self.best) < self.keep or score > self.best[-1][0]:
            self.best.append((score, channel, text))
            self.best.sort(reverse=True)
            del self.best[self.keep :]
        if score >= self.threshold:
            self.hits.append((channel, text))
            print(f"  HIT {score:+.2f}  {channel}: {text[:100]!r}")

    def offer_bytes(self, channel: str, data: bytes) -> None:
        self.offer(channel, data.decode("latin-1"))


# --------------------------------------------------------------- file facts ---
def scan_file_facts(sc: Scanner, raw: bytes, text: str) -> None:
    sc.section("file facts")
    lines = text.splitlines()
    body = [ln for ln in lines if CIPHER_LINE.search(ln)]
    odd = Counter(ch for ch in text if not (32 <= ord(ch) <= 126) and ch != "\n")
    sc.note(f"{len(raw)} bytes, {len(text)} characters, {len(lines)} lines")
    sc.note(f"non-ASCII / control code points: {len(odd)} {dict(odd) if odd else ''}")
    sc.note(f"tabs {text.count(chr(9))}, lines with trailing space "
            f"{sum(1 for ln in lines if ln != ln.rstrip())}, doubled spaces "
            f"{sum(1 for ln in lines if '  ' in ln.strip())}")
    sc.note(f"ends with newline: {text.endswith(chr(10))}")
    if not body:
        sc.note("no cipher-like body lines found")
        return
    letters = ["".join(ln.split()) for ln in body]
    sc.note(f"body: {len(body)} lines, tokens per line "
            f"{dict(Counter(len(ln.split()) for ln in body))}, "
            f"letters per line {dict(Counter(len(x) for x in letters))}")
    indent = Counter(len(ln) - len(ln.lstrip(" ")) for ln in body)
    sc.note(f"indent alphabet: {dict(sorted(indent.items()))}")
    short = min(letters, key=len)
    sc.note(f"shortest body line: {short!r} ({len(short)} letters)")


# ------------------------------------------------------- randomness battery ---
def scan_randomness(sc: Scanner, stream: str) -> None:
    sc.section("randomness battery on the letter stream")
    n = len(stream)
    ic = index_of_coincidence(stream)
    sc.note(f"{n} letters, IC {ic:.5f} (uniform {1 / 26:.5f}, English ~0.0667)")
    counts = Counter(stream)
    expected = n / 26
    sigma = math.sqrt(n * (1 / 26) * (25 / 26))
    chi = sum((counts[chr(65 + i)] - expected) ** 2 / expected for i in range(26))
    var = sum((counts[chr(65 + i)] - expected) ** 2 for i in range(26)) / 25
    sc.note(f"monogram chi-squared {chi:.1f} (25 df; iid uniform ~25 +- 7), count "
            f"variance {var:.0f} (multinomial {n / 26 * 25 / 26:.0f})")
    sc.note("extremes: " + ", ".join(f"{c} {v} ({(v - expected) / sigma:+.1f} sigma)"
                                     for c, v in counts.most_common(2) + counts.most_common()[-2:]))
    digrams = Counter(stream[i : i + 2] for i in range(n - 1))
    exp_di = (n - 1) / 676
    chi_di = sum((v - exp_di) ** 2 / exp_di for v in digrams.values()) + (676 - len(digrams)) * exp_di
    sc.note(f"digram chi-squared {chi_di:.1f} (676 df; iid uniform ~676)")

    trigrams = Counter(stream[i : i + 3] for i in range(n - 2))
    lam = (n - 2) / 17576
    observed = dict(sorted(Counter(trigrams.values()).items()))
    predicted = {k: round(math.exp(-lam) * lam ** k / math.factorial(k) * 17576, 1)
                 for k in range(max(observed) + 1)}
    sc.note(f"trigram multiplicity {observed}")
    sc.note(f"Poisson(lambda={lam:.2f}) prediction {predicted}")

    lags = list(range(1, min(400, n // 4)))
    ics = [(index_of_coincidence(stream[k:]), k) for k in lags]
    sc.note(f"IC over lags 1-{max(lags)}: min {min(ics)[0]:.5f}, max {max(ics)[0]:.5f} "
            f"(a repeating polyalphabetic key peaks here)")
    diff = []
    for k in lags:
        d = "".join(chr((ord(stream[i]) - ord(stream[i + k])) % 26 + 65) for i in range(n - k))
        diff.append((index_of_coincidence(d), k))
    sc.note(f"differential IC over lags 1-{max(lags)}: min {min(diff)[0]:.5f}, max "
            f"{max(diff)[0]:.5f} (a period-p key shows English structure at lag p)")
    for width, label in ((5, "5-letter group"), (60, "line")):
        worst = max(index_of_coincidence(stream[c::width]) for c in range(width))
        sc.note(f"best column IC inside a {label}: {worst:.5f}")


def scan_language(sc: Scanner, stream: str, window: int) -> None:
    sc.section("is any of it language?")
    sc.note(f"whole-stream fitness {sc.model.fitness(stream):.2f} per char "
            f"(English ~-4.1, random ~-7.8)")
    best: list[tuple[float, int, int]] = []
    variants = {shift: "".join(chr((ord(c) - 65 + shift) % 26 + 65) for c in stream)
                for shift in range(26)}
    variants[-1] = "".join(chr(25 - (ord(c) - 65) + 65) for c in stream)
    for shift, text in variants.items():
        for start in range(0, len(text) - window, 5):
            best.append((sc.model.fitness(text[start : start + window]), start, shift))
    best.sort(reverse=True)
    score, start, shift = best[0]
    label = "atbash" if shift < 0 else f"caesar {shift}"
    sc.note(f"best {window}-letter window: {score:.2f} per char at offset {start} ({label})")
    if score >= sc.threshold:
        sc.offer(f"language window offset {start} {label}", variants[shift][start : start + window])
    else:
        sc.note("=> no window of this length reads as language in any shift")


# ---------------------------------------------------- whitespace / indents ---
def scan_whitespace(sc: Scanner, body: list[str]) -> None:
    sc.section("whitespace channel (leading indent)")
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in body]
    letters = ["".join(ln.split()) for ln in body]
    sc.note(f"values: {indents}")
    counts = Counter(indents)
    expected = len(indents) / 8
    chi = sum((counts.get(v, 0) - expected) ** 2 / expected for v in range(8))
    sc.note(f"per-value chi-squared {chi:.1f} (7 df); repeats vs previous "
            f"{sum(1 for a, b in zip(indents, indents[1:]) if a == b)} "
            f"(expected {(len(indents) - 1) / 8:.1f})")

    digits = "".join(str(v) for v in indents)
    for rev in (False, True):
        seq = digits[::-1] if rev else digits
        tag = "reversed" if rev else "forward"
        for phase in range(3):
            values = [int(seq[i : i + 3], 8) for i in range(phase, len(seq) - 2, 3)]
            sc.offer_bytes(f"octal triple {tag} phase {phase}", bytes(v for v in values if v < 256))
        bits: list[int] = []
        for ch in seq:
            v = int(ch)
            bits += [(v >> 2) & 1, (v >> 1) & 1, v & 1]
        for phase in range(8):
            sc.offer_bytes(f"3-bit packed {tag} phase {phase}", to_bytes(bits[phase:]))
            sc.offer_bytes(f"3-bit packed {tag} phase {phase} reversed",
                           to_bytes(bits[phase:][::-1]))
        sc.offer_bytes(f"nibbles {tag}",
                       bytes(int(seq[i]) * 16 + int(seq[i + 1]) for i in range(0, len(seq) - 1, 2)))
        sc.offer_bytes(f"nibbles swapped {tag}",
                       bytes(int(seq[i + 1]) * 16 + int(seq[i]) for i in range(0, len(seq) - 1, 2)))
        sc.offer_bytes(f"base-8 bigint {tag}", bigint_bytes(seq, 8))

    for label, reader in (("prefix", lambda k: digits[:k]), ("suffix", lambda k: digits[k:])):
        for k in range(8, len(digits)):
            data = bigint_bytes(reader(k), 8)
            if len(data) >= 8 and printable_ratio(data) > 0.95:
                sc.offer_bytes(f"base-8 {label} of {k} digits", data)

    for mask in range(1, 255):
        bits = [1 if (mask >> v) & 1 else 0 for v in indents]
        for rev in (False, True):
            seq = bits[::-1] if rev else bits
            for phase in range(8):
                sc.offer_bytes(f"2-class split {mask:08b} {'reversed' if rev else 'forward'} "
                               f"phase {phase}", to_bytes(seq[phase:]))
        for phase in range(5):
            decoded = []
            for i in range(phase, len(bits) - 4, 5):
                value = int("".join(map(str, bits[i : i + 5])), 2)
                decoded.append(chr(65 + value) if value < 26 else "?")
            sc.offer(f"baconian split {mask:08b} phase {phase}",
                     "".join(decoded), letters_only_payload=True)

    for threshold in range(1, 8):
        for separator in range(8):
            coded = "".join(" " if v == separator else "." if v < threshold else "-"
                            for v in indents)
            decoded = "".join(MORSE.get(tok, "") for tok in coded.split(" "))
            sc.offer(f"morse threshold {threshold} separator {separator}",
                     decoded, letters_only_payload=True)

    for offset in range(-8, 9):
        picked = "".join(ln[i + offset] if 0 <= i + offset < len(ln) else ""
                         for ln, i in zip(letters, indents))
        sc.offer(f"letter at indent{offset:+d}", picked, letters_only_payload=True)
    for a in range(0, 61, 1):
        for b in (-2, -1, 0, 1, 2):
            picked = "".join(ln[(a * i + b * ind + 0) % len(ln)]
                             for i, (ln, ind) in enumerate(zip(letters, indents)))
            sc.offer(f"selection {a}*line+{b}*indent", picked, letters_only_payload=True)
    sc.note(f"{sum(sc.tested.values())} candidates scored, none cleared the threshold"
            if not sc.hits else "see hits above")


# ------------------------------------------------------ letter-property probes ---
def scan_letter_properties(sc: Scanner, body: list[str], stream: str) -> None:
    sc.section("letter-property channels")
    idx = [ord(c) - 65 for c in stream]
    props = {
        "alphabet half": lambda v: int(v >= 13),
        "parity": lambda v: v % 2,
        "vowel": lambda v: int(chr(v + 65) in "AEIOU"),
        "bit0": lambda v: v & 1,
        "bit1": lambda v: (v >> 1) & 1,
        "bit2": lambda v: (v >> 2) & 1,
        "bit3": lambda v: (v >> 3) & 1,
        "bit4": lambda v: (v >> 4) & 1,
    }
    for name, fn in props.items():
        bits = [fn(v) for v in idx]
        for rev in (False, True):
            seq = bits[::-1] if rev else bits
            for phase in range(8):
                sc.offer_bytes(f"{name} bitstream {'rev' if rev else 'fwd'} phase {phase}",
                               to_bytes(seq[phase:]))

    groups = re.findall(r".{5}", stream)
    for p in range(5):
        sub = "".join(g[p] for g in groups)
        sc.note(f"position {p} of every 5-letter group: fitness {sc.model.fitness(sub):.2f}, "
                f"IC {index_of_coincidence(sub):.5f}")
    sc.note(f"first letters of groups: fitness "
            f"{sc.model.fitness(''.join(g[0] for g in groups)):.2f}")
    sc.note(f"first letters of lines: fitness "
            f"{sc.model.fitness(''.join(ln[0] for ln in body)):.2f}")

    sc.section("indent vs line content")
    checks = {
        "odd-letter count": lambda s: sum(1 for c in s if (ord(c) - 65) % 2),
        "letter sum": lambda s: sum(ord(c) - 65 for c in s),
        "vowel count": lambda s: sum(1 for c in s if c in "AEIOU"),
        "distinct letters": lambda s: len(set(s)),
        "first letter": lambda s: ord(s[0]) - 65,
        "last letter": lambda s: ord(s[-1]) - 65,
    }
    for name, fn in checks.items():
        agree = sum(1 for ln, ind in zip(body, [len(x) - len(x.lstrip()) for x in body])
                    if fn("".join(ln.split())) % 8 == ind)
        sc.note(f"{name} mod 8 == indent: {agree}/{len(body)} "
                f"({agree / len(body):.3f}, chance {1 / 8:.3f})")


# -------------------------------------------------------------------- driver ---
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="text file to scan")
    parser.add_argument("--window", type=int, default=60,
                        help="window length for the language sweep (default 60)")
    parser.add_argument("--threshold", type=float, default=-5.5,
                        help="language fitness (log10 per char) a candidate must reach "
                             "to count as a hit; English ~-4.5, random ~-7.5 (default -5.5)")
    args = parser.parse_args(argv)

    raw = args.path.read_bytes()
    text = raw.decode("utf-8", "replace")
    sc = Scanner(LanguageModel.get("english"), args.threshold)

    scan_file_facts(sc, raw, text)
    body = [ln for ln in text.splitlines() if CIPHER_LINE.search(ln)]
    stream = letters_only("".join(body))
    if not stream:
        sc.note("no letter stream to analyse")
        return 1
    scan_randomness(sc, stream)
    scan_language(sc, stream, args.window)
    scan_whitespace(sc, body)
    scan_letter_properties(sc, body, stream)

    print("\nsummary\n-------")
    if sc.hits:
        for channel, payload in sc.hits:
            print(f"  {channel} -> {payload[:120]!r}")
        print(f"\n{len(sc.hits)} candidate(s) cleared {args.threshold:+.2f}; verify by hand.")
        return 0
    print(f"  No covert channel cleared the threshold {args.threshold:+.2f}.")
    if sc.best:
        print("  Best-scoring candidates, all noise-level:")
        for score, channel, payload in sc.best:
            print(f"    {score:+.2f}  {channel}: {payload[:70]!r}")
    print("  Combined with the randomness battery above, that means the file carries no"
          "\n  recoverable plaintext: the payload or its key lives outside it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
