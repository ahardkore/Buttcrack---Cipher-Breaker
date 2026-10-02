"""Generate the static site: one hub page plus a landing page per cipher.

Every page ships the same solver; they differ in copy, title and the example
that is preloaded. Separate pages exist because search traffic arrives on
specific queries ("vigenere cipher solver", "decode caesar cipher online"),
and that traffic is the entire monetisation story for this venture.

Monetisation IDs live in site.json so nothing here needs editing to go live:
fill in the AdSense/Ko-fi fields, re-run this script, push.

    python3 ventures/cipher-solver-web/build_pages.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
PACKS = HERE.parent / "puzzle-packs"
sys.path.insert(0, str(PACKS))
CFG = json.loads((HERE / "site.json").read_text())

#: The Kryptos research explorer lives in ``kryptos-app/`` and is mounted as a
#: sub-directory of this site by ``scripts/build_site.py``. Keep the two in
#: step: this href is what makes the two web surfaces one site rather than two.
KRYPTOS_HREF = "kryptos/"

NAV = [
    ("index.html", "Solver"),
    ("cipher-wiki.html", "Cipher wiki"),
    ("history-of-codebreaking.html", "History"),
    ("windows-app.html", "Windows app"),
    ("downloads.html", "Puzzle books"),
    ("caesar-cipher-decoder.html", "Caesar"),
    ("vigenere-cipher-solver.html", "Vigenère"),
    ("substitution-cipher-solver.html", "Substitution"),
    ("morse-code-translator.html", "Morse"),
    ("ctf-crypto-solver.html", "CTF crypto"),
    (KRYPTOS_HREF, "Kryptos"),
]


def adsense_head() -> str:
    if not CFG["adsense_client"]:
        return ""
    return (
        '\n  <script async crossorigin="anonymous" '
        f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={CFG["adsense_client"]}">'
        "</script>"
    )


def analytics() -> str:
    if not CFG["plausible_domain"]:
        return ""
    return (
        f'\n  <script defer data-domain="{CFG["plausible_domain"]}" '
        'src="https://plausible.io/js/script.js"></script>'
    )


#: Ownership tokens are pasted in by hand from a dashboard, and the two ways to
#: get that wrong are pasting the whole ``<meta>`` tag and pasting the *file*
#: method's contents into the *tag* field. Both are caught here rather than
#: producing a page that looks fine and fails verification a week later.
_META_CONTENT = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)


def verification_token(raw: str, field: str) -> str:
    """Normalise a pasted ownership token to the bare value for ``content``."""
    text = (raw or "").strip()
    if not text:
        return ""

    tag = _META_CONTENT.search(text)
    if tag:                                  # they pasted the entire <meta> tag
        text = tag.group(1).strip()

    # "google-site-verification: google1234.html" is the *body of the HTML file*,
    # not a meta token. Used as a tag it verifies nothing.
    if text.lower().startswith("google-site-verification:"):
        filename = text.split(":", 1)[1].strip()
        raise SystemExit(
            f"site.json: {field} holds the contents of Google's verification *file*, "
            f"not the meta tag's token.\n"
            f"Either paste the token from the 'HTML tag' method instead, or use the "
            f'file method:\n    "verification_files": {{"{filename}": "{text}"}}'
        )

    if "<" in text or '"' in text:
        raise SystemExit(f"site.json: {field} contains markup that is not a token: {text!r}")
    return text


def verification_meta() -> str:
    """Ownership meta tags for every indexable page."""
    tags = []
    google = verification_token(CFG.get("google_site_verification", ""), "google_site_verification")
    if google:
        tags.append(("google-site-verification", google))
    for name, raw in (CFG.get("verification") or {}).items():
        if name.startswith("_"):
            continue
        token = verification_token(raw, f"verification.{name}")
        if token:
            tags.append((name, token))
    if not tags:
        return ""
    return "\n" + "\n".join(
        f'<meta name="{html_escape(name)}" content="{html_escape(token)}">' for name, token in tags
    )


def write_verification_files() -> list[str]:
    """Write the 'HTML file' style ownership proofs to the site root."""
    written = []
    for name, body in (CFG.get("verification_files") or {}).items():
        if name.startswith("_"):
            continue
        # Keep these at the site root and out of subdirectories: a verifier only
        # ever fetches https://host/<name>, and "../" here would escape the site.
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise SystemExit(f"site.json: verification_files key {name!r} must be a bare filename")
        (HERE / name).write_text(body if body.endswith("\n") else body + "\n")
        written.append(name)
    return written


def ad_slot() -> str:
    """A real ad unit once IDs are configured; an inert placeholder until then."""
    if not (CFG["adsense_client"] and CFG["adsense_slot"]):
        return '<div class="ad-slot">ad slot — configure adsense_client in site.json</div>'
    return f"""<ins class="adsbygoogle" style="display:block"
     data-ad-client="{CFG['adsense_client']}"
     data-ad-slot="{CFG['adsense_slot']}"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>"""


#: Hosts a live Stripe Payment Link can legitimately be served from. Custom
#: domains are possible, so an unknown host warns rather than fails; the checks
#: that *do* fail are the ones that mean "this button takes no money".
_STRIPE_HOSTS = ("buy.stripe.com", "pay.stripe.com", "checkout.stripe.com")


def payment_url(raw: str, field: str) -> str:
    """Validate a pasted Stripe URL. Returns "" when the field is unset.

    A wrong payment URL is the most expensive kind of typo on this site: the
    page looks finished, the button is there, and every click is a lost sale.
    So each known way of getting it wrong is refused at build time, where the
    message can say what to paste instead.
    """
    url = (raw or "").strip()
    if not url:
        return ""

    if url.startswith("http://"):
        raise SystemExit(f"site.json: {field} must be https, not http: {url}")
    if not url.startswith("https://"):
        raise SystemExit(
            f"site.json: {field} is not a URL: {url!r}\n"
            f"Paste the whole link Stripe shows, starting with https://buy.stripe.com/"
        )

    host = url[len("https://"):].split("/", 1)[0].split("?", 1)[0].lower()
    path = url[len("https://") + len(host):]

    # The dashboard URL is what your browser shows while you *edit* the link;
    # it is behind your login and useless to a customer.
    if host.endswith("dashboard.stripe.com"):
        raise SystemExit(
            f"site.json: {field} is a Stripe dashboard URL, not the public payment link.\n"
            f"Open the payment link in the dashboard and copy the URL under "
            f'"Share" / the copy-link button instead (https://buy.stripe.com/).'
        )

    # Test mode takes fake cards and pays you nothing. Shipping one to a live
    # site is silent: the checkout works perfectly and no money ever arrives.
    if path.startswith("/test_") or "/test_" in path:
        raise SystemExit(
            f"site.json: {field} is a TEST-mode payment link ({url}).\n"
            f"Toggle off test mode in Stripe, recreate the link, and paste the live one."
        )

    if not any(host == h or host.endswith("." + h) for h in _STRIPE_HOSTS):
        print(f"  note: {field} is not a stripe.com host ({host}) — assuming a custom domain")

    return url


def support_block() -> str:
    buttons = []
    if CFG["github_sponsor"]:
        buttons.append(
            f'<a class="btn primary" rel="noopener" target="_blank" '
            f'href="https://github.com/sponsors/{CFG["github_sponsor"]}">Sponsor on GitHub</a>'
        )
    if CFG["kofi_handle"]:
        buttons.append(
            f'<a class="btn" rel="noopener" target="_blank" '
            f'href="https://ko-fi.com/{CFG["kofi_handle"]}">Buy me a coffee</a>'
        )
    # Validated like the product links: the tip button is on every page, so a
    # broken URL here is the most visible dead link on the site.
    tip = payment_url(CFG.get("stripe", {}).get("tip_jar_url", ""), "stripe.tip_jar_url")
    if tip:
        buttons.append(f'<a class="btn" rel="noopener" target="_blank" href="{tip}">Leave a tip</a>')
    buttons.append(f'<a class="btn" rel="noopener" target="_blank" href="{CFG["repo_url"]}">Star on GitHub</a>')
    return f"""<section class="support">
      <h3>This tool is free and has no account, no upload, no tracking of your text</h3>
      <p>Everything runs in your browser. If it saved you time, keeping it alive costs nothing but a click.</p>
      <div class="btns">{''.join(buttons)}</div>
    </section>"""


def nav(current: str) -> str:
    here = ' aria-current="page"'
    links = "".join(
        f'<a href="{href}"{here if href == current else ""}>{label}</a>'
        for href, label in NAV
    )
    return f'<nav class="tools">{links}</nav>'


def faq_jsonld(faqs: list[tuple[str, str]]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def app_jsonld(title: str, desc: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": title,
        "description": desc,
        "applicationCategory": "SecurityApplication",
        "operatingSystem": "Any",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def article_jsonld(h1: str, desc: str, family_title: str) -> str:
    """Wiki articles are articles, not applications: say so to the crawlers."""
    data = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": h1,
        "description": desc,
        "inLanguage": "en",
        "isAccessibleForFree": True,
    }
    if family_title:
        data["articleSection"] = family_title
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def buy_button_script(body: str) -> str:
    """Stripe's script, included only on a page that actually uses the button."""
    if "<stripe-buy-button" not in body:
        return ""
    return '\n  <script async src="https://js.stripe.com/v3/buy-button.js"></script>'


# --------------------------------------------------------------------------
# The cipher wiki
#
# Fifty-plus encyclopedia articles rendered in a Wikipedia-shaped layout:
# left navigation sidebar with a live search box, an article card with a
# serif title, an infobox of registry facts floated right, an auto-built
# table of contents, blue in-article links and a category bar at the foot.
# The solver rides along below the article so every page still breaks ciphers.
# --------------------------------------------------------------------------

#: The order families appear in across the wiki, matching the solver's own
#: "ciphers" table (shifts first, encodings last).
WIKI_FAMILY_ORDER = [
    "shift", "substitution", "polyalphabetic", "transposition",
    "polygraphic", "wheel", "xor", "code", "encoding",
]

#: "Did you know…" items for the wiki main page. Every claim is one the site
#: can back: it comes from an article or from the solver's own registry.
DYK_FACTS = [
    "…that al-Kindi, in ninth-century Baghdad, wrote the first known account of cryptanalysis — and made every monoalphabetic cipher obsolete in the same stroke?",
    "…that Charles Babbage broke the Vigenère cipher around 1854 and never published a word of it?",
    "…that Marian Rejewski reconstructed the internal wiring of the Enigma machine in 1932 using mathematics alone, never having seen one?",
    "…that Bill Tutte deduced the entire structure of the Lorenz SZ40 cipher machine from a single mis-sent message?",
    "…that Colossus, built to break Lorenz traffic, was the first electronic digital computer — and stayed classified for thirty years?",
    "…that the M-94's twenty-five disk alphabets were engraved on every device manufactured? Only the order the disks were threaded in was secret.",
    "…that Johannes Trithemius's <em>Steganographia</em> looked so much like sorcery that it spent two centuries on the Index?",
    "…that Morse code's letter lengths reportedly came from counting type in a printer's case — which is why E is a single dot?",
    "…that the Atbash cipher appears in the Book of Jeremiah, where Babel is written as Sheshach?",
    "…that the Playfair cipher is named for the man who promoted it, not the man who invented it? Charles Wheatstone designed it in 1854.",
    "…that a correctly used one-time pad is the only cipher with a proof of perfect secrecy — and the Venona decrypts exist because Soviet clerks reused pad material?",
    "…that Kryptos K4, ninety-seven characters on a sculpture at CIA headquarters, has resisted public solution since 1990?",
    "…that the Zodiac killer's Z340 cipher fell only in 2020, and turned out to be a transposition wrapped around a homophonic substitution?",
    "…that the tap code was taught through the walls of the Hanoi Hilton in 1965, and carried messages for years?",
]

#: The rotating "featured article" pool for the wiki main page.
FEATURED_ARTICLES = [
    ("The Caesar cipher", "caesar-cipher-wiki.html",
     "A rotation so small it teaches nearly every idea behind classical cryptanalysis — and the first thing this solver tries on unknown text."),
    ("The Vigenère cipher", "vigenere-cipher-wiki.html",
     "Misattributed for centuries and called <em>le chiffre indéchiffrable</em>, until the repetition of its keyword gave the game away."),
    ("The M-94 wheel cipher", "m94-wheel-cipher.html",
     "Twenty-five mixed alphabets on a spindle: the US Army's field cipher from 1922, with a keyspace of 25! disk orders — and how they fall."),
    ("The Playfair cipher", "playfair-cipher-wiki.html",
     "A 5×5 keyed grid that encrypts letter pairs, flattening single-letter statistics three centuries before anyone called them that."),
    ("The Hill cipher", "hill-cipher-wiki.html",
     "Lester Hill's 1929 matrix cipher: the first built on linear algebra, and a standing lesson in why linearity and secrecy sit badly together."),
    ("The Quagmire III cipher", "quagmire3-cipher-wiki.html",
     "Vigenère arithmetic in a keyed alphabet — the form used on the Kryptos sculpture at CIA headquarters."),
    ("The autokey cipher", "autokey-cipher-wiki.html",
     "Vigenère's own 1586 idea, genuinely stronger than the cipher that took his name — and the one nobody used."),
    ("The Bifid cipher", "bifid-cipher-wiki.html",
     "Delastelle's fractionating cipher, smearing each plaintext letter across two ciphertext letters within a period."),
    ("A history of codebreaking", "history-of-codebreaking.html",
     "Frequency analysis in ninth-century Baghdad to Colossus in 1944 — every technique in this solver has an inventor and a date."),
    ("Famous ciphers", "famous-ciphers.html",
     "The Great Cipher, the Zimmermann Telegram, Enigma and Lorenz — and the handful of messages nobody has read yet."),
]

def wiki_article_note(wiki: dict) -> str:
    """The Wikipedia-style 'this page was last edited' footer, honestly worded
    for each kind of page: cipher articles carry registry-generated facts, the
    history features are editorial, and the main page is both."""
    repo = CFG["repo_url"]
    if wiki.get("is_hub"):
        return (
            '<div class="wiki-article-note">Cipher articles on this wiki are generated from '
            f'<a href="{repo}">buttcrack</a>&#39;s cipher registry when the site is built — their '
            "facts tables, worked examples and infoboxes describe the implementation, not an "
            "idealised cipher. The history features are editorial. The full source is on GitHub."
            "</div>"
        )
    if wiki.get("family") == "history":
        return (
            '<div class="wiki-article-note">This feature is editorial. Where the record is '
            "disputed — who invented the Vigenère cipher, whether the Beale papers are genuine "
            "— the text says so rather than picking the tidy version.</div>"
        )
    return (
        '<div class="wiki-article-note">The facts in this article are generated from '
        f'<a href="{repo}">buttcrack</a>&#39;s cipher registry when the site is built, so they '
        "describe the implementation you can run on this page. Registry-generated content is "
        "checked against the code; the history is editorial.</div>"
    )


