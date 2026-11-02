#!/usr/bin/env python3
"""R23: fixed-guide nearest-letter mirror pairing under one global bijection."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path

ROW = re.compile(r' *[A-Z]+(?: +[A-Z]+)* *')


def pairs_for_row(row: str, row_number: int, guide: int) -> list[dict]:
    if not ROW.fullmatch(row) or type(row_number) is not int or row_number < 1 or type(guide) is not int or guide < 0:
        raise ValueError('uppercase row, positive row number, nonnegative guide required')
    left = [(col, c) for col, c in enumerate(row) if 'A' <= c <= 'Z' and col < guide]
    right = [(col, c) for col, c in enumerate(row) if 'A' <= c <= 'Z' and col > guide]
    return [{'body_row': row_number, 'pair_index': i + 1, 'left_column': a[0], 'left': a[1],
             'right_column': b[0], 'right': b[1]}
            for i, (a, b) in enumerate(zip(reversed(left), right))]


def conflicts(a: dict, b: dict) -> bool:
    return (a['left'] == b['left'] and a['right'] != b['right']) or (a['left'] != b['left'] and a['right'] == b['right'])


def consistent(pairs: list[dict], omitted_row: int | None = None) -> bool:
    left, right = {}, {}
    for p in pairs:
        if p['body_row'] == omitted_row:
            continue
        a, b = p['left'], p['right']
        if (a in left and left[a] != b) or (b in right and right[b] != a):
            return False
        left[a], right[b] = b, a
    return True


def disjoint_certificate(pairs: list[dict]) -> list[dict] | None:
    """Find two conflicts requiring at least two distinct row omissions."""
    edges = {}
    for a, b in itertools.combinations(pairs, 2):
        if not conflicts(a, b):
            continue
        involved = frozenset((a['body_row'], b['body_row']))
        if involved in edges:
            continue
        for prior_rows, prior in edges.items():
            if involved.isdisjoint(prior_rows):
                return [prior, {'observations': [a, b], 'involved_rows': sorted(involved)}]
        edges[involved] = {'observations': [a, b], 'involved_rows': sorted(involved)}
    return None


def verify_certificate(rows: list[str], guide: int, certificate: list[dict]) -> bool:
    """Independently re-extract observations and verify both disjoint conflicts."""
    try:
        if len(certificate) != 2:
            return False
        seen = []
        for conflict in certificate:
            observations = conflict['observations']
            if len(observations) != 2 or not conflicts(*observations):
                return False
            rowset = set()
            for p in observations:
                row = p['body_row']
                rank = p['pair_index']
                if type(row) is not int or not 1 <= row <= len(rows) or type(rank) is not int or rank < 1:
                    return False
                actual = pairs_for_row(rows[row - 1], row, guide)
                if rank > len(actual) or p != actual[rank - 1]:
                    return False
                rowset.add(row)
            if sorted(rowset) != conflict['involved_rows']:
                return False
            seen.append(rowset)
        return seen[0].isdisjoint(seen[1])
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def analyze(rows: list[str], guide: int) -> dict:
    if len(rows) != 146 or any(sum('A' <= c <= 'Z' for c in row) != 60 for row in rows[:-1]) or sum('A' <= c <= 'Z' for c in rows[-1]) != 36:
        raise ValueError('expected 145 full rows and final 36-letter row')
    per_row = [pairs_for_row(row, index, guide) for index, row in enumerate(rows, 1)]
    full_pairs = list(itertools.chain.from_iterable(per_row[:-1]))
    if any(not pairs for pairs in per_row[:-1]):
        raise ValueError('each full row must have paired letters')
    compatible = [i for i in range(1, 146) if consistent(full_pairs, i)]
    certificate = disjoint_certificate(full_pairs)
    if certificate is not None and not verify_certificate(rows, guide, certificate):
        raise AssertionError('certificate verification failed')
    return {'hypothesis': 'R23', 'guide_column': guide, 'full_rows': 145,
            'pairing': 'Printed letters nearest zero outward on each side; no guide glyph, spaces or excess unpaired letters.',
            'paired_letters': len(full_pairs), 'pair_counts_by_full_row': [len(p) for p in per_row[:-1]],
            'final_row_pairs_excluded': len(per_row[-1]), 'consistent_without_removal': consistent(full_pairs),
            'compatible_single_removed_rows': compatible, 'disjoint_conflict_certificate': certificate,
            'certificate_verified': certificate is not None,
            'interpretation': 'A disjoint certificate excludes one fixed shared bijection after at most one full-row omission, only for this exact raw pairing. It does not recover a population or outlier.'}


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
        guide = len(rows[-1].rstrip(' ')) - 1
        report = analyze(rows, guide)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report['source_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_bytes'] = len(raw)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('paired_letters', 'final_row_pairs_excluded', 'consistent_without_removal', 'compatible_single_removed_rows', 'disjoint_conflict_certificate')}))


if __name__ == '__main__':
    main()
