#!/usr/bin/env python3
"""Make a transcript-derived sideways strip view, retaining physical columns.

This is a diagram, not a reproduction of the supplied page images. Each
original body row is a vertical strip; the final I is a provisional zero.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
from pathlib import Path

ROW = re.compile(r' *[A-Z]+(?: +[A-Z]+)* *')


def view(raw: bytes) -> str:
    rows = raw.decode('ascii').splitlines()[8:]
    if len(rows) != 146 or any(not ROW.fullmatch(row) for row in rows):
        raise ValueError('expected original 146 uppercase body rows after eight-line preamble')
    if not rows[-1].rstrip(' ').endswith('I'):
        raise ValueError('terminal I required as the provisional zero')
    guide = len(rows[-1].rstrip(' ')) - 1
    # Blank columns are still represented in coordinate calculations. Increasing
    # original column moves up; row order runs left to right for legibility.
    max_col = max(len(row.rstrip(' ')) - 1 for row in rows)
    x0, dx, dy, top = 70, 10, 13, 100
    y_for = lambda col: top + (max_col - col) * dy  # noqa: E731
    width = x0 + dx * (len(rows) - 1) + 90
    height = y_for(0) + 115
    source_hash = hashlib.sha256(raw).hexdigest()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">Nachtlorn — reconstructed sideways strips, provisional I-zero guide</title>',
           '<desc id="desc">Each original transcript body line is one upright-letter vertical strip. Increasing original columns run upward. Group spaces and indentation retain their physical columns. The red guide uses the final I as a hypothesis, not an established solution.</desc>',
           f'<metadata>Source SHA256 {source_hash}; diagram reflows rows horizontally, not a scan of the original pages.</metadata>',
           '<rect width="100%" height="100%" fill="#fafafa"/>',
           '<style>text{font-family:monospace;fill:#202934}.glyph{font-size:9px;text-anchor:middle}.minor{font-size:10px}.major{font-size:14px;font-weight:bold}.axis{stroke:#b63c37;stroke-width:1.4}.grid{stroke:#e0e5eb;stroke-width:0.6}</style>',
           '<text x="20" y="24" class="major">Sideways strips — provisional I = 0</text>',
           '<text x="20" y="44" class="minor">Transcript-derived diagram, not the page photographs. One original line per strip; spaces retain their columns.</text>',
           '<text x="20" y="60" class="minor">Original columns increase upward; strips are displayed left-to-right in source row order. Zoom to read glyphs.</text>']
    for col in range(0, max_col + 1, 5):
        y = y_for(col)
        out.append(f'<line x1="{x0 - 8}" x2="{width - 30}" y1="{y}" y2="{y}" class="grid"/>')
        out.append(f'<text x="{x0 - 14}" y="{y + 3}" text-anchor="end" class="minor">{col - guide:+d}</text>')
    axis_y = y_for(guide)
    out.append(f'<line x1="{x0 - 8}" x2="{width - 30}" y1="{axis_y}" y2="{axis_y}" class="axis"/>')
    out.append(f'<text x="{width - 25}" y="{axis_y + 3}" class="minor">0</text>')
    for index, row in enumerate(rows):
        x = x0 + index * dx
        indent = len(row) - len(row.lstrip(' '))
        title = html.escape(f'Body row {index + 1}; indent {indent}; original line: {row}', quote=True)
        out.append(f'<g data-body-row="{index + 1}"><title>{title}</title>')
        for col, c in enumerate(row):
            if 'A' <= c <= 'Z':
                out.append(f'<text class="glyph" x="{x}" y="{y_for(col) + 3}" data-column="{col}">{c}</text>')
        out.append('</g>')
        if index % 10 == 0 or index == len(rows) - 1:
            out.append(f'<text x="{x}" y="{height - 72}" class="minor" text-anchor="middle">{index + 1}</text>')
    page_split_x = x0 + 60.5 * dx
    out.append(f'<line x1="{page_split_x}" x2="{page_split_x}" y1="{top - 15}" y2="{height - 85}" stroke="#698099" stroke-dasharray="4 4"/>')
    out.append(f'<text x="{x0}" y="{height - 48}" class="minor">Page 1: body rows 1–61</text>')
    out.append(f'<text x="{x0 + 61 * dx}" y="{height - 48}" class="minor">Page 2: body rows 62–146</text>')
    out.append('<text x="20" y="' + str(height - 20) + '" class="minor">The short final row is not established as the puzzle’s final outlier. Row numbers are one-based.</text>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error('output must not overwrite source')
    try:
        output = view(args.path.read_bytes())
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    args.output.write_text(output, encoding='utf-8')
    print(f'Wrote transcript-derived view to {args.output}')


if __name__ == '__main__':
    main()
