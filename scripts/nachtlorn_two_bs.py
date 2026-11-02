#!/usr/bin/env python3
"""R22: exploratory literal two-B / neither-right rule on original strips."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from fractions import Fraction
from pathlib import Path

ROW = re.compile(r' *[A-Z]+(?: +[A-Z]+)* *')


def inspect(row: str, guide: int) -> dict:
    if not ROW.fullmatch(row) or type(guide) is not int or guide < 0:
        raise ValueError('uppercase ASCII row and nonnegative guide required')
    positions = [i for i, char in enumerate(row) if 'A' <= char <= 'Z']
    b = [i for i, char in enumerate(row) if char == 'B']
    left = sum(p < guide for p in b)
    on = sum(p == guide for p in b)
    right = sum(p > guide for p in b)
    left_slots = sum(p < guide for p in positions)
    expected = Fraction(math.comb(left_slots, 2), math.comb(len(positions), 2)) if len(b) == 2 else Fraction(0)
    return {'letters': len(positions), 'left_slots': left_slots,
            'b_left': left, 'b_on': on, 'b_right': right, 'b_total': len(b),
            'matches_rule': left == 2 and on == 0 and right == 0,
            'conditional_expected_match_numerator': expected.numerator,
            'conditional_expected_match_denominator': expected.denominator}


def analyze(rows: list[str], guide: int) -> dict:
    if len(rows) != 146:
        raise ValueError('registered source requires 145 full rows and one final row')
    records = [{'body_row': i, **inspect(row, guide)} for i, row in enumerate(rows, 1)]
    if any(r['letters'] != 60 for r in records[:-1]) or records[-1]['letters'] != 36:
        raise ValueError('registered 60/36 row lengths required')
    matches = [r['body_row'] for r in records[:-1] if r['matches_rule']]
    expectation = sum((Fraction(r['conditional_expected_match_numerator'], r['conditional_expected_match_denominator'])
                       for r in records[:-1]), Fraction(0))
    return {'hypothesis': 'R22', 'guide_column': guide,
            'rule': 'Exactly two literal B glyphs in a full row, both strictly left of the I-zero column; B on zero fails.',
            'full_rows': 145, 'full_row_matches': matches, 'full_row_match_count': len(matches),
            'unique_full_row': len(matches) == 1,
            'conditional_null': {'description': 'Uniform random placement of each row’s observed B count among its existing letter slots, conditional on its layout; expectation only, not a global significance test.',
                                 'exact_expected_matches_numerator': expectation.numerator,
                                 'exact_expected_matches_denominator': expectation.denominator,
                                 'expected_matches': float(expectation)},
            'final_short_row_boundary_control': records[-1], 'rows': records,
            'limits': 'Speculative literal pun; no author-confirmed rule, decoded object, population or final outlier. Negative applies only to this fixed raw-row predicate.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error('output must not overwrite source')
    try:
        raw = args.path.read_bytes()
        rows = raw.decode('ascii').splitlines()[8:]
        if not rows or not rows[-1].rstrip(' ').endswith('I'):
            raise ValueError('expected original body ending in I')
        report = analyze(rows, len(rows[-1].rstrip(' ')) - 1)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report['source_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_bytes'] = len(raw)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('guide_column', 'full_row_match_count', 'unique_full_row', 'conditional_null', 'final_short_row_boundary_control')}))


if __name__ == '__main__':
    main()
