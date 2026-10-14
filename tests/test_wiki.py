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

import collections
import contextlib
import importlib.util
import io
import random
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


class TestPublicSolverExperience(unittest.TestCase):
    def test_simple_shell_advanced_controls_and_optional_history(self):
        shell = bp.solver_html()
        self.assertIn('id="solver"', shell)
        self.assertIn('id="go"', shell)
        self.assertIn('id="advanced-settings"', shell)
        self.assertNotIn('<details open', shell)
        self.assertIn('id="solver-method"', shell)
        self.assertIn('id="solver-key"', shell)
        self.assertIn('Nothing is saved unless', shell)
        self.assertIn('id="save-attempt"', bp.session_html())

    def test_query_links_still_validate_their_real_target_and_fragment(self):
        bp.check_internal_links({"index.html": '<section id="solver"></section>', "wiki.html": '<a href="index.html?cipher=caesar&amp;example=caesar#solver">Try</a>'})
        with self.assertRaises(SystemExit):
            bp.check_internal_links({"index.html": '<section id="solver"></section>', "wiki.html": '<a href="index.html?cipher=caesar#missing">Try</a>'})

    def test_navigation_keeps_primary_destinations_and_folds_secondary_tools(self):
        markup = bp.nav("index.html")
        self.assertIn('class="more-tools"', markup)
        self.assertIn('href="cipher-wiki.html"', markup)
        self.assertIn('href="kryptos/"', markup)
        self.assertIn('aria-current="page"', markup)


class TestSpecCoversRegistry(unittest.TestCase):
    def test_every_cipher_has_a_spec(self):
        specs = wc.cipher_page_specs()
        by_slug = {s["slug"]: s for s in specs}
        for name in wc.HAND_WRITTEN:
            self.assertNotIn(wc.wiki_slug(name), by_slug, f"{name} is hand-written; a generated spec would shadow it")
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
            self.assertLessEqual(len(spec["desc"]), 165, f"{spec['slug']} description is {len(spec['desc'])} chars")

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
            ciphertext = cipher.encrypt(sample, key) if key not in (None, "") else cipher.encrypt(sample)
            expected = ciphertext if len(ciphertext) <= 240 else ciphertext[:237] + "..."
            self.assertEqual(shown, expected, f"{name}: worked example is not the cipher's own output")
            self.assertGreater(len(plaintext), 0)
            checked += 1
        self.assertGreaterEqual(checked, 40, "expected examples for most ciphers")


