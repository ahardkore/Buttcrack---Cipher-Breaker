#!/usr/bin/env python3
"""Exact iid-uniform maximum-frequency union bound; not an answer selector."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_strip_counts import parse_rows  # noqa: E402


def binomial_upper_tail(n: int, k: int, alphabet_size: int) -> Fraction:
    """Exact Pr[Bin(n, 1/alphabet_size) >= k], using integer arithmetic."""
    if any(type(x) is not int for x in (n, k, alphabet_size)) or n < 0 or k < 0 or alphabet_size < 2:
        raise ValueError('nonnegative integer n,k and alphabet size >= 2 required')
    if k == 0:
        return Fraction(1)
    if k > n:
        return Fraction(0)
    failures = alphabet_size - 1
    term = math.comb(n, k) * failures ** (n - k)
    total = term
    for j in range(k, n):
        numerator, denominator = term * (n - j), (j + 1) * failures
        term, remainder = divmod(numerator, denominator)
        if remainder:
            raise ArithmeticError('binomial recurrence unexpectedly non-integral')
        total += term
    return Fraction(total, alphabet_size ** n)


def decimal_value(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 30
        return format(Decimal(value.numerator) / Decimal(value.denominator), '.20g')


def analyze(raw: bytes) -> dict:
    rows = parse_rows(raw)
    if len(rows) != 146 or any(sum('A' <= c <= 'Z' for c in row) != 60 for row in rows[:-1]) or sum('A' <= c <= 'Z' for c in rows[-1]) != 36:
        raise ValueError('registered original 145 full rows plus final 36-letter row required')
    def stream(subset):
        return ''.join(c for row in subset for c in row if 'A' <= c <= 'Z')
    text = stream(rows)
    histogram = Counter(text)
    maximum = max(histogram.values())
    letters = sorted(c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if histogram[c] == maximum)
    one = binomial_upper_tail(len(text), maximum, 26)
    corrected = min(Fraction(1), 26 * one)
    return {'hypothesis': 'R28', 'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_bytes': len(raw),
            'letters': len(text), 'counts_A_to_Z': [histogram[c] for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'],
            'max_count': maximum, 'max_glyphs': letters,
            'expected_count_per_glyph_under_uniform': len(text) / 26,
            'specified_glyph_binomial_upper_tail_decimal': decimal_value(one),
            'maximum_26_glyph_union_bound_decimal': decimal_value(corrected),
            'page1_rows': 61, 'page1_max_glyph_counts': {c: stream(rows[:61]).count(c) for c in letters},
            'page2_max_glyph_counts': {c: stream(rows[61:]).count(c) for c in letters},
            'status': 'Post-observation exploratory reference calculation, not a plaintext, key or outlier.',
            'interpretation': 'Under iid uniform letters, Pr(any of 26 counts >= observed maximum) is at most the union bound. This 26-way correction is not a correction for earlier research or proof of the generator. Marginal frequency and visual-strip outlier are different questions.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error('output must not overwrite source')
    try:
        report = analyze(args.path.read_bytes())
    except (OSError, UnicodeError, ValueError, ArithmeticError) as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('letters', 'max_count', 'max_glyphs',
                      'specified_glyph_binomial_upper_tail_decimal', 'maximum_26_glyph_union_bound_decimal',
                      'page1_max_glyph_counts', 'page2_max_glyph_counts')}))


if __name__ == '__main__':
    main()