_H_RE = re.compile(r"<h([23])([^>]*)>(.*?)</h\1>", re.S)


def _tocify(entries: list, seen: dict[str, int]):
    """The heading rewriter: id it, anchor it, list it, in document order.

    One regex for both levels (rather than one pass per level) so ``entries``
    comes out in the order the headings appear in the body — the nesting pass
    after it depends on that.
    """
    def repl(m: re.Match) -> str:
        level, attrs, text = m.group(1), m.group(2), m.group(3).strip()
        if "data-notoc" in attrs:
            return f"<h{level}{attrs}>{text}</h{level}>"
        plain = re.sub(r"<[^>]+>", "", text)
        existing = re.search(r'id="([^"]+)"', attrs)
        if existing:
            anchor = existing.group(1)
        else:
            base = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or "section"
            n = seen.get(base, 0)
            seen[base] = n + 1
            anchor = base if n == 0 else f"{base}-{n}"
        entries.append((int(level), anchor, plain))
        return (f'<h{level} id="{anchor}">{text}'
                f'<a class="section-anchor" href="#{anchor}" aria-label="Link to this section">§</a></h{level}>')
    return repl


def with_toc(body: str) -> tuple[str, str]:
    """Give every h2/h3 an anchor id and build a nested contents box.

    The table of contents is generated from the article body rather than
    written by hand, so a section can never go missing from it — the same
    discipline as the infobox, applied to navigation. A heading that already
    carries an id (the wiki main page's family sections) keeps it, so links
    from the sidebar and category bars stay stable. A heading marked
    ``data-notoc`` (the main page's rotating featured-article title) is left
    alone entirely: its text changes daily in the browser, so a TOC entry for
    it would be stale by definition.
    """
    entries: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}
    new_body = _H_RE.sub(_tocify(entries, seen), body)
    if not entries:
        return new_body, ""

    # Nest h3s under the h2 that precedes them, Wikipedia-style. An h3 that
    # appears before any h2 (none today, but the template is data-driven)
    # becomes a top-level entry rather than being dropped.
    root: list[list] = []
    current_children: list = root
    for level, anchor, plain in entries:
        item = [anchor, plain, []]
        if level == 2:
            root.append(item)
            current_children = item[2]
        else:
            current_children.append(item)

    def render(items: list) -> str:
        out = []
        for anchor, plain, children in items:
            link = f'<a href="#{anchor}">{plain}</a>'
            if children:
                out.append(f"<li>{link}<ul>{render(children)}</ul></li>")
            else:
                out.append(f"<li>{link}</li>")
        return "".join(out)

    toc = (
        '<nav class="wiki-toc" aria-label="Contents">\n'
        '        <div class="wiki-toc-title">Contents</div>\n'
        f'        <ul>{render(root)}</ul>\n'
        "      </nav>"
    )
    return new_body, toc


def wiki_sidebar(current: str) -> str:
    """The Wikipedia-style left rail: search, navigation, every cipher, tools."""
    from wiki_ciphers import FAMILY_TITLES, wiki_slug

    from buttcrack.ciphers import all_ciphers

    by_family: dict[str, list] = {}
    for cipher in all_ciphers():
        by_family.setdefault(cipher.info.family.value, []).append(cipher)

    def link(href: str, label: str) -> str:
        cur = ' aria-current="page"' if href == current else ""
        return f'<li><a href="{href}"{cur}>{label}</a></li>'

    family_blocks = []
    for family in WIKI_FAMILY_ORDER:
        ciphers = sorted(by_family.get(family, []), key=lambda c: c.info.title)
        if not ciphers:
            continue
        items = "".join(
            link(wiki_slug(c.info.name), c.info.title) for c in ciphers
        )
        family_blocks.append(
            f'      <details class="wiki-side-group" open>\n'
            f'        <summary><a href="cipher-wiki.html#family-{family}">'
            f'{FAMILY_TITLES.get(family, family)}</a><span class="side-count">'
            f'{len(ciphers)}</span></summary>\n'
            f'        <ul>\n{items}\n        </ul>\n'
            f'      </details>'
        )

    history_links = (
        link("history-of-codebreaking.html", "History of codebreaking")
        + link("famous-cryptanalysts.html", "The codebreakers")
        + link("famous-ciphers.html", "Famous ciphers")
        + link("unsolved-ciphers.html", "Unsolved cipher archive")
    )
    tool_links = (
        link("index.html", "Cipher solver")
        + link("caesar-cipher-decoder.html", "Caesar decoder")
        + link("vigenere-cipher-solver.html", "Vigenère solver")
        + link("substitution-cipher-solver.html", "Substitution solver")
        + link("morse-code-translator.html", "Morse translator")
        + link("ctf-crypto-solver.html", "CTF crypto solver")
        + link("windows-app.html", "Windows app")
        + link("downloads.html", "Puzzle books")
        + link(KRYPTOS_HREF, "Kryptos explorer")
    )
    total = sum(len(v) for v in by_family.values())

    return f"""<aside class="wiki-side" aria-label="Wiki navigation">
      <div class="wiki-search" role="search">
        <input class="wiki-search-input" type="search" placeholder="Search the wiki"
          autocomplete="off" aria-label="Search the cipher wiki">
        <button class="wiki-search-go" type="button">Go</button>
        <div class="wiki-search-results" hidden></div>
      </div>
      <nav class="wiki-side-nav">
        <details class="wiki-side-group" open>
          <summary>Navigation<span class="side-count">4</span></summary>
          <ul>
            {link("cipher-wiki.html", "Main page")}
            {link("unsolved-ciphers.html", "Unsolved cipher archive")}
            <li><a href="cipher-wiki.html#families">Contents — all {total}</a></li>
            <li><a class="wiki-random" href="cipher-wiki.html">Random article&nbsp;↻</a></li>
          </ul>
        </details>
        <h3 class="wiki-side-heading">Cipher families</h3>
{chr(10).join(family_blocks)}
        <h3 class="wiki-side-heading">History</h3>
        <details class="wiki-side-group" open>
          <summary>Codebreaking<span class="side-count">4</span></summary>
          <ul>
{history_links}
          </ul>
        </details>
        <h3 class="wiki-side-heading">Tools</h3>
        <details class="wiki-side-group" open>
          <summary>Solver &amp; shop<span class="side-count">8</span></summary>
          <ul>
{tool_links}
          </ul>
        </details>
      </nav>
    </aside>"""


def wiki_main(slug: str, h1: str, tagline: str, body: str,
              faq_html: str, wiki: dict) -> str:
    """The encyclopedia layout: sidebar, article card, then the solver."""
    full_body = body
    if faq_html:
        full_body += f'\n    <h2>Frequently asked questions</h2>\n    {faq_html}'
    body_ids, toc = with_toc(full_body)

    from_line = tagline or ""
    if wiki.get("is_hub"):
        # The main page is the breadcrumb root: no trail above it, and the
        # "From the …" line is redundant when the page *is* the wiki.
        crumbs = ""
    else:
        crumbs = '<a href="cipher-wiki.html">Cipher wiki</a>'
        if wiki.get("family") == "history":
            crumbs += ' <span aria-hidden="true">›</span> <a href="history-of-codebreaking.html">History</a>'
        elif wiki.get("family"):
            crumbs += (f' <span aria-hidden="true">›</span> '
                       f'<a href="cipher-wiki.html#family-{wiki["family"]}">{wiki["family_title"]}</a>')
        crumbs += f' <span aria-hidden="true">›</span> <span class="crumb-here">{h1}</span>'
        from_line = "From the Buttcrack Cipher Wiki — the free field guide to classical ciphers"

    breadcrumb_html = (
        f'<nav class="wiki-breadcrumb" aria-label="Breadcrumb">{crumbs}</nav>' if crumbs else ""
    )
    categories = ""
    if wiki.get("categories"):
        cats = " | ".join(
            f'<a href="{href}">{label}</a>' for label, href in wiki["categories"]
        )
        categories = (
            '<div class="wiki-categories">'
            f'<span class="wiki-categories-label">Categories:</span> {cats}</div>'
        )

    return f"""<main class="wrap wrap-wide" id="main-content">
  <div class="wiki-layout">
{wiki_sidebar(slug)}
    <div class="wiki-content">
      <article class="wiki-article">
        {breadcrumb_html}
        <h1 class="wiki-title">{h1}</h1>
        <p class="wiki-from">{from_line}</p>
        <nav class="wiki-tabs" aria-label="Page sections">
          <span class="wiki-tab is-here" aria-current="page">Article</span>
          <a class="wiki-tab" href="#try-the-solver">Try the solver</a>
        </nav>
        <div class="wiki-article-body">
          {wiki.get("infobox", "")}
          {wiki.get("lead", "")}
          {toc}
{body_ids}
        </div>
{categories}
        {wiki_article_note(wiki)}
      </article>

      <section class="wiki-solver" id="try-the-solver" aria-label="Cipher solver">
        <h2 class="wiki-solver-title">Try it live — break a real puzzle</h2>
        {solver_html()}
      </section>

      <div id="output" aria-live="polite"></div>

      {ad_slot()}
    </div>
  </div>

  {support_block()}
</main>"""


def cipher_index_html() -> str:
    """Every registered cipher, grouped by family, linked to its page.

    Generated from the registry rather than maintained by hand, so a cipher
    added to the solver appears here without anyone remembering to add it --
    and a link can never point at a page that was not written. Ciphers the
    browser build cannot break carry a "full version" chip, which is exactly
    what the intro paragraph above the index promises.
    """
    from wiki_ciphers import BROWSER_BREAKABLE, FAMILY_BLURBS, FAMILY_TITLES, wiki_slug

    from buttcrack.ciphers import all_ciphers

    groups: dict[str, list] = {}
    for cipher in all_ciphers():
        groups.setdefault(cipher.info.family.value, []).append(cipher)

    out = []
    for family in WIKI_FAMILY_ORDER:
        ciphers = groups.get(family)
        if not ciphers:
            continue
        items = []
        for cipher in sorted(ciphers, key=lambda c: c.info.title):
            info = cipher.info
            chip = (
                ' <span class="chip chip-full">full version</span>'
                if info.name not in BROWSER_BREAKABLE else ""
            )
            items.append(
                f'        <li><a href="{wiki_slug(info.name)}">{info.title}</a>{chip}'
                f" — {info.description}</li>"
            )
        out.append(
            f'    <section class="wiki-family" id="family-{family}">\n'
            f'      <h3>{FAMILY_TITLES.get(family, family)}</h3>\n'
            f'      <p>{FAMILY_BLURBS.get(family, "")}</p>\n'
            f'      <ul class="cipher-index">\n' + "\n".join(items) + "\n      </ul>\n"
            "    </section>"
        )
    return "\n".join(out)


def wiki_stats_infobox() -> str:
    """The main page's infobox: what this wiki contains, counted at build time."""
    from wiki_ciphers import FAMILY_TITLES

    from buttcrack.ciphers import all_ciphers

    by_family: dict[str, int] = {}
    for cipher in all_ciphers():
        by_family[cipher.info.family.value] = by_family.get(cipher.info.family.value, 0) + 1
    rows = [
        ("Cipher articles", str(len(list(all_ciphers())))),
        ("Families", ", ".join(
            f'<a href="cipher-wiki.html#family-{f}">{FAMILY_TITLES[f]}</a>'
            for f in WIKI_FAMILY_ORDER if f in by_family
        )),
        ("History features", "Timeline · Codebreakers · Famous ciphers · Unsolved archive"),
        ("Written by", "the solver's registry, at build time"),
        ("License", f'<a href="{CFG["repo_url"]}">Open source</a>'),
    ]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return (
        '<aside class="wiki-infobox" aria-label="About this wiki">\n'
        '      <div class="wiki-infobox-title">Buttcrack Cipher Wiki</div>\n'
        '      <div class="wiki-infobox-sub">The free field guide</div>\n'
        '      <table class="wiki-infobox-table"><tbody>\n'
        f'        {body}\n'
        "      </tbody></table>\n"
        '      <div class="wiki-infobox-note">One article per cipher, generated from the '
        "code that implements it — so a page cannot quietly disagree with the tool above it.</div>\n"
        "    </aside>"
    )


def history_series_infobox(current: str) -> str:
    """A small series box for the three history features."""
    entries = [
        ("history-of-codebreaking.html", "A history of codebreaking", "Timeline"),
        ("famous-cryptanalysts.html", "The codebreakers", "People"),
        ("famous-ciphers.html", "Famous ciphers", "Solved &amp; unsolved"),
    ]
    rows = "".join(
        f'<tr><th>{label}</th><td><a href="{href}">{title}</a>'
        + (" ← you are here" if href == current else "")
        + "</td></tr>"
        for href, title, label in entries
    )
    return (
        '<aside class="wiki-infobox" aria-label="History series">\n'
        '      <div class="wiki-infobox-title">History series</div>\n'
        '      <div class="wiki-infobox-sub">Three features</div>\n'
        '      <table class="wiki-infobox-table"><tbody>\n'
        f"        {rows}\n"
        "      </tbody></table>\n"
        '      <div class="wiki-infobox-note">Every technique in this solver has an '
        "inventor and a date; these are they.</div>\n"
        "    </aside>"
    )


