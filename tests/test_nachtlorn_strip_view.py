from __future__ import annotations

import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts import nachtlorn_strip_view as strips

NS = {'svg': 'http://www.w3.org/2000/svg'}


class StripViewTests(unittest.TestCase):
    def test_every_glyph_keeps_its_row_and_physical_column(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / 'docs/data/nachtlorn-transcript.txt').read_bytes()
        rows = raw.decode('ascii').splitlines()[8:]
        document = ET.fromstring(strips.view(raw))
        self.assertIn(hashlib.sha256(raw).hexdigest(), document.find('svg:metadata', NS).text)
        groups = document.findall('svg:g', NS)
        self.assertEqual(len(groups), 146)
        max_col = max(len(r.rstrip(' ')) - 1 for r in rows)
        for index, (group, row) in enumerate(zip(groups, rows)):
            self.assertEqual(group.attrib['data-body-row'], str(index + 1))
            glyphs = group.findall('svg:text', NS)
            expected = [(col, c) for col, c in enumerate(row) if 'A' <= c <= 'Z']
            actual = [(int(g.attrib['data-column']), g.text) for g in glyphs]
            self.assertEqual(actual, expected)
            for glyph, (col, _) in zip(glyphs, expected):
                self.assertEqual(int(glyph.attrib['x']), 70 + 10 * index)
                self.assertEqual(int(glyph.attrib['y']), 100 + 13 * (max_col - col) + 3)
        axis = document.find("svg:line[@class='axis']", NS)
        self.assertEqual(int(axis.attrib['y1']), 100 + 13 * (max_col - 48))
        self.assertEqual(groups[-1].findall('svg:text', NS)[-1].text, 'I')
        self.assertEqual(groups[-1].findall('svg:text', NS)[-1].attrib['data-column'], '48')

    def test_rejects_invalid_and_does_not_overwrite_source(self):
        with self.assertRaises(ValueError):
            strips.view(b'bad')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'source'
            p.write_text('unchanged')
            with self.assertRaises(SystemExit):
                strips.main([str(p), '--output', str(p)])
            self.assertEqual(p.read_text(), 'unchanged')

    def test_public_svg_is_exactly_reproducible(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'docs/data/nachtlorn-strip-view.svg'
        if not path.exists():
            self.skipTest('view not yet created')
        self.assertEqual(path.read_text(), strips.view((root / 'docs/data/nachtlorn-transcript.txt').read_bytes()))


if __name__ == '__main__':
    unittest.main()