class TestUnsolvedArchive(unittest.TestCase):
    def test_archive_is_sourced_and_has_explicit_boundaries(self):
        archive = bp.UNSOLVED_ARCHIVE
        self.assertEqual(len(archive), 7)
        self.assertEqual(len({item["title"] for item in archive}), len(archive))
        for item in archive:
            self.assertTrue(item["source_url"].startswith("https://"))
            self.assertTrue(item["source_label"])
            self.assertTrue(item["boundary"])

    def test_archive_page_is_a_wiki_spec(self):
        spec = next((item for item in bp.WIKI_PAGES if item["slug"] == "unsolved-ciphers.html"), None)
        self.assertIsNotNone(spec)
        self.assertIn("Verification boundary", spec["body"])
        self.assertIn("D’Agapeyeff Cipher", spec["body"])
        self.assertIn("Phaistos Disc", spec["body"])

    def test_findings_are_measured_not_asserted(self):
        """A findings block may only quote a number the shipped script reproduces."""
        entry = next(i for i in bp.UNSOLVED_ARCHIVE if "findings" in i)
        self.assertIn("dagapeyeff_alignment.py", " ".join(entry["findings"]))
        align = _load(
            "dagapeyeff_alignment_test",
            VENTURE.parents[1] / "scripts" / "dagapeyeff_alignment.py",
        )
        result = align.analyse(align.digits(align.CANONICAL), align.random.Random(1))
        self.assertEqual(result["violations"], 0)
        self.assertEqual(result["shuffle_passes"], 0)
        self.assertEqual(result["cells_used"], 19)
        self.assertEqual(result["leftover"], "0")
        self.assertEqual(result["firsts"], ["0", "6", "7", "8", "9"])
        self.assertEqual(result["seconds"], ["0", "1", "2", "3", "4", "5"])
        # The card's frequency claim, straight from the script.
        counts = dict(result["frequencies"])
        self.assertEqual(counts["81"], 20)
        self.assertEqual(result["distinct"], 19)

    def test_detect_harness_streams_match_the_attack_they_document(self):
        """The card quotes a ceiling/null/CT comparison; keep the inputs honest."""
        detect = _load(
            "dagapeyeff_detect_test",
            VENTURE.parents[1] / "scripts" / "dagapeyeff_detect.py",
        )
        ct = detect.ciphertext_stream()
        self.assertEqual(len(ct), 197)
        self.assertEqual(sorted(set(ct)), list(range(detect.NS)))
        for profile in (detect.CT_PROFILE, detect.ENGLISH_PROFILE):
            self.assertEqual(sum(profile), 197, "a null of another length is not a control")
        # the control must be a permutation of the cipher's own counts, else
        # "same profile" is a claim the code does not actually honour
        null = detect.profile_stream(detect.CT_PROFILE, 197, random.Random(1))
        self.assertEqual(sorted(collections.Counter(null).values()),
                         sorted(collections.Counter(ct).values()))
        self.assertEqual(sorted(detect.CT_PROFILE, reverse=True),
                         sorted(collections.Counter(ct).values(), reverse=True))
        with self.assertRaises(ValueError):
            detect.profile_stream([1, 2, 3], 197, random.Random(1))
        table = detect.quad_table()
        self.assertEqual(len(table), 26**4)
        slot = lambda w: sum((ord(c) - 65) * 26**k for k, c in enumerate(reversed(w)))
        self.assertGreater(table[slot("TION")], table[slot("QZJX")])
        # the python fallback has to run and stay in the sane range
        score = detect.anneal_py(ct[:60], table, 2, 2000, 3)
        self.assertTrue(-8.0 <= score <= -2.5, f"fallback scorer out of range: {score}")

    def test_no_doubling_rejection_is_a_proof_not_a_p_value(self):
        """The Playfair-family test must stay a hard logical test."""
        detect = _load(
            "dagapeyeff_detect_hard_test",
            VENTURE.parents[1] / "scripts" / "dagapeyeff_detect.py",
        )
        # a real no-doubling plaintext through an injective code: zero repeats
        playfair_like = list("ATBUCV.DWEFXGY.HZJ.QKWLRI.MNSOTP")
        self.assertEqual([a for a, b in zip(playfair_like, playfair_like[1:]) if a == b], [])
        adj, _, verdict = detect.doubled_letter_cipher_rejected(playfair_like)
        self.assertEqual(adj, 0)
        self.assertTrue(verdict.startswith("consistent"))
        # and one doubled letter anywhere is enough to reject the family
        adj2, longest, verdict2 = detect.doubled_letter_cipher_rejected(
            list("ABBCDEF"))
        self.assertEqual(adj2, 1)
        self.assertEqual(longest, 2)
        self.assertTrue(verdict2.startswith("REJECTED"))
        # the actual cipher: the family is gone, and it is a counted fact, not a model
        adj3, longest3, verdict3 = detect.doubled_letter_cipher_rejected(
            detect.ciphertext_stream())
        self.assertEqual(adj3, 17)
        self.assertEqual(longest3, 3)
        self.assertIn("REJECTED", verdict3)

    def test_findings_render_as_balanced_markup(self):
        markup = bp.unsolved_archive_html()
        self.assertIn("unsolved-findings", markup)
        self.assertIn("What holds up", markup)
        self.assertEqual(markup.count("<ul>"), markup.count("</ul>"))
        self.assertEqual(markup.count("<li>"), markup.count("</li>"))
        self.assertEqual(markup.count("<section"), markup.count("</section>"))
        # Only entries that actually carry findings grow the box.
        for item in bp.UNSOLVED_ARCHIVE:
            title = f"<h3>{item['title']}</h3>"
            block = markup.split(title, 1)[1].split("</section>", 1)[0]
            self.assertEqual("unsolved-findings" in block, bool(item.get("findings")), item["title"])


class TestTableOfContents(unittest.TestCase):
    def test_anchors_exist_and_nest(self):
        body = '<h2>One</h2><p>x</p><h3>Deep</h3><p>y</p><h2 id="kept">Two</h2><h3 data-notoc>Hidden</h3>'
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
        self.assertIn('<ul><li><a href="#deep">Deep</a></li></ul></li>', toc)

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
        written = {"a.html": '<a href="b.html#nowhere">x</a>', "b.html": "<p>no ids</p>"}
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
            bp.payment_url("https://buy.stripe.com/abc123", "payment_link"), "https://buy.stripe.com/abc123"
        )

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
        self.assertEqual(bp.payment_url("https://example.com/pay", "payment_link"), "https://example.com/pay")