def write_wiki_index_js(wiki_specs: list[dict]) -> None:
    """The search index and rotation data, consumed by wiki.js in the browser.

    Written at build time from the same specs that generate the pages, so the
    search box can never return a page that does not exist.
    """
    pages = []
    for spec in wiki_specs:
        fam = (spec.get("wiki") or {}).get("family_title", "")
        pages.append({
            "t": spec["h1"],
            "s": spec["slug"],
            "f": fam,
            "d": spec.get("desc", "")[:200],
        })
    data = {
        "pages": pages,
        "featured": [
            {"t": t, "s": s, "d": d} for t, s, d in FEATURED_ARTICLES
        ],
        "facts": DYK_FACTS,
    }
    (HERE / "wiki-index.js").write_text(
        "window.WIKI_INDEX = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )


#: hrefs that point outside this generator's directory. The Kryptos explorer is
#: mounted at the site root by scripts/build_site.py after this build runs.
_EXTERNAL_HREFS = {KRYPTOS_HREF, "kryptos/index.html"}
_HREF_RE = re.compile(r'''href="([^"]+)"''')


def check_internal_links(written: dict[str, str]) -> None:
    """Fail the build if any internal link on any page is broken.

    "All fifty cipher wikis are accessible" is a build guarantee here, not a
    hope: every href on every generated page must resolve to a file this build
    wrote or shipped (or a known mount point), and every #fragment must resolve
    to an id on the page it points at. A typo'd slug fails the deploy instead
    of shipping a dead link.
    """
    problems: list[str] = []
    for slug, html in written.items():
        for m in _HREF_RE.finditer(html):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
                continue
            if href in _EXTERNAL_HREFS:
                continue
            target_page, _, fragment = href.partition("#")
            target_page = target_page.strip() or slug
            # Assets and generated files (style.css, model.js, the PDFs) are
            # not pages, but they must exist on disk or the link is dead.
            if target_page in written:
                if fragment and f'id="{fragment}"' not in written[target_page]:
                    problems.append(f"{slug}: anchor #{fragment} not found on {target_page}")
            elif (HERE / target_page).is_file():
                continue
            else:
                problems.append(f"{slug}: links to missing page {href!r}")
    if problems:
        details = "\n  ".join(problems[:30])
        raise SystemExit(
            f"broken internal links ({len(problems)}):\n  {details}"
            + ("\n  …" if len(problems) > 30 else "")
        )


def solver_html() -> str:
    """The solver shell, shared by every page regardless of layout."""
    sample_buttons = "".join(
        f'<button data-sample="{key}">{label}</button>'
        for key, label in [
            ("caesar", "Caesar"), ("vigenere", "Vigenère"),
            ("beaufort", "Beaufort"), ("porta", "Porta"), ("autokey", "Autokey"),
            ("substitution", "Substitution"), ("layered", "Layered"), ("morse", "Morse"),
        ]
    )
    return f"""<section class="solver-shell" aria-label="Cipher solver">
    <div class="solver-heading">
      <div><p class="eyebrow">Private by design</p><h2>Drop in a puzzle. Leave with an answer.</h2></div>
      <span class="local-badge"><i aria-hidden="true"></i> Runs on this device</span>
    </div>
    <label class="sr-only" for="ciphertext">Ciphertext to solve</label>
    <textarea id="ciphertext" spellcheck="false"
      placeholder="Paste ciphertext here — you don't need to know which cipher it is."></textarea>
    <div class="controls">
      <button class="go" id="go">Solve cipher <span aria-hidden="true">→</span></button>
      <button class="ghost" id="clear">Clear</button>
      <span class="samples"><span class="sample-label">Try a sample</span>{sample_buttons}</span>
    </div>
    <details class="solver-limits">
      <summary>What this browser solver can—and cannot—do</summary>
      <p><strong>It tries:</strong> Caesar, Atbash, ROT13, affine, Trithemius, rail fence, single-byte XOR, periodic Vigenère-family ciphers, autokey, selected encoding layers (such as Base64, hex, binary, decimal ASCII, Morse, and reverse), and—only with 60+ A–Z letters—statistical substitution.</p>
      <p><strong>It does not:</strong> prove a decryption, cover every classical cipher, or break modern encryption such as AES or RSA. Its ranking model is tuned for English, so a high score is a lead to verify with the method, key, and source context—not a guarantee.</p>
      <p>Short text, non-English plaintext, non-Latin or symbol alphabets, missing keys, and unsupported formats can all leave no high-confidence answer. When that happens, the result includes input-specific observations and suggested next checks; those observations are not a claim to know the exact cause.</p>
    </details>
    <p class="privacy">No account. No upload. No stored text. The complete solver runs in your browser.</p>
  </section>"""


def page(slug: str, title: str, desc: str, h1: str, tagline: str,
         preset: str, body: str, faqs: list[tuple[str, str]],
         wiki: dict | None = None) -> str:
    faq_html = "".join(
        f"<details class=\"faq\"><summary>{q}</summary><p>{a}</p></details>" for q, a in faqs
    )
    if wiki:
        # Wiki pages wear the encyclopedia layout: a compact site bar (the
        # solver's big hero would push the article below the fold), then the
        # Wikipedia-style two-column chrome with the article first. The solver
        # follows the article rather than preceding it — the reader came for
        # the article, and the solver is one scroll away with the same sample
        # preloaded.
        header = f"""<header class="site-header site-header-compact">
  <div class="wrap wrap-wide">
    <a class="brand" href="index.html" aria-label="Buttcrack cipher solver home">
      <span class="brand-mark" aria-hidden="true">B</span>
      <span>buttcrack<span class="brand-dot">.</span></span>
    </a>
    <a class="wiki-wordmark" href="cipher-wiki.html">Cipher&nbsp;Wiki</a>
    {nav(slug)}
  </div>
</header>"""
        main = wiki_main(slug, h1, tagline, body, faq_html, wiki)
        extra_scripts = '<script src="wiki-index.js"></script>\n<script src="wiki.js"></script>'
    else:
        header = f"""<header class="site-header">
  <div class="wrap">
    <a class="brand" href="index.html" aria-label="Buttcrack cipher solver home">
      <span class="brand-mark" aria-hidden="true">B</span>
      <span>buttcrack<span class="brand-dot">.</span></span>
    </a>
    <div class="hero-copy">
      <p class="eyebrow">Automatic classical cryptanalysis</p>
      <h1>{h1}<span class="dot">.</span></h1>
      <p class="tagline">{tagline}</p>
    </div>
    {nav(slug)}
  </div>
</header>"""
        main = f"""<main class="wrap" id="main-content">
  {solver_html()}

  <div id="output" aria-live="polite"></div>

  {ad_slot()}

  <article>
{body}
    <h2>Frequently asked questions</h2>
    {faq_html}
  </article>

  {support_block()}
</main>"""
        extra_scripts = ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{CFG['base_url']}/{slug}">{verification_meta()}
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{'article' if wiki else 'website'}">
<meta property="og:url" content="{CFG['base_url']}/{slug}">
<link rel="stylesheet" href="style.css">
{article_jsonld(h1, desc, (wiki or {}).get('family_title', '')) if wiki else app_jsonld(title, desc)}
{faq_jsonld(faqs) if faqs else ''}{buy_button_script(body)}{adsense_head()}{analytics()}
</head>
<body data-preset="{preset}">
<a class="skip-link" href="#main-content">Skip to content</a>
{header}

{main}

<footer>
  <div class="wrap">
    <p>Powered by <a href="{CFG['repo_url']}">buttcrack</a>, an open-source automatic cipher breaker.
    This browser build uses a compact trigram model; the <a href="windows-app.html">desktop
    version</a> searches 50 ciphers — including the M-94 wheel cipher — with quadgram models in
    six languages, and runs its own local interface entirely offline.</p>
    <p>For puzzles, CTFs and curiosity. Don't use it on anything you have no right to read.</p>
  </div>
</footer>

<script src="model.js"></script>
<script src="app.js"></script>
{extra_scripts}
</body>
</html>
"""

def delivery_url(raw: str, field: str) -> str:
    """Validate the post-purchase installer URL. Returns "" when unset.

    Same discipline as ``payment_url``: this link is what somebody has just
    paid $39.99 to reach, and a URL that 404s or downgrades to http looks
    exactly like a working one until a customer clicks it.
    """
    url = (raw or "").strip()
    if not url:
        return ""
    if url.startswith("http://"):
        raise SystemExit(
            f"site.json: windows_app.{field} must be https, not http: {url}\n"
            f"Browsers block executable downloads served over plain http."
        )
    if not url.startswith("https://"):
        raise SystemExit(f"site.json: windows_app.{field} is not a URL: {url!r}")
    # The whole paywall is that this URL is not guessable and not linked from
    # anywhere public. Hosting it on the site itself gives it away.
    if CFG["base_url"].rstrip("/") in url:
        raise SystemExit(
            f"site.json: windows_app.{field} points back at this site ({url}).\n"
            f"The installer is the paid product and this site is public — serving it from\n"
            f"here means anyone can download it without paying. Put it on storage you\n"
            f"control (Cloudflare R2, Backblaze B2, S3) and paste that URL instead."
        )
    if not url.lower().endswith(".exe"):
        print(f"  note: windows_app.{field} does not end in .exe ({url}) — assuming a redirect")
    return url


def windows_app_config() -> dict:
    """The Windows product, with its two URLs validated."""
    cfg = dict(CFG.get("windows_app", {}) or {})
    cfg["payment_link"] = payment_url(cfg.get("payment_link", ""), "windows_app.payment_link")
    cfg["delivery_url"] = delivery_url(cfg.get("delivery_url", ""), "delivery_url")
    cfg["token"] = hashlib.sha256(
        f"{cfg.get('sku', 'winapp')}:{CFG.get('stripe', {}).get('delivery_salt', '')}".encode()
    ).hexdigest()[:20]
    cfg["delivery_page"] = f"thank-you-{cfg['token']}.html"
    return cfg


def write_windows_delivery(cfg: dict) -> None:
    """The page Stripe redirects to after payment. Not linked, not indexed.

    Written after ``build_products``, which clears every ``thank-you-*.html``
    so a changed salt cannot leave a stale delivery page behind.
    """
    link = cfg["delivery_url"]
    spec = " · ".join(filter(None, [
        f"version {cfg.get('version', '')}" if cfg.get("version") else "",
        "Windows 10/11, 64-bit",
        cfg.get("size", ""),
    ]))
    if link:
        action = f"""<p><a class="btn primary" style="display:inline-block;padding:11px 24px;border-radius:8px;
       background:var(--accent);color:#05230f;font-weight:700;text-decoration:none"
       href="{link}">Download the installer</a></p>
    <p style="font-size:14px;color:var(--muted);margin-bottom:0">
      Bookmark this page — the link stays valid. Lost it? Email the address on your
      Stripe receipt and it will be sent again.</p>"""
    else:
        # A buyer must never see a broken button. Until the installer is
        # uploaded, promise a human instead of linking to nothing.
        action = """<p style="margin-bottom:0">Your payment went through and your copy is reserved.
      The download link is being sent to the email address on your Stripe receipt — if it has
      not arrived within a few hours, reply to that receipt and it will be sent straight away.</p>"""

    sha = ""
    if cfg.get("sha256"):
        sha = f"""
    <p style="font-size:13px;color:var(--muted);margin:14px 0 0">SHA-256, to check the file arrived
      intact:<br><code style="font-size:12px;word-break:break-all">{html_escape(cfg['sha256'])}</code></p>"""

    (HERE / cfg["delivery_page"]).write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Your download — {html_escape(cfg.get('title', 'Buttcrack for Windows'))}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header><div class="wrap">
  <h1>Thank you<span class="dot">.</span></h1>
  <p class="tagline">Your copy of Buttcrack for Windows is ready.</p>
</div></header>
<main class="wrap">
  <div class="card">
    <h2 style="margin-top:0">{html_escape(cfg.get('title', 'Buttcrack for Windows'))}</h2>
    <p style="color:var(--muted)">{html_escape(spec)}</p>
    {action}{sha}
  </div>
  <div class="card">
    <h3 style="margin-top:0">Windows will warn you the first time</h3>
    <p style="margin-bottom:0">The installer is not code-signed, so SmartScreen shows a blue
      <em>“Windows protected your PC”</em> box. Click <strong>More info</strong>, then
      <strong>Run anyway</strong>. It installs without administrator rights and uninstalls from
      Add/Remove Programs.</p>
  </div>
  <div class="card">
    <p style="margin:0">Installed? Open <strong>Buttcrack</strong> from the Start menu — it opens
      the solver in your browser and runs entirely on your machine.</p>
  </div>
</main>
<footer><div class="wrap"><p><a href="index.html">Back to the solver</a></p></div></footer>
</body>
</html>
""")


def windows_app_html() -> str:
    """The storefront for the desktop build.

    One product, one Stripe button. The installer itself is never served from
    this site — ``delivery_url`` points at storage the author controls, and the
    link is only ever shown on the post-payment page.
    """
    cfg = windows_app_config()
    link = cfg["payment_link"]
    price = html_escape(cfg.get("price") or "")
    version = html_escape((cfg.get("version") or "").strip())
    digest = (cfg.get("sha256") or "").strip().lower()

    spec_bits = " · ".join(filter(None, [
        f"version {version}" if version else "",
        "Windows 10 / 11, 64-bit",
        html_escape((cfg.get("size") or "").strip()),
        "no admin rights needed",
    ]))
    if link:
        button = f'<a class="buy" href="{link}">Buy for {price or "the listed price"}</a>'
    else:
        button = ('<span class="soon">Payment link not configured yet — '
                  'see ventures/README.md</span>')

    checksum = f"""
    <h2>Verify what you downloaded</h2>
    <p>The installer's SHA-256 is published before you buy, so you can confirm the file you
    receive is byte-for-byte the one described here. In PowerShell:</p>
    <pre class="spec">Get-FileHash .\\buttcrack-setup-{version or 'VERSION'}.exe -Algorithm SHA256</pre>
    <p class="spec">{html_escape(digest)}</p>""" if digest else ""

    return f"""    <h2>The desktop application</h2>
    <p>The solver on this page runs in your browser on a compact trigram model, and it is free
    for as long as this site exists. The desktop build is the full engine:
    <strong>50 ciphers</strong> including the M-94 wheel cipher, Quagmire III and the
    polyalphabetic sum-clock, quadgram models in <strong>six languages</strong>, layered-puzzle
    unwrapping six levels deep, and a search budget you set yourself.</p>

    <div class="products">
  <div class="product">
      <h3>{html_escape(cfg.get('title', 'Buttcrack for Windows'))}</h3>
      <p class="blurb">The complete cipher breaker as a Windows program. One installer, nothing
      else to fetch — the language models and the interface are inside it. Install it on a
      machine that has never seen Python and it works.</p>
      <p class="spec">{spec_bits}</p>
      {button}
    </div>
    </div>
    <p class="spec" style="margin-top:22px">Payment is handled by Stripe. The download appears
    immediately after checkout — no account, no licence key, no subscription. One payment, yours
    to keep, on as many of your own machines as you like.</p>

    <h2>What you get</h2>
    <p>Two programs sharing one runtime:</p>
    <ul>
      <li><strong>Buttcrack</strong> — the Start-menu app. It starts a private server on
      <code>127.0.0.1</code>, opens the solver in your browser, and sits in the notification
      area until you close it.</li>
      <li><strong>buttcrack.exe</strong> — the command line, optionally added to your
      <code>PATH</code> during setup, so <code>buttcrack "Wkh txlfn eurzq ira"</code> works in
      any terminal, reads files and pipes, and prints JSON for scripting.</li>
    </ul>
    <p>It installs per-user into <code>%LOCALAPPDATA%</code>, so there is <strong>no
    administrator prompt</strong>, and it uninstalls from Add/Remove Programs like anything
    else. No account, no licence server, no telemetry, no update checks, no expiry.</p>

    <h2>Nothing leaves your machine</h2>
    <p>The desktop build is a local web server, not a web service. The address it opens is bound
    to loopback only — unreachable from your own network, let alone the internet — and the
    language models are inside the installer, so every feature works with the network cable
    out. That is the entire reason it exists: a document you are not allowed to paste into a
    website can still be worked on using hardware you control.</p>

    <h2>What it breaks that the browser version does not</h2>
    <ul>
      <li><strong>All 50 ciphers</strong>, each with its own attack rather than a brute-force
      loop — including Playfair, bifid, trifid, four-square, Hill, the M-94 wheel cipher,
      Quagmire III, Myszkowski and AMSCO.</li>
      <li><strong>Six languages.</strong> English with an 80,000-word dictionary distilled from
      a 25-million-word corpus, plus French, German, Italian, Latin and Spanish n-gram models —
      and <code>--language auto</code> to probe all six.</li>
      <li><strong>Deeper layers.</strong> Encodings and ciphers stacked six deep, unwrapped and
      reported as a chain, with the key of the cipher that actually hid the message.</li>
      <li><strong>Your own time budget.</strong> Hard puzzles get minutes instead of the
      seconds a web page can spare, and the search reports what it tried and what it scored.</li>
    </ul>
{checksum}

    <h2>Windows will warn you the first time</h2>
    <p>The installer is not code-signed, so Windows SmartScreen shows a blue
    <em>“Windows protected your PC”</em> dialog. That is a statement about a certificate that
    costs several hundred dollars a year, not about the file. Click <strong>More info</strong>,
    then <strong>Run anyway</strong> — and check the SHA-256 above first if you would rather not
    take anyone's word for it.</p>

    <h2>Requirements</h2>
    <p>Windows 10 or 11, 64-bit. Roughly 60 MB of disk once installed. No internet connection is
    required at any point after the download, and none is used. There is no macOS or Linux
    installer.</p>"""


