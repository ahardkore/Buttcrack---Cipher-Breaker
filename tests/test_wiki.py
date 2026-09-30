"""Tests for the cipher wiki's build-time guarantees.

The wiki is generated: ``ventures/cipher-solver-web/build_pages.py`` turns the
solver's own cipher registry into fifty articles, and ``wiki_ciphers.py``
supplies the per-cipher prose.  These tests pin the invariants that make that
pipeline trustworthy without building the whole site (``build_pages.main()``
writes PDFs and HTML and belongs to CI's deploy job, not the unit suite):

* every registered cipher gets exactly one article, with a unique slug;
* the worked examples really are the cipher's own output (they encrypt the
  stated plaintext under the stated key);
* ``with_toc`` cannot emit a contents box whose anchors do not exist, and
  honours the ``data-notoc`` opt-out the main page's rotating slot relies on;
* ``check_internal_links`` actually catches broken pages and anchors, so the
  build-time green light means something;
* ``payment_url`` enforces the Stripe discipline (never a test-mode or
  dashboard link in a published page).

Importing ``build_pages`` pulls in ``buttcrack`` (already imported by the
rest of this suite) and reads ``site.json``; it does not write anything.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

VENTURE = Path(__file__).resolve().parents[1] / "ventures" / "cipher-solver-web"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bp = _load("build_pages", VENTURE / "build_pages.py")
wc = _load("wiki_ciphers_test_module", VENTURE / "wiki_ciphers.py")


class TestSpecCoversRegistry(unittest.TestCase):
    def test_every_cipher_has_a_spec(self):
        specs = wc.cipher_page_specs()
        by_slug = {s["slug"]: s for s in specs}
        for name in wc.HAND_WRITTEN:
            self.assertNotIn(wc.wiki_slug(name), by_slug,
                             f"{name} is hand-written; a generated spec would shadow it")
        for cipher in wc.all_ciphers():
            name = cipher.info.name
            if name in wc.HAND_WRITTEN:
                continue
            slug = wc.wiki_slug(name)
            self.assertIn(slug, by_slug, f"no generated spec for {name!r}")
            self.assertEqual(by_slug[slug]["h1"], cipher.info.title)

    def test_slugs_unique(self):
        specs = wc.cipher_page_specs()
        slugs = [s["slug"] for s in specs] + [s["slug"] for s in bp.WIKI_PAGES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_meta_descriptions_bounded(self):
        # Search engines truncate around 160 characters; a description built
        # past that is a registry edit away from a mangled snippet.
        for spec in wc.cipher_page_specs():
            self.assertLessEqual(
                len(spec["desc"]), 165,
                f"{spec['slug']} description is {len(spec['desc'])} chars")

    def test_examples_are_real_output(self):
        checked = 0
        for cipher in wc.all_ciphers():
            name = cipher.info.name
            ex = wc._example(name)
            if ex is None:
                continue
            plaintext, shown, _key_display = ex
            sample = wc.SAMPLE_OVERRIDES.get(name, wc.SAMPLE_PLAINTEXT)
            key = cipher.info.example_key
            ciphertext = (
                cipher.encrypt(sample, key)
                if key not in (None, "") else cipher.encrypt(sample)
            )
            expected = ciphertext if len(ciphertext) <= 240 else ciphertext[:237] + "..."
            self.assertEqual(shown, expected,
                             f"{name}: worked example is not the cipher's own output")
            self.assertGreater(len(plaintext), 0)
            checked += 1
        self.assertGreaterEqual(checked, 40, "expected examples for most ciphers")


class TestTableOfContents(unittest.TestCase):
    def test_anchors_exist_and_nest(self):
        body = ("<h2>One</h2><p>x</p>"
                "<h3>Deep</h3><p>y</p>"
                '<h2 id="kept">Two</h2>'
                "<h3 data-notoc>Hidden</h3>")
        new_body, toc = bp.with_toc(body)
        self.assertIn('id="one"', new_body)
        self.assertIn('id="deep"', new_body)
        self.assertIn('id="kept"', new_body)  # pre-existing id is preserved
        self.assertNotIn('id="hidden"', new_body)  # data-notoc is left alone
        self.assertIn('href="#one"', toc)
        self.assertIn('href="#deep"', toc)
        self.assertIn('href="#kept"', toc)
        self.assertNotIn("Hidden", toc)
        # the h3 nests inside the h2's <li>, not beside it
        self.assertIn("<ul><li><a href=\"#deep\">Deep</a></li></ul></li>", toc)

    def test_repeated_headings_get_suffixes(self):
        body = "<h2>Shift</h2><p>a</p><h2>Shift</h2><p>b</p>"
        new_body, toc = bp.with_toc(body)
        self.assertIn('id="shift"', new_body)
        self.assertIn('id="shift-1"', new_body)

    def test_no_headings_no_toc(self):
        new_body, toc = bp.with_toc("<p>just prose</p>")
        self.assertEqual(toc, "")
        self.assertEqual(new_body, "<p>just prose</p>")


class TestLinkChecker(unittest.TestCase):
    def test_catches_missing_page(self):
        written = {"a.html": '<a href="missing.html">x</a>'}
        with self.assertRaises(SystemExit):
            bp.check_internal_links(written)

    def test_catches_missing_anchor(self):
        written = {"a.html": '<a href="b.html#nowhere">x</a>',
                   "b.html": "<p>no ids</p>"}
        with self.assertRaises(SystemExit):
            bp.check_internal_links(written)

    def test_accepts_valid_links_and_exemptions(self):
        written = {
            "a.html": '<a href="b.html#there">x</a> <a href="https://x.example/">y</a>'
                      ' <a href="mailto:s@example">z</a>',
            "b.html": '<p id="there">hi</p>',
        }
        bp.check_internal_links(written)  # must not raise


class TestPaymentUrls(unittest.TestCase):
    def test_live_url_passes(self):
        self.assertEqual(
            bp.payment_url("https://buy.stripe.com/abc123", "payment_link"),
            "https://buy.stripe.com/abc123")

    def test_empty_is_allowed(self):
        self.assertEqual(bp.payment_url("", "payment_link"), "")

    def test_test_path_refused(self):
        with self.assertRaises(SystemExit):
            bp.payment_url("https://buy.stripe.com/test_a1b2c3", "payment_link")

    def test_dashboard_refused(self):
        with self.assertRaises(SystemExit):
            bp.payment_url("https://dashboard.stripe.com/links", "payment_link")

    def test_plain_http_refused(self):
        with self.assertRaises(SystemExit):
            bp.payment_url("http://buy.stripe.com/abc", "payment_link")

    def test_non_stripe_host_is_a_note_not_a_gate(self):
        # A non-Stripe checkout host is allowed but flagged in the build log;
        # only misconfigured *Stripe* states are hard failures.
        self.assertEqual(
            bp.payment_url("https://example.com/pay", "payment_link"),
            "https://example.com/pay")


class TestBrowserBreakableSet(unittest.TestCase):
    def test_members_exist_and_are_registered(self):
        from buttcrack.ciphers import all_ciphers
        names = {c.info.name for c in all_ciphers()}
        for name in wc.BROWSER_BREAKABLE:
            self.assertIn(name, names, f"BROWSER_BREAKABLE names {name!r}, not a cipher")

    def test_hand_written_m94_is_full_version(self):
        # The M-94 article says the browser build cannot break it; the chip
        # and category logic must agree.
        self.assertNotIn("m94", wc.BROWSER_BREAKABLE)


if __name__ == "__main__":
    unittest.main()