class TestDeliveryUrls(unittest.TestCase):
    """The installer URL a buyer has just paid $39.99 to reach.

    ``payment_url`` protects the *sale*; these protect the *delivery*. A sale
    that completes and delivers nothing is the worse failure of the two, because
    Stripe reports it as an ordinary successful payment and the only evidence is
    a customer who cannot find their download.
    """

    def setUp(self):
        bp.CONFIG_WARNINGS.clear()

    def test_https_passes_unchanged(self):
        url = "https://downloads.example.com/buttcrack-setup-1.2.1-abc.exe"
        self.assertEqual(bp.delivery_url(url, "delivery_url"), url)
        self.assertEqual(bp.CONFIG_WARNINGS, [])

    def test_empty_is_allowed(self):
        # An empty URL is legal — the delivery page falls back to promising the
        # file by email rather than rendering a dead button.
        self.assertEqual(bp.delivery_url("", "delivery_url"), "")

    def test_plain_http_refused(self):
        with self.assertRaises(SystemExit):
            bp.delivery_url("http://downloads.example.com/app.exe", "delivery_url")

    def test_not_a_url_refused(self):
        with self.assertRaises(SystemExit):
            bp.delivery_url("downloads.example.com/app.exe", "delivery_url")

    def test_self_hosting_refused(self):
        # Serving the paid installer from the public site hands it to everyone.
        with self.assertRaises(SystemExit):
            bp.delivery_url(f"{bp.CFG['base_url']}/files/buttcrack-setup.exe", "delivery_url")

    def test_r2_dev_hostname_warns_but_is_not_a_gate(self):
        # docs/windows-installer.md allows r2.dev as the quickest first-run path,
        # so it warns rather than fails — but a live sale on it must be loud,
        # because it is rate-limited, ISP-blockable, and a second public URL for
        # an object whose unguessable name is the entire paywall.
        url = "https://pub-067dfa932fcd43178eed7d93d56634f7.r2.dev/buttcrack-setup-1.2.1-abc.exe"
        self.assertEqual(bp.delivery_url(url, "delivery_url"), url)
        self.assertEqual(len(bp.CONFIG_WARNINGS), 1)
        self.assertIn("r2.dev", bp.CONFIG_WARNINGS[0])
        self.assertIn("custom domain", bp.CONFIG_WARNINGS[0])

    def test_custom_domain_on_r2_is_clean(self):
        url = "https://downloads.example.com/buttcrack-setup-1.2.1-abc.exe"
        self.assertEqual(bp.delivery_url(url, "delivery_url"), url)
        self.assertEqual(bp.CONFIG_WARNINGS, [])

    def test_warnings_are_deduplicated_when_printed(self):
        # windows_app_config() runs once per page that renders the product, so
        # the same URL is validated several times per build.
        for _ in range(3):
            bp.delivery_url("https://pub-abc123.r2.dev/app.exe", "delivery_url")
        self.assertEqual(len(list(dict.fromkeys(bp.CONFIG_WARNINGS))), 1)