PAGES = [
    {
        "slug": "index.html",
        "title": "Free Cipher Solver — Break Any Classical Cipher Automatically",
        "desc": "Paste ciphertext and this free solver names the cipher, recovers the key and prints the plaintext — Caesar, Vigenère, substitution, XOR, base64, Morse. No upload.",
        "h1": "Cipher Solver",
        "tagline": "Paste ciphertext. It works out the cipher, finds the key, and shows the plaintext.",
        "preset": "caesar",
        "faqs": [
            ("Do I need to know which cipher was used?",
             "No. The solver characterises the text first — index of coincidence, entropy, character set — then tries every cipher it knows and ranks the candidate plaintexts with an English trigram language model. You just paste and press the button."),
            ("Is my ciphertext uploaded anywhere?",
             "No. There is no server. The entire solver, including the language model, is JavaScript that your browser downloads once and runs locally. You can disconnect from the internet after the page loads and it still works."),
            ("Which ciphers can it break?",
             "Caesar and ROT13, Atbash, affine, the periodic family — Vigenère, Beaufort, Variant Beaufort, Porta, Gronsfeld, Trithemius and autokey, all with automatic key recovery — plus monoalphabetic substitution, rail fence transposition, single-byte XOR, and the encoding layers base64, hex, binary, decimal bytes, Morse and reversed text, including several of those stacked on top of each other."),
            ("Why did it fail on my text?",
             "The most common reasons are that the text is too short (under about 40 letters there is not enough statistical signal), the plaintext is not English — this browser build scores English only — or the cipher is outside the set above. Longer ciphertext is dramatically easier to break than short ciphertext, and the full desktop version adds French, German, Italian, Latin and Spanish models for non-English plaintext."),
            ("Can it break modern encryption like AES or RSA?",
             "No, and neither can anything else you will find on the web. This tool targets classical and puzzle ciphers. Properly implemented modern encryption is not breakable by frequency analysis or key search."),
        ],
        "body": """    <h2>What this does</h2>
    <p>Most cipher tools ask you to pick the cipher and supply the key. That is fine when you
    already know both, and useless when you are staring at a block of gibberish from a puzzle
    box, a geocache, an escape room or a CTF challenge. This one starts from nothing: it
    measures the text, forms hypotheses about what produced it, searches the keyspaces, and
    scores every candidate plaintext against a statistical model of English.</p>

    <h2>How it decides</h2>
    <p>Three signals do most of the work.</p>
    <h3>Index of coincidence</h3>
    <p>The probability that two letters drawn at random from the text are the same. English
    sits near <code>0.067</code>; random text sits near <code>0.038</code>. A monoalphabetic
    cipher such as Caesar or a substitution keeps the value near English because it only
    relabels letters. A polyalphabetic cipher such as Vigenère flattens it. That single number
    splits the search space roughly in half before any key is tried.</p>
    <h3>Trigram scoring</h3>
    <p>Every candidate plaintext is scored by the average log-probability of its three-letter
    sequences under an English corpus model. <code>THE</code>, <code>AND</code> and
    <code>ING</code> are common; <code>QKX</code> is not. This is what lets the tool pick the
    correct Caesar shift out of 26 without a human reading them, and what guides the
    hill-climbing search for substitution keys.</p>
    <h3>Word hits</h3>
    <p>Trigram scores alone can be fooled — a hill-climber will happily produce text that
    <em>looks</em> English-shaped without being English. So the final ranking also counts how
    many real words appear, weighted by length, which breaks ties between near-identical
    candidates and catches single wrong letters in a recovered key.</p>

    <h2>Layered puzzles</h2>
    <p>Puzzle setters stack things: base64 around hex around a Caesar shift. After trying the
    direct ciphers, the solver tests whether the text is a valid encoding, unwraps one layer,
    and runs the whole process again on the result, up to three layers deep. The decode chain
    is shown with the answer so you can see exactly what was done.</p>

    <h2>A worked example</h2>
    <p>Press the <strong>Layered</strong> sample above. The input looks like base64. Decoding
    it gives hex; decoding that gives letters that still are not English; the index of
    coincidence says monoalphabetic; a 26-shift sweep finds the answer. The tool reports the
    chain <code>base64 → base16 → caesar</code> along with the key it recovered.</p>""",
    },
    {
        "slug": "caesar-cipher-decoder.html",
        "title": "Caesar Cipher Decoder — Decrypt Without Knowing the Shift",
        "desc": "Free Caesar cipher decoder that finds the shift for you. Paste ciphertext and get the plaintext plus the key. Also handles ROT13 and Atbash. Runs in your browser.",
        "h1": "Caesar Cipher Decoder",
        "tagline": "Don't know the shift? It tries all 26 and picks the English one.",
        "preset": "caesar",
        "faqs": [
            ("How do I decode a Caesar cipher without the key?",
             "There are only 26 possible shifts, so you try them all and pick the one that produces English. This page automates both halves: it generates all 26 candidates and scores each with a trigram language model, so the correct shift is chosen without you reading through the list."),
            ("Is ROT13 the same thing?",
             "ROT13 is a Caesar cipher with a shift of exactly 13. Because 13 is half of 26, applying it twice returns the original text, which is why it is used for hiding spoilers rather than for security."),
            ("What is the difference between Caesar and Atbash?",
             "Caesar rotates the alphabet by a fixed amount. Atbash reflects it, mapping A to Z, B to Y and so on. Atbash has no key at all, so there is only one possible decryption. This tool tests both."),
            ("The shift looks right but some words are wrong. Why?",
             "A Caesar cipher applies one shift to the whole message, so if part of it decodes and part does not, you are probably looking at a Vigenère cipher, which uses a repeating sequence of shifts. Try the Vigenère page."),
        ],
        "body": """    <h2>How the Caesar cipher works</h2>
    <p>Each letter is moved a fixed number of places along the alphabet. With a shift of 3,
    <code>A</code> becomes <code>D</code>, <code>B</code> becomes <code>E</code>, and
    <code>Z</code> wraps around to <code>C</code>. Decryption shifts back by the same amount.
    Non-letters are left untouched, which is why punctuation and word lengths survive — and
    why the cipher is so easy to break.</p>

    <h2>Why it falls instantly</h2>
    <p>The key is a single number between 0 and 25. That is the entire keyspace: 26
    possibilities, 25 of which are wrong. A computer checks all of them in under a
    millisecond. The only real work is deciding which output is English, and a trigram model
    does that reliably on anything longer than a short phrase.</p>

    <h3>Breaking it by hand</h3>
    <p>If you want to do it yourself, count letters. <code>E</code> is the most common letter
    in English by a wide margin, so whichever letter dominates your ciphertext is probably
    <code>E</code>; the distance between them is your shift. Failing that, look for one-letter
    words, which are almost always <code>A</code> or <code>I</code>, and three-letter words,
    which are overwhelmingly <code>THE</code>.</p>

    <h2>Where you'll meet it</h2>
    <p>Caesar shifts turn up in escape rooms, geocache puzzles, beginner CTF challenges,
    treasure hunts and children's puzzle books. They are also frequently the innermost layer
    of a harder puzzle, wrapped in base64 or hex to disguise the fact that the underlying
    cipher is trivial — which is why this page still runs the full layered search rather than
    only trying shifts.</p>""",
    },
    {
        "slug": "vigenere-cipher-solver.html",
        "title": "Vigenère Cipher Solver — Recovers the Key Automatically",
        "desc": "Break a Vigenère cipher without the keyword. This free solver finds the key length by index of coincidence and recovers the key letter by letter, in your browser.",
        "h1": "Vigenère Solver",
        "tagline": "No keyword needed — it recovers the key from the ciphertext itself.",
        "preset": "vigenere",
        "faqs": [
            ("Can a Vigenère cipher be broken without the key?",
             "Yes. Because the key repeats, the ciphertext contains several interleaved Caesar ciphers. Find the key length and each of those can be solved independently by frequency analysis. This has been standard practice since Kasiski published the method in 1863."),
            ("How much ciphertext do I need?",
             "As a rough rule you want at least 20 letters per key character, so a six-letter key wants 120 letters or more. Shorter texts leave each position with too few samples for the statistics to be reliable, though the trigram refinement pass on this page recovers many borderline cases."),
            ("What if the key is as long as the message?",
             "Then it is a one-time pad and it is genuinely unbreakable, provided the key is random and never reused. No tool can help. In practice puzzle keys are short repeating words."),
            ("Why did it return a key that is a repeated word, like LAMPLAMP?",
             "Any multiple of the true key length fits the ciphertext just as well. The solver penalises longer keys to prefer the shortest explanation, but on short texts a doubled key occasionally wins. The plaintext is still correct."),
        ],
        "body": """    <h2>Why Vigenère resisted for 300 years</h2>
    <p>A Caesar cipher uses one shift for the whole message, so letter frequencies survive
    intact and betray it immediately. Vigenère uses a keyword: each letter of the keyword
    gives a shift, and the keyword repeats across the message. <code>E</code> no longer maps to
    a single letter, the frequency distribution flattens, and the technique that destroys
    Caesar simply stops working. It was called <em>le chiffre indéchiffrable</em> for a
    reason.</p>

    <h2>The crack: find the period first</h2>
    <p>The weakness is the repetition. If the key is four letters long, then every fourth
    letter of the ciphertext was encrypted with the same shift. Take positions 1, 5, 9, 13 and
    you have a pure Caesar cipher. The whole problem reduces to one question: how long is the
    key?</p>

    <h3>Index of coincidence</h3>
    <p>For each candidate length, the solver splits the ciphertext into that many cosets and
    measures the index of coincidence of each. When the guessed length matches the real one,
    every coset is monoalphabetic and its IC jumps toward the English value of
    <code>0.067</code>. When the guess is wrong, the cosets stay mixed and the IC stays near
    random. The correct period announces itself.</p>

    <h3>Then solve each position</h3>
    <p>With the length known, each coset is attacked by chi-squared comparison against English
    letter frequencies, which gives a first guess at every key letter. That first guess is
    often one or two letters wrong on short texts, because a coset of twelve letters is a thin
    sample. So the solver runs a refinement pass: it re-picks each key letter by scoring the
    <em>whole</em> decryption with the trigram model, then a final pass that also counts real
    English words. That is what turns a nearly-right key into an exactly-right one.</p>

    <h2>Related ciphers</h2>
    <p>The same machinery handles the Beaufort and variant Beaufort ciphers, which differ only
    in the direction of the shift, and repeating-key XOR, which is Vigenère over bytes instead
    of letters and is extremely common in CTF challenges.</p>""",
    },
    {
        "slug": "substitution-cipher-solver.html",
        "title": "Substitution Cipher Solver — Automatic Cryptogram Breaker",
        "desc": "Solve substitution ciphers and cryptograms automatically. Hill-climbing search with an English trigram model recovers the key without hints. Free, no upload.",
        "h1": "Substitution Solver",
        "tagline": "Cryptograms cracked by hill-climbing search — no crib, no hints.",
        "preset": "substitution",
        "faqs": [
            ("How long does the ciphertext need to be?",
             "About 60 letters is the practical minimum and 150 or more is comfortable. Unlike Caesar, there are 26 factorial possible keys, so the search relies on letter statistics and short texts simply do not contain enough of them."),
            ("Does it handle keyword-generated alphabets?",
             "Yes, implicitly. The solver searches for the mapping itself and does not care how the key alphabet was produced, so keyword ciphers, random alphabets and keyed Caesar variants are all the same problem to it."),
            ("Why is one or two letters wrong in the output?",
             "Rare letters like J, Q, X and Z appear too infrequently for the statistics to place them confidently, so they sometimes swap. The text is usually readable anyway and the correct letter is obvious from context."),
            ("Will it solve a newspaper cryptogram?",
             "Usually yes, if you paste the whole puzzle. Cryptograms preserve word boundaries, which makes them easier than the continuous-block ciphertext this solver is designed for."),
        ],
        "body": """    <h2>A keyspace you cannot search</h2>
    <p>A monoalphabetic substitution replaces each letter with another, consistently, using a
    scrambled alphabet as the key. There are 26 factorial such alphabets — roughly
    403 septillion. Trying them all is not an option now and will not be an option ever.
    And yet these ciphers fall in seconds, because the keyspace does not need to be
    searched exhaustively; it needs to be climbed.</p>

    <h2>Hill climbing</h2>
    <p>The solver starts with a guess built from letter frequencies: the most common
    ciphertext letter is provisionally <code>E</code>, the next <code>T</code>, and so on down
    the <code>ETAOIN SHRDLU</code> ordering. That guess is usually wrong in detail but roughly
    right in shape.</p>
    <p>Then it improves. Swap two letters in the key, rescore the decryption with the trigram
    model, and keep the swap if the score went up. Repeat over every pair until no swap helps.
    That yields a local optimum — often the answer, sometimes a near-miss where a couple of
    letters are transposed.</p>

    <h3>Escaping local optima</h3>
    <p>To avoid getting stuck, the search restarts repeatedly from perturbed copies of the
    best key found so far, keeping whichever run scores highest. A final polish pass changes
    the objective, scoring partly on how many genuine English words appear, which is what
    separates confusable letters such as <code>B</code>, <code>V</code> and <code>M</code> that
    sit in similar trigram contexts.</p>

    <h2>Doing it by hand</h2>
    <p>If you would rather solve it yourself: single-letter words are <code>A</code> or
    <code>I</code>. The most common three-letter word is <code>THE</code>, which also hands you
    the two most common letters. Doubled letters are usually <code>LL</code>, <code>EE</code>,
    <code>SS</code>, <code>OO</code> or <code>TT</code>. An apostrophe followed by one letter is
    nearly always <code>S</code> or <code>T</code>. From four or five confirmed letters the rest
    usually collapses quickly.</p>""",
    },
    {
        "slug": "morse-code-translator.html",
        "title": "Morse Code Translator & Decoder — Dots and Dashes to Text",
        "desc": "Translate Morse code to plain text instantly. Handles slashes, pipes or double spaces as word separators, and keeps decoding if there is another cipher underneath.",
        "h1": "Morse Decoder",
        "tagline": "Dots and dashes in, readable text out — and it keeps going if there's a cipher underneath.",
        "preset": "morse",
        "faqs": [
            ("What separators does it accept?",
             "Single spaces between letters, and a slash, a pipe or a double space between words. Mixed conventions in the same message are handled, which matters because puzzle sources are rarely consistent."),
            ("Can it decode Morse audio or flashing lights?",
             "No, this is a text tool. You need to transcribe the signal into dots and dashes first, then paste it here."),
            ("What if the decoded Morse is still gibberish?",
             "Then Morse was only the outer layer. This page automatically re-runs the full cipher search on whatever the Morse decodes to, so a Caesar shift or Vigenère cipher hidden underneath is peeled off in the same pass."),
            ("Does it support numbers and punctuation?",
             "Digits zero through nine are supported. Punctuation codes are rarer in puzzles and are skipped rather than guessed."),
        ],
        "body": """    <h2>Reading Morse</h2>
    <p>Morse encodes each letter as a sequence of short and long signals — dots and dashes.
    <code>E</code>, the most common English letter, is a single dot; <code>T</code> is a single
    dash. Rarer letters get longer sequences. That design makes it efficient to send by hand
    and, incidentally, easy to decode by lookup table.</p>

    <h3>The separator problem</h3>
    <p>Morse has no inherent way to mark where one letter ends and the next begins — that is
    carried by timing in the original signal. Written down, people improvise: one space between
    letters, three spaces or a slash between words. Puzzle authors mix conventions freely. This
    decoder accepts slashes, pipes and runs of whitespace as word breaks, which covers nearly
    everything you will encounter.</p>

    <h2>Morse as a puzzle layer</h2>
    <p>In puzzle hunts and CTFs, Morse is almost never the whole challenge. It is a wrapper —
    the dots and dashes decode to letters that are themselves encrypted. Because this page runs
    the complete cipher search on the decoded output, a Caesar shift, Vigenère cipher or further
    encoding underneath comes out in the same run, with the full decode chain shown alongside
    the answer.</p>

    <h2>Common source formats</h2>
    <p>Morse turns up transcribed from audio files, from blinking lights in a video, from long
    and short marks in an image, and from text where dots and dashes have been substituted with
    other characters entirely. If yours uses different symbols, replace them with
    <code>.</code> and <code>-</code> before pasting.</p>""",
    },
    {
        "slug": "ctf-crypto-solver.html",
        "title": "CTF Crypto Solver — Base64, Hex, XOR and Layered Encodings",
        "desc": "Automatic solver for CTF crypto challenges: base64, hex, binary, single-byte and repeating-key XOR, and stacked encoding layers. Identifies and peels each layer.",
        "h1": "CTF Crypto Solver",
        "tagline": "Base64 around hex around XOR? It unwraps the whole stack.",
        "preset": "layered",
        "faqs": [
            ("What is single-byte XOR and why is it everywhere in CTFs?",
             "Every byte of the plaintext is XORed with the same one-byte key. There are only 255 keys to try, so it is trivially breakable, which makes it the standard warm-up challenge in introductory CTF crypto categories."),
            ("How deep can the layers go?",
             "The browser version peels up to three encoding layers. The full version goes six layers deep, searches 50 ciphers and scores in six languages, which is what you want for harder challenges."),
            ("Can it handle flag formats?",
             "Yes, incidentally — flags like ctf{...} are usually surrounded by enough English or structured text for the scoring to lock on. Very short flag-only inputs are harder because there is little statistical signal."),
            ("Why does it sometimes pick the wrong layer to unwrap?",
             "Hex and base64 character sets overlap, so a string can be validly interpretable as either. The solver tries both branches and keeps whichever produces the more English-like result rather than committing to the first guess."),
        ],
        "body": """    <h2>The shape of a crypto challenge</h2>
    <p>Introductory CTF crypto is mostly recognition. The underlying operations are simple —
    base64, hex, XOR, a classical cipher — and the difficulty comes from not knowing which ones
    were applied, in what order, and how many times. Experienced players recognise the shapes
    instantly. This tool does the recognising for you and then does the work as well.</p>

    <h2>Identifying encodings by shape</h2>
    <h3>Base64</h3>
    <p>Alphanumerics plus <code>+</code> and <code>/</code>, length a multiple of four, often
    ending in one or two <code>=</code> padding characters. Mixed case with occasional digits is
    the tell.</p>
    <h3>Hex</h3>
    <p>Only <code>0-9</code> and <code>a-f</code>, always an even number of characters. If you
    see a long string that happens to contain no letters past <code>f</code>, it is hex and not a
    cipher.</p>
    <h3>Binary and decimal</h3>
    <p>Runs of <code>0</code> and <code>1</code> in groups of eight, or space-separated numbers
    in the 32 to 126 range — the printable ASCII window. Both are common obfuscation for text
    that is otherwise in the clear.</p>

    <h2>XOR</h2>
    <p>XOR is its own inverse, which is what makes it convenient and what makes it breakable.
    With a single-byte key there are 255 candidates; the solver tries every one, discards those
    producing non-printable bytes, and scores the rest against English. With a repeating
    multi-byte key the structure is identical to Vigenère: find the key length by looking at
    the index of coincidence of each byte position, then solve each position independently.</p>

    <h2>Working the layers</h2>
    <p>The solver treats decoding as a search tree rather than a fixed pipeline. At each node it
    tries every direct cipher, and separately tests whether the text is a valid encoding it can
    unwrap. Unwrapping produces a child node and the process repeats. The answer returned is the
    leaf with the highest confidence, reported with the complete chain that produced it — so you
    learn the structure of the challenge, not just the flag.</p>""",
    },
    {
        "slug": "windows-app.html",
        "title": "Buttcrack for Windows — Offline Cipher Solver and Installer",
        "desc": "Download the Buttcrack cipher solver as a Windows desktop app: 50 ciphers, six language models, runs entirely offline. No Python, no account, no admin rights needed.",
        "h1": "Windows App",
        "tagline": "The full solver as a desktop program. Installs in seconds, runs offline, uploads nothing.",
        "preset": "layered",
        # Rendered in main()'s loop, not here: the storefront needs helpers
        # defined further down the file, and composing it at render time keeps
        # a second call to main() from stacking a second copy.
        "body": "__WINDOWS_APP__",
        "faqs": [
            ("How do I get the file after paying?",
             "Stripe sends you straight to a download page the moment the payment clears, and your receipt arrives by email. The download page stays valid, so bookmark it. If you lose it, reply to the Stripe receipt and it will be sent again."),
            ("Do I need Python installed?",
             "No. The installer contains its own copy of Python, the six language models and the interface. Nothing else has to be present on the machine and nothing is downloaded during installation."),
            ("Does it need administrator rights?",
             "No. By default it installs into your own user profile, so there is no UAC prompt at all. The first page of the installer offers a machine-wide install if you would rather have one, and that does need an administrator."),
            ("Why does Windows say the publisher is unknown?",
             "Because the installer is not code-signed. SmartScreen is reporting the absence of a certificate rather than anything it found in the file. Click More info, then Run anyway — and check the published SHA-256 if you want independent confirmation of what you downloaded."),
            ("Does it send my ciphertext anywhere?",
             "No. The desktop build runs a web server bound to 127.0.0.1, which is your own machine and is not reachable from your network or the internet. There is no analytics, no update check and no account. Disconnect from the network entirely and every feature still works."),
            ("How is this different from the free solver on this page?",
             "The browser solver uses a compact trigram model and covers the common ciphers. The desktop build has all 50 ciphers including Playfair, Hill, the M-94 wheel cipher and Quagmire III, quadgram models for English, French, German, Italian, Latin and Spanish, layered unwrapping six levels deep, and a search budget you can raise for hard problems."),
            ("Can I install it on more than one machine?",
             "Yes. One payment covers your own machines — desktop, laptop, a virtual machine. There is no licence key and nothing to activate, so there is nothing to juggle."),
            ("How do I uninstall it?",
             "Settings, then Apps, then Buttcrack, then Uninstall — or the Uninstall shortcut in its Start menu folder. It removes the program, the shortcuts and the PATH entry if you added one. It leaves nothing behind, because it never writes anything outside its own folder."),
        ],
    },
]

