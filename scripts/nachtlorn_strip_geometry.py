#!/usr/bin/env python3
"""Check whether the proposed I-zero strip counts follow from group geometry."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROW = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")


def predict_positions(indent: int, length: int, group: int = 5) -> list[int]:
    if any(type(n) is not int for n in (indent, length, group)) or indent < 0 or length < 1 or group < 1:
        raise ValueError("nonnegative indent and positive integer length/group required")
    return [indent + j + j // group for j in range(length)]


def analyze(rows: list[str], guide: int) -> dict:
    if not rows or type(guide) is not int or guide < 0 or any(not ROW.fullmatch(row) for row in rows):
        raise ValueError("nonempty ASCII rows and nonnegative integer guide required")
    records = []
    for index, row in enumerate(rows, 1):
        positions = [j for j, glyph in enumerate(row) if 'A' <= glyph <= 'Z']
        indent = len(row) - len(row.lstrip(' '))
        expected = predict_positions(indent, len(positions))
        records.append({'body_row': index, 'indent': indent, 'letters': len(positions),
                        'exact_position_match': positions == expected,
                        'first_mismatch_letter_index': next((j for j, (a, b) in
                                                             enumerate(zip(positions, expected)) if a != b), None),
                        'predicted_counts': {'below': sum(j < guide for j in expected),
                                             'on': sum(j == guide for j in expected),
                                             'above': sum(j > guide for j in expected)},
                        'actual_counts': {'below': sum(j < guide for j in positions),
                                          'on': sum(j == guide for j in positions),
                                          'above': sum(j > guide for j in positions)}})
    return {'guide_column': guide, 'group_letters': 5, 'rows': records,
            'exact_position_matches': sum(r['exact_position_match'] for r in records),
            'count_matches': sum(r['predicted_counts'] == r['actual_counts'] for r in records),
            'scope': 'Fixed group geometry and guide; this does not interpret ciphertext, prove the guide, or exclude other visual constructions.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error('output must not overwrite source')
    try:
        raw = args.path.read_bytes()
        lines = raw.decode('ascii').splitlines()
        rows = lines[8:]
        if not rows or not rows[-1].rstrip(' ').endswith('I'):
            raise ValueError('expected terminal I and eight-line preamble')
        guide = len(rows[-1].rstrip(' ')) - 1
        report = analyze(rows, guide)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report['source_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_bytes'] = len(raw)
    report['hypothesis'] = 'R21'
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'rows': len(report['rows']), 'guide': guide,
                      'exact_position_matches': report['exact_position_matches'], 'count_matches': report['count_matches']}))


if __name__ == '__main__':
    main()