class TestWindowsDeliveryPage(unittest.TestCase):
    """The committed post-payment page must match site.json and the salt.

    The page is ``noindex`` and linked from nowhere, so no link checker and no
    search console ever looks at it. These assertions are the only thing that
    notices if the button on it points at a file that is no longer the one
    ``site.json`` advertises.
    """

    def test_page_name_is_derived_from_sku_and_salt(self):
        cfg = bp.windows_app_config()
        expected = bp.CFG["base_url"] + "/" + cfg["delivery_page"]
        self.assertRegex(cfg["delivery_page"], r"^thank-you-[0-9a-f]{20}\.html$")
        # set_payment_links.py must derive the same URL it tells the author to
        # paste into Stripe, or the two tools disagree about where buyers land.
        spl = _load("set_payment_links_test_module", VENTURE / "set_payment_links.py")
        self.assertEqual(spl.delivery_url(bp.CFG, cfg.get("sku", "winapp")), expected)

    def test_committed_page_carries_the_configured_installer(self):
        cfg = bp.windows_app_config()
        page = VENTURE / cfg["delivery_page"]
        self.assertTrue(page.exists(), f"{cfg['delivery_page']} is not committed; run build_pages.py")
        body = page.read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', body)
        if cfg["delivery_url"]:
            self.assertIn(f'href="{cfg["delivery_url"]}"', body)
        else:
            self.assertNotIn("Download the installer", body)

    def test_report_lists_the_windows_app(self):
        # --show is the documented way to reprint the redirect URLs. Omitting the
        # most expensive product from it is how its redirect goes unchecked.
        spl = _load("set_payment_links_test_module", VENTURE / "set_payment_links.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            spl.report(bp.CFG)
        text = out.getvalue()
        cfg = bp.windows_app_config()
        self.assertIn("Windows app", text)
        self.assertIn(f"{bp.CFG['base_url']}/{cfg['delivery_page']}", text)


class TestAdSense(unittest.TestCase):
    """The loader tag has to be on every page, and identical on both halves.

    AdSense reviews the site, not the repository: a page that does not load
    adsbygoogle.js shows no ads, and a publisher ID that differs between the
    generated pages and the hand-written Kryptos app is a bug nobody would
    notice until the revenue did not arrive.
    """

    def setUp(self):
        self.client = bp.CFG["adsense_client"]
        if not self.client:
            self.skipTest("no adsense_client configured in site.json")

    def test_loader_is_googles_snippet(self):
        head = bp.adsense_head()
        self.assertIn(f"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={self.client}", head)
        self.assertIn("async", head)
        self.assertIn('crossorigin="anonymous"', head)

    def test_client_id_looks_like_a_publisher_id(self):
        self.assertRegex(self.client, r"^ca-pub-\d{16}$")

    def test_build_site_injects_the_same_tag(self):
        # scripts/build_site.py adds the tag to the hand-written Kryptos page.
        # It must be byte-for-byte the generated one, from the same site.json.
        build_site = _load(
            "build_site_test_module", Path(__file__).resolve().parents[1] / "scripts" / "build_site.py"
        )
        self.assertEqual(build_site.adsense_loader().strip(), bp.adsense_head().strip())

    def test_injection_is_idempotent(self):
        import tempfile

        build_site = _load(
            "build_site_test_module2", Path(__file__).resolve().parents[1] / "scripts" / "build_site.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_text("<html><head><title>t</title></head><body></body></html>")
            self.assertEqual(build_site.inject_adsense(Path(tmp)), 1)
            once = page.read_text()
            self.assertIn("adsbygoogle.js", once)
            self.assertIn("adsbygoogle.js", once.split("</head>")[0])
            # A second pass must not add it twice.
            self.assertEqual(build_site.inject_adsense(Path(tmp)), 0)
            self.assertEqual(page.read_text(), once)

    def test_no_stale_placeholder_once_configured(self):
        # The placeholder names adsense_client as the thing to configure; with
        # a client set it would be visible to visitors and wrong.
        self.assertNotIn("configure adsense_client", bp.ad_slot())


class TestCustomDomain(unittest.TestCase):
    """base_url is the single source of truth for where the site lives.

    Three things have to agree with it and none of them fails loudly:
    the CNAME file in the artifact, the hand-written Kryptos canonical, and
    ads.txt. Each is a one-line file whose absence costs the domain, the
    search ranking or the ad revenue, silently.
    """

    def setUp(self):
        self.build_site = _load(
            "build_site_domain_module", Path(__file__).resolve().parents[1] / "scripts" / "build_site.py"
        )
        self.base = bp.CFG["base_url"]

    def test_cname_matches_base_url(self):
        from urllib.parse import urlparse

        host = urlparse(self.base).hostname
        if host.endswith(".github.io"):
            self.assertEqual(self.build_site.custom_domain(), "", "a github.io base_url must produce no CNAME")
        else:
            self.assertEqual(self.build_site.custom_domain(), host)

    def test_cname_is_written_into_the_tree(self):
        # Without this file an Actions deploy clears the custom domain stored
        # in repository settings, and the site silently reverts to github.io.
        import tempfile
        from urllib.parse import urlparse

        host = urlparse(self.base).hostname
        with tempfile.TemporaryDirectory() as tmp:
            written = self.build_site.write_cname(Path(tmp))
            cname = Path(tmp) / "CNAME"
            if host.endswith(".github.io"):
                self.assertFalse(cname.exists())
            else:
                self.assertEqual(written, host)
                self.assertEqual(cname.read_text().strip(), host)
                self.assertNotIn("/", cname.read_text(), "a CNAME holds a bare hostname, not a URL")

    def test_kryptos_canonical_matches_base_url(self):
        # kryptos-app is hand-written: nothing regenerates this URL, so it can
        # only be kept honest by being checked.
        page = (Path(__file__).resolve().parents[1] / "kryptos-app" / "index.html").read_text(encoding="utf-8")
        expected = f'<link rel="canonical" href="{self.base}/kryptos/">'
        self.assertIn(expected, page, "kryptos-app/index.html canonical is out of step with base_url")
        self.assertIn(f'content="{self.base}/kryptos/"', page)

    def test_ads_txt_only_on_a_real_domain(self):
        from urllib.parse import urlparse

        host = urlparse(self.base).hostname
        line = bp.write_ads_txt()
        if not bp.CFG["adsense_client"] or host.endswith(".github.io"):
            # ads.txt is only read at the domain root, which a project page
            # does not own; writing one there would be false confidence.
            self.assertEqual(line, "")
        else:
            self.assertRegex(line, r"^google\.com, pub-\d{16}, DIRECT, [0-9a-f]{16}$")
            self.assertIn(bp.CFG["adsense_client"].removeprefix("ca-"), line)


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