# Curated unresolved problems. "Unsolved" means no generally accepted,
# reproducible decipherment—not that every object below is definitely a cipher.
# Sources are chosen for institutional, scholarly, or specialist provenance.
UNSOLVED_ARCHIVE = [
    {
        "title": "D’Agapeyeff Cipher",
        "when": "1939",
        "kind": "Challenge ciphertext",
        "summary": "Alexander D’Agapeyeff published this 395-digit exercise in the first edition of <em>Codes and Ciphers</em>. No plaintext or method has been verified; a construction or transcription error remains possible.",
        "boundary": "An English-looking fragment is not a solution without an exact, reproducible construction for the published digits.",
        "source_label": "MysteryTwister’s challenge transcript",
        "source_url": "https://mysterytwister.org/media/challenges/pdf/mtc3-schmeh-02-agapeyeff-en.pdf",
    },
    {
        "title": "Zodiac Z13",
        "when": "1970",
        "kind": "13-symbol cryptogram",
        "summary": "This short cipher follows the phrase “My name is—” in a Zodiac letter. Its length leaves too little information to distinguish a proposed name from other fitting candidates, and no definitive solution is accepted.",
        "boundary": "Treat proposed names as hypotheses, not identifications, unless a method supplies unique and independently checkable validation.",
        "source_label": "History’s overview of the Zodiac ciphers",
        "source_url": "https://www.history.com/articles/the-zodiac-ciphers-what-we-know",
    },
    {
        "title": "Zodiac Z32",
        "when": "1970",
        "kind": "32-symbol map cipher",
        "summary": "This 32-symbol message accompanied a San Francisco Bay Area map and was said to concern a bomb location. It has not been definitively decoded; map context does not by itself turn a candidate reading into proof.",
        "boundary": "A credible solution must account for the full symbol sequence and produce a falsifiable connection to the accompanying map.",
        "source_label": "History’s overview of the Zodiac ciphers",
        "source_url": "https://www.history.com/articles/the-zodiac-ciphers-what-we-know",
    },
    {
        "title": "Dorabella Cipher",
        "when": "1897",
        "kind": "87-glyph personal cryptogram",
        "summary": "Composer Edward Elgar’s note to Dora Penny uses a small set of curved glyphs. Textual and musical interpretations have been proposed, but no reading has gained consensus as the intended message.",
        "boundary": "The short text admits many plausible readings; historical fit and an exact, consistently applied key are required before calling one a solution.",
        "source_label": "Nautilus on Elgar’s cipher",
        "source_url": "https://nautil.us/the-artist-of-the-unbreakable-code-234588",
    },
    {
        "title": "Beale Ciphers 1 &amp; 3",
        "when": "Published 1885",
        "kind": "Number-cipher / treasure legend",
        "summary": "Of the three number ciphers in the Beale Papers, only cipher 2 has a demonstrated Declaration of Independence key. The location and heir messages, ciphers 1 and 3, remain open—and the underlying treasure story itself is unverified.",
        "boundary": "The archive separates the unsolved texts from the historical claim: a decryption would not by itself authenticate the treasure narrative.",
        "source_label": "Cipher Museum’s provenance note",
        "source_url": "https://ciphermuseum.com/ciphers/beale.html",
    },
    {
        "title": "Voynich Manuscript",
        "when": "15th–16th century",
        "kind": "Undeciphered manuscript / script",
        "summary": "Beinecke MS 408 is written in an unidentified script by an unknown author. It is not established that the writing is a cipher at all; cryptographic approaches have not produced an accepted decipherment.",
        "boundary": "This belongs in an undeciphered-script archive, not in a list of solved cipher systems. Yale provides high-resolution research images.",
        "source_label": "Yale Beinecke’s record and scans",
        "source_url": "https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript",
    },
    {
        "title": "Phaistos Disc",
        "when": "Bronze Age Crete",
        "kind": "Undeciphered inscribed object",
        "summary": "The unique spiral object bears more than 240 stamped signs. Its script, language, purpose, and even whether it should be treated as ordinary text remain unresolved because there is no comparable corpus or bilingual key.",
        "boundary": "Proposed readings are not established decipherments. The archive labels it an undeciphered object rather than assuming a specific cipher mechanism.",
        "source_label": "Ancient Near East Today on the object’s context",
        "source_url": "https://anetoday.org/phaistos-disk/",
    },
]


def unsolved_archive_html() -> str:
    """Render the curated archive with sources and a verification boundary."""
    cards = []
    for item in UNSOLVED_ARCHIVE:
        cards.append(
            f"""    <section class="unsolved-entry">
      <div class="unsolved-meta"><span>{item["kind"]}</span><span class="status status-unsolved">unresolved</span></div>
      <h3>{item["title"]}</h3>
      <p class="unsolved-date">{item["when"]}</p>
      <p>{item["summary"]}</p>
      <p class="unsolved-boundary"><strong>Verification boundary:</strong> {item["boundary"]}</p>
      <p class="unsolved-source"><a href="{item["source_url"]}" target="_blank" rel="noopener noreferrer">{item["source_label"]} ↗</a></p>
    </section>"""
        )
    return "\n".join(cards)


# A compact, interlinked reference rather than a grab-bag of thin SEO pages.
# Each article starts with the practical recognition clues, then explains the
# underlying operation, its historical context and the honest limits of the
# attack. The solver stays on the page so a reader can immediately test a clue.
WIKI_PAGES = [
    {
        "slug": "cipher-wiki.html",
        "title": "Cipher Wiki — A Field Guide to Classical Codes and Ciphers",
        "desc": "A practical field guide to classical ciphers: how to recognise Caesar, Vigenère, substitution and Playfair, how they work, and what actually breaks them.",
        "h1": "Cipher Wiki",
        "tagline": "Recognise the shape. Understand the mechanism. Know what an answer is worth.",
        "preset": "caesar",
        "faqs": [
            ("What is the difference between a code and a cipher?",
             "A code substitutes whole words or ideas from a shared book or table. A cipher transforms letters or bytes according to a repeatable rule and a key. Classical puzzle writing often calls both ciphers, but the distinction matters when you decide how to attack a message."),
            ("Can this site break every cipher in the wiki?",
             "The browser solver targets the shift family, the periodic family (Vigenère, Beaufort, Variant Beaufort, Porta, Gronsfeld, Trithemius and autokey), monoalphabetic substitution, rail fence and several encodings. The full version of the project searches 50 ciphers — the Hill matrix cipher and the M-94 wheel among them — with quadgram models in six languages. Modern encryption such as AES and RSA is not a classical cipher and is not breakable by these methods."),
            ("How much ciphertext is enough?",
             "A short Caesar message may need only a few words because there are 26 keys. A substitution cipher needs roughly 100 letters to become comfortable. Playfair and other polygraphic systems need hundreds or more because the key has much more structure, and a wheel cipher such as the M-94 wants 200 letters or more before the disk order is pinned down."),
            ("Who writes this wiki?",
             "The facts — family, key type, keyspace, minimum text, worked examples — are generated from the solver's own cipher registry every time the site is built, and the round trips are verified, so an article cannot quietly disagree with the tool it documents. The history and context are editorial. The full source is on GitHub."),
        ],
        "body": """    <section class="mp-banner">
      <h2>Welcome to the Cipher Wiki</h2>
      <p>A field guide to the fifty ciphers, codes and encodings this solver knows —
      one article each, with the facts generated from the solver's own registry and
      the worked examples produced by actually running the cipher. Read the article,
      then paste a real puzzle into the solver below it.</p>
    </section>

    <div class="mp-columns">
      <section class="mp-box mp-featured" aria-label="Featured article">
        <h2>Featured article</h2>
        <div id="mp-featured-slot">
          <h3 data-notoc><a href="{FEATURED_HREF}">{FEATURED_TITLE}</a></h3>
          <p>{FEATURED_DESC}</p>
          <p class="mp-readmore"><a href="{FEATURED_HREF}">Read the article →</a></p>
        </div>
      </section>
      <section class="mp-box mp-dyk" aria-label="Did you know">
        <h2>Did you know…</h2>
        <div id="mp-dyk-slot">
          <p>{DYK_FIRST}</p>
        </div>
      </section>
    </div>

    <h2 id="families">Every cipher, one article each</h2>
    <p>Grouped by family, straight from the solver's registry: the same
    descriptions, keyspaces and minimum text lengths the tool works from, so a page
    cannot quietly disagree with the code it documents. Articles marked
    <em>full version</em> describe ciphers the pip-installable solver breaks that the
    browser build does not.</p>
__CIPHER_INDEX__

    <h2 id="history">The history</h2>
    <ul>
      <li><a href="history-of-codebreaking.html">A history of codebreaking</a> — al-Kindi to Colossus, and where each technique in this solver came from.</li>
      <li><a href="famous-cryptanalysts.html">The codebreakers</a> — who broke what, and what it cost them.</li>
      <li><a href="famous-ciphers.html">Famous ciphers</a> — the ones that changed history, and the handful still unread.</li>
      <li><a href="unsolved-ciphers.html">Unsolved cipher archive</a> — seven famous open problems, their evidence boundaries, and source links.</li>
    </ul>

    <h2>Three measurements worth knowing</h2>
    <h3>Alphabet and formatting</h3>
    <p>Only dots and dashes suggests Morse; hexadecimal uses only <code>0–9</code> and
    <code>A–F</code>; base64 is usually a multiple of four characters and may end in
    <code>=</code>. For letter ciphers, note whether spacing survived. A transposition may lose
    word boundaries while a substitution normally keeps them.</p>
    <h3>Frequency</h3>
    <p>English has uneven letter frequencies: E, T, A and O are common; Q and Z are not. A
    single-alphabet substitution preserves that unevenness under new names. A repeating-key
    cipher mixes several distributions together, making the text look flatter.</p>
    <h3>Index of coincidence</h3>
    <p>The index of coincidence measures the chance that two drawn letters are the same.
    Ordinary English is near <code>0.067</code>; uniformly random letters are near
    <code>0.038</code>. It is a guide, not a verdict, but it is exceptionally useful for
    separating monoalphabetic and polyalphabetic puzzles.</p>

    <h2>What this wiki does not promise</h2>
    <p>Recognising a classical cipher does not mean a unique solution exists. Short messages can
    fit several keys; proper names and another language confuse an English scorer; and a
    one-time pad used correctly has no statistical weakness. Treat an automatic answer as a
    hypothesis backed by evidence, then read it and verify the recovered key.</p>""",
    },
    {
        "slug": "unsolved-ciphers.html",
        "title": "Famous Unsolved Ciphers and Undeciphered Scripts",
        "desc": "A sourced archive of seven famous unresolved cipher problems, with clear verification boundaries that separate a candidate reading from an accepted decipherment.",
        "h1": "Famous Unsolved Ciphers & Scripts",
        "tagline": "Open problems deserve sources, scope, and an honest standard of proof.",
        "preset": "caesar",
        "faqs": [
            ("Does unsolved mean nobody has proposed an answer?",
             "No. Many of these objects have many proposed readings. Here, unsolved means there is no generally accepted, reproducible decipherment that explains the full source material without arbitrary choices."),
            ("Are all of these conventional ciphers?",
             "No. The D’Agapeyeff and Zodiac entries are ciphertext challenges; the Voynich Manuscript and Phaistos Disc are undeciphered written objects. The distinction is stated on every card because it changes what a valid solution would look like."),
            ("Why are short cryptograms especially difficult?",
             "Short text provides too little redundancy to choose uniquely among keys and plaintexts. A candidate can look meaningful while many different candidates fit equally well. Independent verification is essential."),
        ],
        "body": f"""    <section class="mp-banner">
      <h2>Research archive, not a claim list</h2>
      <p>These are famous unresolved problems selected for accessible source material and clear limits. “Unresolved” does not mean every entry is necessarily a cipher, and it does not turn a plausible phrase into a verified solution.</p>
    </section>

    <h2>How to read the archive</h2>
    <p>Each card identifies the kind of evidence, links to a source, and states what would have to be shown before a proposed reading should be treated as established. That matters especially for tiny cryptograms, where a name or phrase can be fitted after the fact. For the active Kryptos challenges, see the separate <a href="{KRYPTOS_HREF}">Kryptos research explorer</a>.</p>

    <div class="unsolved-grid">
{unsolved_archive_html()}
    </div>

    <h2>What is not a solution</h2>
    <p>A readable fragment, a favorable n-gram score, a thematic story, or a coincidence with a map or historical event is evidence to investigate—not a decipherment. A strong solution gives a complete method, applies it consistently to the source, and leaves a result that another researcher can reproduce.</p>""",
    },
    {
        "slug": "caesar-cipher-wiki.html",
        "title": "Caesar Cipher Explained — History, Formula and How to Break It",
        "desc": "A clear guide to the Caesar cipher: its alphabet rotation formula, why it has only 26 keys, how frequency analysis breaks it, and where ROT13 fits in.",
        "h1": "The Caesar Cipher",
        "tagline": "A rotation so small it teaches nearly every idea behind classical cryptanalysis.",
        "preset": "caesar",
        "faqs": [
            ("What is the Caesar cipher formula?",
             "With A equal to 0 through Z equal to 25, encryption is C = P + k mod 26 and decryption is P = C − k mod 26. The key k is the number of places rotated around the alphabet."),
            ("Is ROT13 a Caesar cipher?",
             "Yes. ROT13 uses k = 13. Since 13 is exactly half of 26, encryption and decryption are the same operation: applying ROT13 twice returns the original text."),
            ("Why is it not secure?",
             "There are only 26 possible rotations, including the unchanged alphabet. A person can list them; a computer can score them all immediately. Frequency analysis is useful, but exhaustive search alone is enough."),
        ],
        "body": """    <h2>The operation</h2>
    <p>Write the alphabet twice and slide the lower copy by a fixed number of places. With a
    shift of three, <code>A → D</code>, <code>B → E</code> and <code>Z → C</code>. Every letter
    gets exactly the same treatment; punctuation and spaces are usually copied unchanged. That
    simple uniformity is both the cipher's appeal and its fatal weakness.</p>

    <h2>A tiny keyspace</h2>
    <p>The key can be any number from 0 to 25. Shift 0 says nothing was encrypted, so there are
    only 25 meaningful alternatives. Try each decryption and score the result for English
    trigrams such as <code>THE</code>, <code>ING</code> and <code>AND</code>. The correct shift
    rapidly separates itself from the other 24.</p>

    <h2>Recognising a Caesar shift</h2>
    <p>Word lengths, apostrophes, punctuation and repeated-letter patterns are unchanged. The
    most frequent ciphertext letter is often the encryption of E, and common short words remain
    the same shape. None of those clues is proof — a substitution cipher has similar surface
    properties — but a 26-shift sweep is so cheap that there is no reason to guess by eye.</p>

    <h2>History and legacy</h2>
    <p>The cipher is named for Julius Caesar, who reportedly used a fixed shift in Roman military
    correspondence. Its modern value is educational: it demonstrates modular arithmetic, the
    difference between a keyspace and a strong keyspace, and the reason letter statistics matter.
    ROT13 survives as a convention for hiding spoilers, not for protecting secrets.</p>

    <p>Next: learn why a repeating sequence of Caesar shifts is harder to spot in the
    <a href="vigenere-cipher-wiki.html">Vigenère cipher guide</a>.</p>""",
    },
    {
        "slug": "vigenere-cipher-wiki.html",
        "title": "Vigenère Cipher Explained — Keywords and the Kasiski Attack",
        "desc": "Learn how the Vigenère cipher uses a repeating keyword, how Kasiski examination and index of coincidence expose its period, and how each column is solved.",
        "h1": "The Vigenère Cipher",
        "tagline": "Several Caesar ciphers woven together by a keyword — clever, historic, and breakable.",
        "preset": "vigenere",
        "faqs": [
            ("Why was Vigenère called unbreakable?",
             "It hides ordinary letter frequencies better than a single substitution. Before the period was understood, analysts could not tell which of several shifts had enciphered each E. The repeated keyword is the weakness that eventually made systematic attacks possible."),
            ("What is Kasiski examination?",
             "Repeated ciphertext fragments can result from repeated plaintext fragments aligned under the same part of the keyword. Distances between them often share factors with the key length. It suggests periods to test; it does not recover the key on its own."),
            ("What makes a Vigenère cipher genuinely secure?",
             "If the key is truly random, as long as the message, used once and kept secret, the construction is a one-time pad. A repeating dictionary word is the critical flaw in ordinary Vigenère."),
        ],
        "body": """    <h2>A Caesar shift that changes every letter</h2>
    <p>Vigenère assigns each keyword letter a shift. With the key <code>LEMON</code>, the shifts
    11, 4, 12, 14 and 13 repeat across the message. The same plaintext letter may therefore
    encrypt to different ciphertext letters. This defeats the simple “most common letter is E”
    reasoning that breaks Caesar immediately.</p>

    <h2>Find the period before the key</h2>
    <p>If the key has five letters, take every fifth ciphertext character. Each resulting column
    was encrypted by one fixed Caesar shift. The attack is therefore: propose a key length, split
    into columns, and measure whether each column behaves like English. The average index of
    coincidence rises when the proposed period is a multiple of the real period.</p>

    <h2>Recover and refine</h2>
    <p>Once the period is known, compare each column's letter frequencies with expected English
    frequencies to choose a shift. That produces a first key. On short texts, refine it by changing
    one key letter at a time and rescoring the <em>whole</em> plaintext: language model context
    resolves columns too sparse for frequency analysis alone.</p>

    <h2>Limits of the method</h2>
    <p>Short messages and long keys leave too few letters in each column. A period that is a
    multiple of the true key can also look convincing; prefer the shortest key that explains the
    text. Variants such as Beaufort use a different algebraic direction but retain the same
    repeating-period weakness.</p>

    <p>For a cipher that uses one fixed alphabet instead, see the
    <a href="substitution-cipher-wiki.html">substitution cipher guide</a>.</p>""",
    },
    {
        "slug": "substitution-cipher-wiki.html",
        "title": "Substitution Cipher Explained — Patterns and Hill Climbing",
        "desc": "How monoalphabetic substitution ciphers and cryptograms work, why 26 factorial keys cannot be brute-forced, and how frequency patterns and hill climbing solve them.",
        "h1": "Substitution Ciphers",
        "tagline": "A colossal keyspace with a very human leak: the shape of language remains.",
        "preset": "substitution",
        "faqs": [
            ("How many keys does a substitution cipher have?",
             "A full mixed alphabet has 26 factorial possible permutations, about 4 × 10 to the power of 26. Exhaustive search is impractical, which is why substitution is more interesting than Caesar despite using the same basic idea."),
            ("What patterns survive a substitution?",
             "Every occurrence of a plaintext letter becomes the same ciphertext letter, so word lengths, repeated letters and repeated word patterns survive. THE and THAT have different letter-pattern signatures, and doubled letters strongly constrain guesses."),
            ("Why do solvers sometimes miss rare letters?",
             "A ciphertext that never uses Q, J or Z contains almost no evidence about where that plaintext letter maps. Several keys can decrypt the observed text equally well; context, a crib or more ciphertext resolves the ambiguity."),
        ],
        "body": """    <h2>A scrambled alphabet, used consistently</h2>
    <p>In a monoalphabetic substitution cipher, each plaintext letter maps to one different
    ciphertext letter for the entire message. A key might map A to Q, B to W and so on, but it
    need not follow any keyboard or keyword pattern. Unlike Caesar, there is no small numerical
    key to enumerate.</p>

    <h2>Why it still falls</h2>
    <p>English is highly redundant. E remains the commonest plaintext letter even after it is
    renamed; <code>THE</code> retains the pattern of three distinct letters; and <code>HELLO</code>
    retains the pattern <code>0-1-2-2-3</code>. Word boundaries make newspaper cryptograms easier,
    but continuous ciphertext still contains n-gram frequencies such as TH, HE and ING.</p>

    <h2>From hand solving to hill climbing</h2>
    <p>A hand solver starts with frequency counts, one-letter words, doubled letters and likely
    short words. An automatic solver starts similarly, then scores the decrypted text with a
    language model. It swaps two assignments in a candidate alphabet, keeps swaps that improve
    quadgram fitness, and restarts from perturbed keys to escape local optima. The result is a
    search guided by English rather than a futile walk through every permutation.</p>

    <h2>Use enough text</h2>
    <p>With fewer than about 60 letters, the statistical evidence is thin; with 150 or more,
    common patterns repeat and recovery becomes much steadier. Do not treat a beautifully
    English-shaped 30-letter output as proof. Verify that the recovered key consistently
    transforms the full message.</p>

    <p>For a pair-based cipher whose statistics are less familiar, continue to
    <a href="playfair-cipher-wiki.html">Playfair</a>.</p>""",
    },
    {
        "slug": "playfair-cipher-wiki.html",
        "title": "Playfair Cipher Explained — The 5×5 Grid and Digraph Rules",
        "desc": "Understand the Playfair cipher's 5×5 keyed square, its same-row, same-column and rectangle rules, padding behaviour, and why it needs long ciphertext to attack.",
        "h1": "The Playfair Cipher",
        "tagline": "A grid of 25 letters turns single-letter statistics into a pairwise problem.",
        "preset": "substitution",
        "faqs": [
            ("Why are I and J combined in Playfair?",
             "A 5 by 5 square holds 25 cells, but the Latin alphabet has 26 letters. Traditional English Playfair merges I and J into one cell. Other alphabets and six-by-six variants make different choices."),
            ("Why does Playfair insert X characters?",
             "A digraph cannot contain the same letter twice. A repeated letter is split with a filler, traditionally X, and an odd-length message gets a final filler. That means decryption returns the intended letters plus ambiguous Xs that a reader removes from context."),
            ("Can frequency analysis break Playfair?",
             "Single-letter frequency analysis is much less direct because Playfair encrypts pairs. Modern classical-cipher attacks score candidate decryptions by n-grams and use simulated annealing or genetic search to rearrange the grid. Long ciphertext is important."),
        ],
        "body": """    <h2>The keyed square</h2>
    <p>Playfair writes a keyword without duplicates into a 5×5 square, then fills the remaining
    cells with the unused alphabet. In the traditional English form I and J share a cell. Plaintext
    is normalised into pairs; repeated letters in one pair are separated with a filler such as X.</p>

    <h2>Three rules for every pair</h2>
    <p>If both letters are on the same row, encrypt each with the letter to its right. If they are
    in the same column, use the letter below. Otherwise they form the corners of a rectangle: keep
    each letter's row and take the other letter's column. Decryption reverses the row and column
    steps; the rectangle rule is its own inverse.</p>

    <h2>What to look for</h2>
    <p>Traditional Playfair ciphertext has an even number of letters, contains no J, and cannot
    have a doubled letter within a ciphertext pair. These are useful hints, not guarantees. A
    carefully prepared substitution message can share some of them, and variants may use a
    different alphabet or filler.</p>

    <h2>Why automated attacks are hard</h2>
    <p>The unknown key is a 25-cell permutation, not a short word. One wrong cell disrupts many
    pairs, creating a fitness landscape full of narrow local optima. Effective attacks combine
    broad exploration, such as simulated annealing, with population-based or hill-climbing
    refinement, scoring candidate plaintexts using tetragrams. Hundreds of letters help; thousands
    are better. If a puzzle supplies a likely keyword, test it first.</p>

    <p>Return to the <a href="cipher-wiki.html">cipher wiki field guide</a> for the other common
    classical families.</p>""",
    },
    {
        "slug": "m94-wheel-cipher.html",
        "title": "M-94 Wheel Cipher — The US Army's Disk Device, and How It Falls",
        "desc": "The M-94 wheel cipher explained: 25 mixed-alphabet disks on a spindle, how the 25-letter period betrays it, and why 25! disk orders still fall to hill climbing.",
        "h1": "The M-94 Wheel Cipher",
        "tagline": "Twenty-five mixed alphabets on a spindle: the US Army's field cipher, and how 25! disk orders still fall.",
        "preset": "vigenere",
        "faqs": [
            ("What was the M-94?",
             "A cylindrical cipher device used by the US Army from 1922 until 1943, and by the Navy as the CSP-488. Major Joseph Mauborgne designed it in 1917 from Colonel Parker Hitt's ideas, and the same wheel principle had been reinvented several times before, most famously by Thomas Jefferson around 1795."),
            ("How does it differ from Vigenère?",
             "Vigenère shifts each position by a key letter, so every column of the period is a Caesar cipher. On the M-94, every position of the period runs through its own completely scrambled alphabet, one per disk. The period is exactly 25 because there are 25 disks, and frequency analysis per column no longer works — each column needs its full mixed alphabet recovered."),
            ("Can this page break an M-94 message?",
             "No. The browser solver on this page handles the common puzzle families; a wheel cipher needs a hill-climbing search over disk orders with quadgram scoring, which is in the full version of the project. It recovers a genuinely secret 25-disk order from about 200 letters of ciphertext, and a suspected order can be tested instantly with a key hint."),
            ("Why is disk 17 famous?",
             "One of the standard disks spells ARMYOFTHEUS — 'ARMY OF THE US' — around its rim, starting at A, which is how the device's origin is identified at a glance. The full 25-disk set was public: it was engraved on every device manufactured, and only the spindle order was secret."),
            ("How much ciphertext does a break need?",
             "About 200 letters for a reliable recovery with a real search budget, and 150 is the floor below which even the true order cannot be proven — 25 wheels each want roughly six letters of evidence. Longer messages are dramatically easier; 300 or more usually falls within seconds."),
        ],
        "body": """    <h2>The device</h2>
    <p>Twenty-five brass disks, each about an inch and a half across, threaded onto a spindle in a
    frame. Every disk carries the alphabet in a different scrambled order around its rim, and the
    set of alphabets is fixed and public — what the enemy never knew was the <em>order</em> the
    disks were threaded in, which is one of 25 factorial arrangements: roughly a septillion, or
    about 83 bits. To encrypt, the sender turned the disks to spell the first 25 letters of the
    message along one row, then read the ciphertext off any other row. Twenty-five letters at a
    time, the whole message went round and round the spindle.</p>

    <h2>Why it is stronger than it looks</h2>
    <p>A Vigenère key of length 25 gives each position of the period a shift — a Caesar cipher
    with 26 possibilities, crackable by frequency analysis on a few dozen letters of that column.
    The M-94 gives each position an entire mixed alphabet with no relationship to its neighbours.
    Nothing about column 1 tells you column 2, and the flat letter statistics that expose a
    monoalphabetic substitution never appear. When it was adopted in 1922 it was genuinely strong
    for field traffic, and the Army used it for low-level messages into the 1940s.</p>

    <h2>Recognising wheel-cipher ciphertext</h2>
    <p>Letters only, no key rhythm, and statistics that look polyalphabetic: the index of
    coincidence sits near random because the same plaintext letter encrypts differently each time
    it appears. The tell is the period. Every 25th letter went through the same disk, so if you
    split the text into 25 columns, each column is a pure monoalphabetic substitution and its
    letter frequencies look natural — split it into any other number and they stay flat. A
    column-wise index-of-coincidence spike at exactly 25, on a message whose length is a multiple
    of 25 or close to one, is the fingerprint. (A Vigenère with a 25-letter key looks similar at
    this distance; the two are told apart by trying the cheap Vigenère attack first.)</p>

    <h2>How the orders fall</h2>
    <p>83 bits is far beyond brute force, but the search does not have to be blind. Swapping two
    disks on the spindle changes only the letters at two of the 25 positions, so a hill climb can
    start from a random order, swap pairs, and keep every swap that makes some reading of the
    message look more like language — measured with letter n-gram statistics, exactly as a
    substitution solver scores candidate alphabets. The row the sender read from is part of the
    key but costs nothing extra: with the disks in the true order, one of the 26 rows reads as
    plaintext and the other 25 read as noise, so the search simply scores the best row of each
    candidate order. A few thousand swaps, restarted from several random orders, converge on the
    true arrangement from about 200 letters. That is not a weakness of the implementation; it is
    what actually happened to wheel-cipher traffic, and why the device was retired.</p>

    <h2>Honest limits</h2>
    <p>Below about 150 letters the recovered order cannot be distinguished from a near-miss — 25
    wheels each want a handful of letters of evidence before the answer is proven rather than
    plausible, and a good solver says so instead of guessing. Short messages that also stack an
    encoding layer around the wheel are the hard case. If you are working one by hand, look for
    the period-25 column structure first, then try the full version of the
    <a href="https://github.com/ahardkore/Buttcrack---Cipher-Breaker">buttcrack</a> solver with a
    generous budget, or hand it a suspected order as a key hint.</p>

    <p>Return to the <a href="cipher-wiki.html">cipher wiki field guide</a> for the other common
    classical families.</p>""",
    },
]


def wiki_index_section() -> str:
    """The wiki surfaced on the home page as article cards, not just a nav pill.

    Cards are generated from WIKI_PAGES and the history features, so adding an
    article there is all it takes for it to appear here — the links cannot
    dangle, because the cards and the pages they point at are written by the
    same loop in main(). The hub page is pulled out as a full-width featured
    card (its h1 would otherwise repeat the section heading), and each
    article's tagline doubles as its card blurb. The fifty generated cipher
    pages are one click deeper, through the hub — fifty cards would bury
    everything else on this page.
    """
    from wiki_history import HISTORY_PAGES

    cards = [
        f'      <a class="wiki-card" href="{spec["slug"]}">\n'
        f'        <h3>{spec["h1"]}</h3>\n'
        f'        <p>{spec["tagline"]}</p>\n'
        f'        <span class="wiki-more">Read the article →</span>\n'
        f'      </a>'
        for spec in WIKI_PAGES + HISTORY_PAGES if spec["slug"] != "cipher-wiki.html"
    ]
    return f"""    <section class="wiki-index" aria-label="Cipher wiki">
    <h2>Cipher wiki</h2>
    <p>The solver above breaks the puzzle; the wiki explains what was going on
    underneath. Fifty cipher articles — one per cipher in the registry, each
    with a worked example generated by running the cipher itself — plus
    long-form guides and a three-part history of codebreaking. Every article
    page carries the same solver, so you can test each idea on a real puzzle
    as you read.</p>
    <div class="wiki-grid">
      <a class="wiki-card featured" href="cipher-wiki.html">
        <h3>Start here: the wiki main page</h3>
        <p>Browse all fifty ciphers by family, catch the featured article, and
        read a ciphertext's alphabet, frequencies and index of coincidence
        before you guess at the cipher.</p>
        <span class="wiki-more">Open the cipher wiki →</span>
      </a>
{chr(10).join(cards)}
      <a class="wiki-card all-ciphers" href="cipher-wiki.html#families">
        <h3>All fifty cipher articles</h3>
        <p>Shift, substitution, polyalphabetic, transposition, polygraphic,
        wheel, XOR, codes and encodings — one encyclopedia page each, generated
        from the solver's registry.</p>
        <span class="wiki-more">Browse every cipher →</span>
      </a>
    </div>
    </section>"""


def build_products() -> tuple[list[dict], str]:
    """Generate the puzzle-book PDFs and their delivery pages.

    Files get content-hashed names so the download URLs are not guessable from
    the store page. That is deliberately light protection — it stops casual
    sharing of a tidy URL, nothing more. For hard entitlement checks you want a
    platform like Gumroad; for a five dollar puzzle book this is the right
    trade against running (and paying for) a licensing server.
    """
    from build_pdf import build as build_book  # imported late: needs PACKS on sys.path

    stripe = CFG.get("stripe", {})
    products = stripe.get("products", [])
    files_dir = HERE / "files"
    files_dir.mkdir(exist_ok=True)
    for stale in files_dir.glob("*.pdf"):
        stale.unlink()
    for stale in HERE.glob("thank-you-*.html"):   # drop pages from an old salt
        stale.unlink()

    built = []
    for product in products:
        tmp = files_dir / f"_tmp-{product['sku']}.pdf"
        build_book(product["puzzles"], product["seed"], product["title"], tmp)
        digest = hashlib.sha256(tmp.read_bytes()).hexdigest()[:16]
        final = files_dir / f"cryptograms-{product['sku']}-{digest}.pdf"
        tmp.rename(final)
        # Derived from the SKU and a fixed salt, never from file contents, so
        # the delivery URL you paste into Stripe keeps working across rebuilds.
        token = hashlib.sha256(
            f"{product['sku']}:{stripe.get('delivery_salt', '')}".encode()
        ).hexdigest()[:20]
        built.append({
            **product,
            "file": f"files/{final.name}",
            "size_kb": final.stat().st_size // 1024,
            "delivery": f"thank-you-{token}.html",
        })

    sampler_cfg = stripe.get("sampler")
    sampler_rel = ""
    if sampler_cfg:
        tmp = files_dir / "_tmp-sampler.pdf"
        build_book(sampler_cfg["puzzles"], sampler_cfg["seed"], sampler_cfg["title"], tmp)
        final = files_dir / "cryptograms-free-sampler.pdf"
        tmp.rename(final)
        sampler_rel = f"files/{final.name}"

    # One delivery page per product, reached only by Stripe's post-payment
    # redirect. Marked noindex so search engines never surface it.
    for product in built:
        (HERE / product["delivery"]).write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Your download — {html_escape(product['title'])}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header><div class="wrap">
  <h1>Thank you<span class="dot">.</span></h1>
  <p class="tagline">Your puzzle book is ready.</p>
</div></header>
<main class="wrap">
  <div class="card">
    <h2 style="margin-top:0">{html_escape(product['title'])}</h2>
    <p style="color:var(--muted)">{product['puzzles']} puzzles with full solutions · PDF · {product['size_kb']} KB</p>
    <p><a class="btn primary" style="display:inline-block;padding:11px 24px;border-radius:8px;
       background:var(--accent);color:#05230f;font-weight:700;text-decoration:none"
       href="{product['file']}" download>Download the PDF</a></p>
    <p style="font-size:14px;color:var(--muted);margin-bottom:0">
      Bookmark this page — the link stays valid. Lost it? Email the address on your
      Stripe receipt and it will be sent again.</p>
  </div>
  <div class="card">
    <p style="margin:0">While you are here, the
      <a href="index.html">cipher solver</a> is free and will crack any of these
      puzzles instantly if you get stuck.</p>
  </div>
</main>
<footer><div class="wrap"><p><a href="index.html">Back to the solver</a></p></div></footer>
</body>
</html>
""")
    return built, sampler_rel


def store_page(products: list[dict], sampler: str) -> str:
    pk = CFG.get("stripe", {}).get("publishable_key", "")
    if pk.startswith("sk_"):
        raise SystemExit(
            "site.json holds a SECRET Stripe key in publishable_key. Remove it and "
            "rotate that key in the Stripe dashboard immediately — secret keys must "
            "never reach a public site."
        )

    cards = []
    for product in products:
        link = payment_url(product.get("payment_link", ""), f"stripe.products[{product['sku']}].payment_link")
        button_id = product.get("buy_button_id", "")
        # A button id without the key it needs renders nothing at all, which
        # looks exactly like a product with no checkout. Say so instead.
        if button_id and not pk:
            raise SystemExit(
                f"site.json: {product['sku']} sets buy_button_id but stripe.publishable_key "
                f"is empty. Stripe's embedded button needs both; add the pk_live_... key or "
                f"clear buy_button_id to use the plain payment link."
            )
        if pk and button_id:
            # Stripe's embedded button: checkout happens in an overlay, so the
            # visitor never leaves the page. Publishable keys are meant to ship
            # in client HTML, so this is safe to commit and deploy.
            button = (f'<stripe-buy-button buy-button-id="{html_escape(button_id)}" '
                      f'publishable-key="{html_escape(pk)}"></stripe-buy-button>')
        elif link:
            button = (f'<a class="buy" href="{link}">Buy for {html_escape(product["price"])}</a>')
        else:
            button = ('<span class="soon">Payment link not configured yet — '
                      'see ventures/README.md</span>')
        cards.append(f"""    <div class="product">
      <h3>{html_escape(product['title'])}</h3>
      <p class="blurb">{html_escape(product['blurb'])}</p>
      <p class="spec">{product['puzzles']} puzzles · full solutions · PDF · {product['size_kb']} KB</p>
      {button}
    </div>""")

    free = ""
    if sampler:
        free = f"""  <div class="product free">
      <h3>Free sampler</h3>
      <p class="blurb">Ten puzzles from the collection, with solutions. No email, no checkout — just the file.</p>
      <a class="buy ghostbuy" href="{sampler}" download>Download free PDF</a>
    </div>"""

    return f"""    <h2>Printable cryptogram books</h2>
    <p>The solver on this site breaks ciphers. These books are the other direction: quiet,
    pencil-and-paper puzzles built from the same engine. Every quotation is a short fragment
    from a historical figure, every puzzle is graded, and every answer is in the back.</p>
    <div class="products">
{free}
{chr(10).join(cards)}
    </div>
    <p class="spec" style="margin-top:22px">Payment is handled by Stripe. Files are delivered
    instantly in the browser after checkout — no account, no mailing list, no subscription.</p>

    <h2>What is inside</h2>
    <p>Each volume opens with a page on technique — how to attack one-letter words, why
    <code>THE</code> is the most valuable guess you can make, which doubled letters to expect —
    then works from puzzles with several letters given up to puzzles with nothing at all. Every
    fifth puzzle is a Caesar rotation for a change of pace.</p>
    <p>They are typeset for US Letter with answer blanks under every character, so they print
    cleanly and are comfortable to work on directly.</p>"""


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def not_found_page() -> str:
    """The custom 404 GitHub Pages serves for any path that does not exist.

    Written by hand rather than through page() because it is deliberately not
    a normal page: noindex (a 404 in the sitemap or with a canonical would be
    a lie), no solver markup, no structured data — just the wiki chrome, the
    full sidebar so search still works, and links to the places people were
    almost certainly trying to reach. It goes into the link checker like
    every other page, but not into the sitemap.
    """
    header = f"""<header class="site-header site-header-compact">
  <div class="wrap wrap-wide">
    <a class="brand" href="index.html" aria-label="Buttcrack cipher solver home">
      <span class="brand-mark" aria-hidden="true">B</span>
      <span>buttcrack<span class="brand-dot">.</span></span>
    </a>
    <a class="wiki-wordmark" href="cipher-wiki.html">Cipher&nbsp;Wiki</a>
    {nav('404.html')}
  </div>
</header>"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page Not Found — Buttcrack Cipher Wiki</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="style.css">
{adsense_head()}{analytics()}
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
{header}

<main class="wrap wrap-wide" id="main-content">
  <div class="wiki-layout">
{wiki_sidebar('404.html')}
    <div class="wiki-content">
      <article class="wiki-article">
        <h1 class="wiki-title">Page not found</h1>
        <p class="wiki-from">Buttcrack Cipher Wiki</p>
        <div class="wiki-article-body">
          <p>There is no page at this address. It may have been mistyped, or it
          never existed — the wiki is a fixed set of articles, so nothing was
          moved here.</p>
          <ul>
            <li><a href="cipher-wiki.html">The cipher wiki main page</a> — the
            front door, with the featured article and the day's facts.</li>
            <li><a href="cipher-wiki.html#families">All fifty cipher articles</a>,
            grouped by family.</li>
            <li><a href="index.html">The cipher solver</a> — paste a puzzle and
            it works out the cipher, the key and the plaintext.</li>
            <li><a href="downloads.html">Printable puzzle books</a>, if a
            pencil-and-paper cryptogram was the errand.</li>
          </ul>
          <p>Or search the wiki from the box in the sidebar — every article on
          the site is in it.</p>
        </div>
      </article>
    </div>
  </div>
</main>

<footer>
  <div class="wrap">
    <p>Powered by <a href="{CFG['repo_url']}">buttcrack</a>, an open-source automatic cipher breaker.
    This browser build uses a compact trigram model; the <a href="windows-app.html">desktop
    version</a> searches 50 ciphers — including the M-94 wheel cipher — with quadgram models in
    six languages, and runs its own local interface entirely offline.</p>
    <p>For puzzles, CTFs and curiosity. Don't use it on anything you have no right to read.</p>
  </div>
</footer>

<script src="wiki-index.js"></script>
<script src="wiki.js"></script>
</body>
</html>
"""


def main() -> None:
    products, sampler = build_products()
    print(f"built {len(products)} puzzle book PDF(s)" + (" + free sampler" if sampler else ""))

    # After build_products, which clears every thank-you-*.html so a changed
    # salt cannot strand an old one.
    windows_app = windows_app_config()
    write_windows_delivery(windows_app)
    print(f"wrote {windows_app['delivery_page']:38} (Windows installer delivery page)")

    PAGES.append({
        "slug": "downloads.html",
        "title": "Printable Cryptogram Puzzle Books — PDF, Instant Download",
        "desc": "Printable cryptogram puzzle books as PDFs: graded easy to hard, full solutions included, plus a free ten-puzzle sampler. Instant download, no account needed.",
        "h1": "Puzzle Books",
        "tagline": "Pencil-and-paper cryptograms, graded and solved, as printable PDFs.",
        "preset": "substitution",
        "body": store_page(products, sampler),
        "faqs": [
            ("What format are the books in?",
             "PDF, typeset for US Letter paper with answer blanks under every character. They print cleanly on a home printer and are equally usable on screen."),
            ("Do I need an account to buy one?",
             "No. Checkout is handled by Stripe, and the download appears immediately afterwards in your browser. There is no account, no mailing list and no subscription."),
            ("Are the solutions included?",
             "Yes, every volume has a complete solutions section listing each quotation, its author and the key that was used."),
            ("Can I print copies for my classroom or club?",
             "Yes. Print as many copies as you need for your own group. Please do not redistribute the PDF itself or resell it."),
        ],
    })

    from wiki_ciphers import (
        FAMILY_PRESETS,
        FAMILY_TITLES,
        HAND_WRITTEN,
        _example,
        categories_for,
        cipher_page_specs,
        infobox_html,
        wiki_slug,
    )
    from wiki_history import HISTORY_PAGES

    from buttcrack.ciphers import get as get_cipher

    # The hand-written articles get the same encyclopedia chrome as the
    # generated ones — an infobox of registry facts, a category bar — so the
    # wiki reads as one publication rather than two glued together.
    for name in sorted(HAND_WRITTEN):
        slug = wiki_slug(name)
        for spec in WIKI_PAGES:
            if spec["slug"] == slug:
                info = get_cipher(name).info
                spec["wiki"] = {
                    "family": info.family.value,
                    "family_title": FAMILY_TITLES.get(info.family.value, info.family.value),
                    "infobox": infobox_html(info, _example(name)),
                    "categories": categories_for(info),
                    "lead": "",
                }
                spec["preset"] = FAMILY_PRESETS.get(info.family.value, spec["preset"])
                break

    # History features share a series box and a category of their own.
    for spec in HISTORY_PAGES:
        spec["wiki"] = {
            "family": "history",
            "family_title": "History of codebreaking",
            "infobox": history_series_infobox(spec["slug"]),
            "categories": [
                ("History of cryptography", "cipher-wiki.html#history"),
                ("Cipher wiki", "cipher-wiki.html"),
            ],
        }

    # The unresolved archive is editorial/history material, not a cipher in the
    # solver registry. Give it the same breadcrumb and category trail as the
    # history features without pretending the entries share one mechanism.
    for spec in WIKI_PAGES:
        if spec["slug"] == "unsolved-ciphers.html":
            spec["wiki"] = {
                "family": "history",
                "family_title": "History of codebreaking",
                "infobox": "",
                "categories": [
                    ("History of cryptography", "cipher-wiki.html#history"),
                    ("Unsolved ciphers", "unsolved-ciphers.html"),
                    ("Cipher wiki", "cipher-wiki.html"),
                ],
            }

    # The wiki main page: its infobox is the wiki's own stats, and it is the
    # one page without a breadcrumb (it is the breadcrumb root).
    for spec in WIKI_PAGES:
        if spec["slug"] == "cipher-wiki.html":
            spec["wiki"] = {
                "family": "",
                "family_title": "",
                "infobox": wiki_stats_infobox(),
                "categories": [],
                "is_hub": True,
            }

    generated = cipher_page_specs()
    print(f"generated {len(generated)} cipher wiki pages from the registry")

    meta = verification_meta()
    urls: list[str] = []
    written: dict[str, str] = {}
    # The storefront is appended above because its body depends on generated
    # products; the wiki is static and deliberately kept as a separate list so
    # a rebuild never appends duplicate reference pages in a long-lived process.
    for spec in PAGES + WIKI_PAGES + HISTORY_PAGES + generated:
        body = spec["body"]
        # The home page is the site's front door, and the wiki used to be one
        # nav pill deep. Surface the articles as the first content block under
        # the solver. Composed at render time rather than folded into the spec
        # so calling main() twice in one process cannot stack it twice.
        if spec["slug"] == "index.html":
            body = wiki_index_section() + "\n\n" + body
        # Same reason: the desktop storefront reads site.json and needs the
        # escaping helpers, so it is composed here rather than at import.
        if spec["slug"] == "windows-app.html":
            body = windows_app_html()
        # The wiki main page is assembled last-minute from the same data that
        # fills the sidebar and the search index, so all three agree by
        # construction. The static first entries are the no-JS fallback; the
        # browser rotates them daily.
        if spec["slug"] == "cipher-wiki.html":
            f_title, f_slug, f_desc = FEATURED_ARTICLES[0]
            body = (body
                    .replace("{FEATURED_TITLE}", f_title)
                    .replace("{FEATURED_HREF}", f_slug)
                    .replace("{FEATURED_DESC}", f_desc)
                    .replace("{DYK_FIRST}", DYK_FACTS[0])
                    .replace("__CIPHER_INDEX__", cipher_index_html()))
        html = page(**{**spec, "body": body})
        # A token configured but missing from a page means a silently unverified
        # property, which shows up as a Search Console failure days later. Fail
        # the build here instead, where the cause is obvious.
        if meta and meta.strip() not in html:
            raise SystemExit(f"verification tags missing from {spec['slug']}")
        (HERE / spec["slug"]).write_text(html)
        urls.append(spec["slug"])
        written[spec["slug"]] = html
        print(f"wrote {spec['slug']:38} {len(html):>6} bytes")

    # The browser-side search index: built from the pages this run actually
    # wrote, so the search box can never offer a page that does not exist.
    write_wiki_index_js(
        WIKI_PAGES + HISTORY_PAGES + generated
    )
    print(f"wrote wiki-index.js ({len(WIKI_PAGES) + len(HISTORY_PAGES) + len(generated)} searchable pages)")

    # Every registered cipher must have a page, and every page must be linked
    # from the wiki main page. Checked here rather than in a test so that
    # adding a cipher to the solver and forgetting its page fails the build
    # that would have published the gap.
    from buttcrack.ciphers import all_ciphers as _all_ciphers

    hub_html = written["cipher-wiki.html"]
    n_ciphers = 0
    for cipher in _all_ciphers():
        n_ciphers += 1
        slug = wiki_slug(cipher.info.name)
        if slug not in written:
            raise SystemExit(f"no wiki page for cipher {cipher.info.name!r} (expected {slug})")
        if f'href="{slug}"' not in hub_html:
            raise SystemExit(f"{slug} is not linked from the wiki main page")
    print(f"checked: every cipher has a linked wiki page ({n_ciphers} of them)")

    # GitHub Pages serves a custom 404 for any path that does not exist,
    # including mistyped cipher names. It is generated (so its links are
    # checked like everything else) but noindex, so it stays out of the
    # sitemap.
    not_found = not_found_page()
    (HERE / "404.html").write_text(not_found)
    written["404.html"] = not_found
    print(f"wrote {'404.html':38} {len(not_found):>6} bytes (custom not-found page)")

    # And the same guarantee for every internal link on every page: nothing
    # ships unless every href resolves.
    check_internal_links(written)
    print(f"checked: no broken internal links across {len(written)} pages")

    # The Kryptos explorer is a hand-written app rather than a generated page,
    # but it is part of this site once build_site.py mounts it, so it belongs in
    # the sitemap like everything else.
    urls.append(KRYPTOS_HREF)

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(
            f"  <url><loc>{CFG['base_url']}/{u}</loc>"
            f"<priority>{'1.0' if u == 'index.html' else '0.8'}</priority></url>\n"
            for u in urls
        )
        + "</urlset>\n"
    )
    (HERE / "sitemap.xml").write_text(sitemap)
    (HERE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {CFG['base_url']}/sitemap.xml\n"
    )
    print(f"wrote sitemap.xml and robots.txt ({len(urls)} pages)")

    for name in write_verification_files():
        print(f"wrote {name:38} (ownership proof)")

    # Ownership verification is the gate in front of every other SEO step, so
    # say plainly whether this build produced a verifiable site.
    names = re.findall(r'<meta name="([^"]+)"', meta)
    if names:
        print(f"\nverification tags on all {len(urls)} pages: {', '.join(names)}")
    elif not CFG.get("verification_files"):
        print("\nno ownership verification configured — set google_site_verification in "
              "site.json, then push (see ventures/README.md step 3)")

    # The delivery URLs are what you paste into each Stripe Payment Link as its
    # "after payment" redirect, so print them where you cannot miss them.
    print("\nStripe setup — set each payment link's post-payment redirect to:")
    for product in products:
        state = "LINK SET" if product.get("payment_link") else "needs payment_link"
        print(f"  {product['sku']:6} {CFG['base_url']}/{product['delivery']}   [{state}]")
    win_state = "LINK SET" if windows_app["payment_link"] else "needs payment_link"
    print(f"  {windows_app.get('sku', 'winapp'):6} {CFG['base_url']}/{windows_app['delivery_page']}"
          f"   [{win_state}]")

    # The installer is the one thing this build cannot produce (it needs
    # Windows) and the one thing a customer has paid for, so an unset
    # delivery_url is a silent broken sale rather than a broken page.
    if not windows_app["delivery_url"]:
        print(
            "\n  WARNING: windows_app.delivery_url is empty.\n"
            "  Anyone who buys right now gets a page promising the file by email.\n"
            "  Build the installer (packaging\\windows\\build.ps1), upload it to storage you\n"
            "  control — Cloudflare R2, Backblaze B2, S3 — and paste the URL into site.json.\n"
            "  Do not put it in this repository: the repo and the site are both public."
        )


if __name__ == "__main__":
    main()
