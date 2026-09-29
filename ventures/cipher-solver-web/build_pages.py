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
SAMPLES = json.loads((HERE / "samples.json").read_text())

NAV = [
    ("index.html", "Solver"),
    ("cipher-wiki.html", "Cipher wiki"),
    ("downloads.html", "Puzzle books"),
    ("caesar-cipher-decoder.html", "Caesar"),
    ("vigenere-cipher-solver.html", "Vigenère"),
    ("substitution-cipher-solver.html", "Substitution"),
    ("morse-code-translator.html", "Morse"),
    ("ctf-crypto-solver.html", "CTF crypto"),
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
    tip = CFG.get("stripe", {}).get("tip_jar_url", "")
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


def buy_button_script(body: str) -> str:
    """Stripe's script, included only on a page that actually uses the button."""
    if "<stripe-buy-button" not in body:
        return ""
    return '\n  <script async src="https://js.stripe.com/v3/buy-button.js"></script>'


def page(slug: str, title: str, desc: str, h1: str, tagline: str,
         preset: str, body: str, faqs: list[tuple[str, str]]) -> str:
    faq_html = "".join(
        f"<details class=\"faq\"><summary>{q}</summary><p>{a}</p></details>" for q, a in faqs
    )
    sample_buttons = "".join(
        f'<button data-sample="{key}">{label}</button>'
        for key, label in [
            ("caesar", "Caesar"), ("vigenere", "Vigenère"),
            ("substitution", "Substitution"), ("layered", "Layered"), ("morse", "Morse"),
        ]
    )
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
<meta property="og:type" content="website">
<link rel="stylesheet" href="style.css">
{app_jsonld(title, desc)}
{faq_jsonld(faqs) if faqs else ''}{buy_button_script(body)}{adsense_head()}{analytics()}
</head>
<body data-preset="{preset}">
<header class="site-header">
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
</header>

<main class="wrap">
  <section class="solver-shell" aria-label="Cipher solver">
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
    <p class="privacy">No account. No upload. No stored text. The complete solver runs in your browser.</p>
  </section>

  <div id="output" aria-live="polite"></div>

  {ad_slot()}

  <article>
{body}
    <h2>Frequently asked questions</h2>
    {faq_html}
  </article>

  {support_block()}
</main>

<footer>
  <div class="wrap">
    <p>Powered by <a href="{CFG['repo_url']}">buttcrack</a>, an open-source automatic cipher breaker.
    The browser build uses a compact trigram model; the command-line version searches far more ciphers
    with a full quadgram model.</p>
    <p>For puzzles, CTFs and curiosity. Don't use it on anything you have no right to read.</p>
  </div>
</footer>

<script src="model.js"></script>
<script src="app.js"></script>
</body>
</html>
"""


PAGES = [
    dict(
        slug="index.html",
        title="Cipher Solver — Break Any Classical Cipher Automatically (Free, No Upload)",
        desc="Paste ciphertext and this free tool works out which cipher was used, recovers the key and shows the plaintext. Caesar, Vigenère, substitution, XOR, base64, Morse and layered puzzles. Runs entirely in your browser.",
        h1="Cipher Solver",
        tagline="Paste ciphertext. It works out the cipher, finds the key, and shows the plaintext.",
        preset="caesar",
        faqs=[
            ("Do I need to know which cipher was used?",
             "No. The solver characterises the text first — index of coincidence, entropy, character set — then tries every cipher it knows and ranks the candidate plaintexts with an English trigram language model. You just paste and press the button."),
            ("Is my ciphertext uploaded anywhere?",
             "No. There is no server. The entire solver, including the language model, is JavaScript that your browser downloads once and runs locally. You can disconnect from the internet after the page loads and it still works."),
            ("Which ciphers can it break?",
             "Caesar and ROT13, Atbash, affine, Vigenère with automatic key recovery, monoalphabetic substitution, rail fence transposition, single-byte XOR, and the encoding layers base64, hex, binary, decimal bytes, Morse and reversed text — including several of those stacked on top of each other."),
            ("Why did it fail on my text?",
             "The most common reasons are that the text is too short (under about 40 letters there is not enough statistical signal), the plaintext is not English, or the cipher is outside the set above. Longer ciphertext is dramatically easier to break than short ciphertext."),
            ("Can it break modern encryption like AES or RSA?",
             "No, and neither can anything else you will find on the web. This tool targets classical and puzzle ciphers. Properly implemented modern encryption is not breakable by frequency analysis or key search."),
        ],
        body="""    <h2>What this does</h2>
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
    ),
    dict(
        slug="caesar-cipher-decoder.html",
        title="Caesar Cipher Decoder — Decrypt Without Knowing the Shift",
        desc="Free Caesar cipher decoder that finds the shift for you. Paste the ciphertext and get the plaintext plus the key. Also handles ROT13 and Atbash. No upload, runs in your browser.",
        h1="Caesar Cipher Decoder",
        tagline="Don't know the shift? It tries all 26 and picks the English one.",
        preset="caesar",
        faqs=[
            ("How do I decode a Caesar cipher without the key?",
             "There are only 26 possible shifts, so you try them all and pick the one that produces English. This page automates both halves: it generates all 26 candidates and scores each with a trigram language model, so the correct shift is chosen without you reading through the list."),
            ("Is ROT13 the same thing?",
             "ROT13 is a Caesar cipher with a shift of exactly 13. Because 13 is half of 26, applying it twice returns the original text, which is why it is used for hiding spoilers rather than for security."),
            ("What is the difference between Caesar and Atbash?",
             "Caesar rotates the alphabet by a fixed amount. Atbash reflects it, mapping A to Z, B to Y and so on. Atbash has no key at all, so there is only one possible decryption. This tool tests both."),
            ("The shift looks right but some words are wrong. Why?",
             "A Caesar cipher applies one shift to the whole message, so if part of it decodes and part does not, you are probably looking at a Vigenère cipher, which uses a repeating sequence of shifts. Try the Vigenère page."),
        ],
        body="""    <h2>How the Caesar cipher works</h2>
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
    ),
    dict(
        slug="vigenere-cipher-solver.html",
        title="Vigenère Cipher Solver — Recovers the Key Automatically",
        desc="Break a Vigenère cipher without the keyword. This free solver finds the key length by index of coincidence, recovers the key letter by letter, and prints the plaintext. Runs in your browser.",
        h1="Vigenère Solver",
        tagline="No keyword needed — it recovers the key from the ciphertext itself.",
        preset="vigenere",
        faqs=[
            ("Can a Vigenère cipher be broken without the key?",
             "Yes. Because the key repeats, the ciphertext contains several interleaved Caesar ciphers. Find the key length and each of those can be solved independently by frequency analysis. This has been standard practice since Kasiski published the method in 1863."),
            ("How much ciphertext do I need?",
             "As a rough rule you want at least 20 letters per key character, so a six-letter key wants 120 letters or more. Shorter texts leave each position with too few samples for the statistics to be reliable, though the trigram refinement pass on this page recovers many borderline cases."),
            ("What if the key is as long as the message?",
             "Then it is a one-time pad and it is genuinely unbreakable, provided the key is random and never reused. No tool can help. In practice puzzle keys are short repeating words."),
            ("Why did it return a key that is a repeated word, like LAMPLAMP?",
             "Any multiple of the true key length fits the ciphertext just as well. The solver penalises longer keys to prefer the shortest explanation, but on short texts a doubled key occasionally wins. The plaintext is still correct."),
        ],
        body="""    <h2>Why Vigenère resisted for 300 years</h2>
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
    ),
    dict(
        slug="substitution-cipher-solver.html",
        title="Substitution Cipher Solver — Automatic Cryptogram Breaker",
        desc="Solve monoalphabetic substitution ciphers and cryptograms automatically. Hill-climbing search with an English trigram model recovers the key without any hints. Free, no upload.",
        h1="Substitution Solver",
        tagline="Cryptograms cracked by hill-climbing search — no crib, no hints.",
        preset="substitution",
        faqs=[
            ("How long does the ciphertext need to be?",
             "About 60 letters is the practical minimum and 150 or more is comfortable. Unlike Caesar, there are 26 factorial possible keys, so the search relies on letter statistics and short texts simply do not contain enough of them."),
            ("Does it handle keyword-generated alphabets?",
             "Yes, implicitly. The solver searches for the mapping itself and does not care how the key alphabet was produced, so keyword ciphers, random alphabets and keyed Caesar variants are all the same problem to it."),
            ("Why is one or two letters wrong in the output?",
             "Rare letters like J, Q, X and Z appear too infrequently for the statistics to place them confidently, so they sometimes swap. The text is usually readable anyway and the correct letter is obvious from context."),
            ("Will it solve a newspaper cryptogram?",
             "Usually yes, if you paste the whole puzzle. Cryptograms preserve word boundaries, which makes them easier than the continuous-block ciphertext this solver is designed for."),
        ],
        body="""    <h2>A keyspace you cannot search</h2>
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
    ),
    dict(
        slug="morse-code-translator.html",
        title="Morse Code Translator & Decoder — Dots and Dashes to Text",
        desc="Translate Morse code to plain text instantly. Handles slashes, pipes or double spaces as word separators, and keeps decoding if there is another cipher underneath. Free, no upload.",
        h1="Morse Decoder",
        tagline="Dots and dashes in, readable text out — and it keeps going if there's a cipher underneath.",
        preset="morse",
        faqs=[
            ("What separators does it accept?",
             "Single spaces between letters, and a slash, a pipe or a double space between words. Mixed conventions in the same message are handled, which matters because puzzle sources are rarely consistent."),
            ("Can it decode Morse audio or flashing lights?",
             "No, this is a text tool. You need to transcribe the signal into dots and dashes first, then paste it here."),
            ("What if the decoded Morse is still gibberish?",
             "Then Morse was only the outer layer. This page automatically re-runs the full cipher search on whatever the Morse decodes to, so a Caesar shift or Vigenère cipher hidden underneath is peeled off in the same pass."),
            ("Does it support numbers and punctuation?",
             "Digits zero through nine are supported. Punctuation codes are rarer in puzzles and are skipped rather than guessed."),
        ],
        body="""    <h2>Reading Morse</h2>
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
    ),
    dict(
        slug="ctf-crypto-solver.html",
        title="CTF Crypto Solver — Base64, Hex, XOR and Layered Encodings",
        desc="Automatic solver for CTF crypto challenges: base64, hex, binary, single-byte XOR, repeating-key XOR and stacked encoding layers. Identifies and peels each layer. Free, browser-only.",
        h1="CTF Crypto Solver",
        tagline="Base64 around hex around XOR? It unwraps the whole stack.",
        preset="layered",
        faqs=[
            ("What is single-byte XOR and why is it everywhere in CTFs?",
             "Every byte of the plaintext is XORed with the same one-byte key. There are only 255 keys to try, so it is trivially breakable, which makes it the standard warm-up challenge in introductory CTF crypto categories."),
            ("How deep can the layers go?",
             "The browser version peels up to three encoding layers. The command-line version goes deeper and searches a wider cipher set, which is what you want for harder challenges."),
            ("Can it handle flag formats?",
             "Yes, incidentally — flags like ctf{...} are usually surrounded by enough English or structured text for the scoring to lock on. Very short flag-only inputs are harder because there is little statistical signal."),
            ("Why does it sometimes pick the wrong layer to unwrap?",
             "Hex and base64 character sets overlap, so a string can be validly interpretable as either. The solver tries both branches and keeps whichever produces the more English-like result rather than committing to the first guess."),
        ],
        body="""    <h2>The shape of a crypto challenge</h2>
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
    ),
]

# A compact, interlinked reference rather than a grab-bag of thin SEO pages.
# Each article starts with the practical recognition clues, then explains the
# underlying operation, its historical context and the honest limits of the
# attack. The solver stays on the page so a reader can immediately test a clue.
WIKI_PAGES = [
    dict(
        slug="cipher-wiki.html",
        title="Cipher Wiki — A Field Guide to Classical Codes and Ciphers",
        desc="A practical field guide to classical ciphers: how to recognise Caesar, Vigenère, substitution and Playfair, how they work, and what actually breaks them.",
        h1="Cipher Wiki",
        tagline="Recognise the shape. Understand the mechanism. Know what an answer is worth.",
        preset="caesar",
        faqs=[
            ("What is the difference between a code and a cipher?",
             "A code substitutes whole words or ideas from a shared book or table. A cipher transforms letters or bytes according to a repeatable rule and a key. Classical puzzle writing often calls both ciphers, but the distinction matters when you decide how to attack a message."),
            ("Can this site break every cipher in the wiki?",
             "The browser solver targets the common puzzle families: shifts, Vigenère, monoalphabetic substitution, rail fence and several encodings. The command-line project has a wider experimental set. Modern encryption such as AES and RSA is not a classical cipher and is not breakable by these methods."),
            ("How much ciphertext is enough?",
             "A short Caesar message may need only a few words because there are 26 keys. A substitution cipher needs roughly 100 letters to become comfortable. Playfair and other polygraphic systems need hundreds or more because the key has much more structure."),
        ],
        body="""    <h2>Start with the ciphertext, not a favourite cipher</h2>
    <p>A useful first question is not <em>which trick do I know?</em> but <em>what survives the
    transformation?</em> Spaces, punctuation, repeated letters, a restricted alphabet and the
    frequency of letters are clues. A Caesar shift preserves every word shape. A substitution
    preserves repeated patterns but changes the letter distribution. Vigenère flattens that
    distribution because one plaintext letter can encrypt several ways. Playfair works in pairs,
    so it leaves a different set of fingerprints again.</p>

    <h2>The field guide</h2>
    <ul>
      <li><a href="caesar-cipher-wiki.html">Caesar cipher</a> — one fixed rotation; 26 possibilities.</li>
      <li><a href="vigenere-cipher-wiki.html">Vigenère cipher</a> — a repeating keyword creates interleaved Caesar shifts.</li>
      <li><a href="substitution-cipher-wiki.html">Monoalphabetic substitution</a> — a scrambled alphabet, solved by language statistics.</li>
      <li><a href="playfair-cipher-wiki.html">Playfair cipher</a> — a 5×5 grid that transforms letter pairs.</li>
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
    ),
    dict(
        slug="caesar-cipher-wiki.html",
        title="Caesar Cipher Explained — History, Formula and How to Break It",
        desc="A clear guide to the Caesar cipher: its alphabet rotation formula, why it has only 26 keys, how frequency analysis breaks it, and where ROT13 fits in.",
        h1="The Caesar Cipher",
        tagline="A rotation so small it teaches nearly every idea behind classical cryptanalysis.",
        preset="caesar",
        faqs=[
            ("What is the Caesar cipher formula?",
             "With A equal to 0 through Z equal to 25, encryption is C = P + k mod 26 and decryption is P = C − k mod 26. The key k is the number of places rotated around the alphabet."),
            ("Is ROT13 a Caesar cipher?",
             "Yes. ROT13 uses k = 13. Since 13 is exactly half of 26, encryption and decryption are the same operation: applying ROT13 twice returns the original text."),
            ("Why is it not secure?",
             "There are only 26 possible rotations, including the unchanged alphabet. A person can list them; a computer can score them all immediately. Frequency analysis is useful, but exhaustive search alone is enough."),
        ],
        body="""    <h2>The operation</h2>
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
    ),
    dict(
        slug="vigenere-cipher-wiki.html",
        title="Vigenère Cipher Explained — Keywords, Kasiski and Index of Coincidence",
        desc="Learn how the Vigenère cipher uses a repeating keyword, how Kasiski examination and index of coincidence expose its period, and how each column is solved.",
        h1="The Vigenère Cipher",
        tagline="Several Caesar ciphers woven together by a keyword — clever, historic, and breakable.",
        preset="vigenere",
        faqs=[
            ("Why was Vigenère called unbreakable?",
             "It hides ordinary letter frequencies better than a single substitution. Before the period was understood, analysts could not tell which of several shifts had enciphered each E. The repeated keyword is the weakness that eventually made systematic attacks possible."),
            ("What is Kasiski examination?",
             "Repeated ciphertext fragments can result from repeated plaintext fragments aligned under the same part of the keyword. Distances between them often share factors with the key length. It suggests periods to test; it does not recover the key on its own."),
            ("What makes a Vigenère cipher genuinely secure?",
             "If the key is truly random, as long as the message, used once and kept secret, the construction is a one-time pad. A repeating dictionary word is the critical flaw in ordinary Vigenère."),
        ],
        body="""    <h2>A Caesar shift that changes every letter</h2>
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
    ),
    dict(
        slug="substitution-cipher-wiki.html",
        title="Substitution Cipher Explained — Cryptogram Patterns and Hill Climbing",
        desc="How monoalphabetic substitution ciphers and cryptograms work, why 26 factorial keys cannot be brute-forced, and how frequency patterns and hill climbing solve them.",
        h1="Substitution Ciphers",
        tagline="A colossal keyspace with a very human leak: the shape of language remains.",
        preset="substitution",
        faqs=[
            ("How many keys does a substitution cipher have?",
             "A full mixed alphabet has 26 factorial possible permutations, about 4 × 10 to the power of 26. Exhaustive search is impractical, which is why substitution is more interesting than Caesar despite using the same basic idea."),
            ("What patterns survive a substitution?",
             "Every occurrence of a plaintext letter becomes the same ciphertext letter, so word lengths, repeated letters and repeated word patterns survive. THE and THAT have different letter-pattern signatures, and doubled letters strongly constrain guesses."),
            ("Why do solvers sometimes miss rare letters?",
             "A ciphertext that never uses Q, J or Z contains almost no evidence about where that plaintext letter maps. Several keys can decrypt the observed text equally well; context, a crib or more ciphertext resolves the ambiguity."),
        ],
        body="""    <h2>A scrambled alphabet, used consistently</h2>
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
    ),
    dict(
        slug="playfair-cipher-wiki.html",
        title="Playfair Cipher Explained — The 5×5 Grid, Digraph Rules and Attacks",
        desc="Understand the Playfair cipher's 5×5 keyed square, its same-row, same-column and rectangle rules, padding behaviour, and why it needs long ciphertext to attack.",
        h1="The Playfair Cipher",
        tagline="A grid of 25 letters turns single-letter statistics into a pairwise problem.",
        preset="substitution",
        faqs=[
            ("Why are I and J combined in Playfair?",
             "A 5 by 5 square holds 25 cells, but the Latin alphabet has 26 letters. Traditional English Playfair merges I and J into one cell. Other alphabets and six-by-six variants make different choices."),
            ("Why does Playfair insert X characters?",
             "A digraph cannot contain the same letter twice. A repeated letter is split with a filler, traditionally X, and an odd-length message gets a final filler. That means decryption returns the intended letters plus ambiguous Xs that a reader removes from context."),
            ("Can frequency analysis break Playfair?",
             "Single-letter frequency analysis is much less direct because Playfair encrypts pairs. Modern classical-cipher attacks score candidate decryptions by n-grams and use simulated annealing or genetic search to rearrange the grid. Long ciphertext is important."),
        ],
        body="""    <h2>The keyed square</h2>
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
    ),
]


def wiki_index_section() -> str:
    """The wiki surfaced on the home page as article cards, not just a nav pill.

    Cards are generated from WIKI_PAGES, so adding an article there is all it
    takes for it to appear here — the links cannot dangle, because the cards
    and the pages they point at are written by the same loop in main(). The
    hub page is pulled out as a full-width featured card (its h1 would
    otherwise repeat the section heading), and each article's tagline doubles
    as its card blurb.
    """
    cards = [
        f'      <a class="wiki-card" href="{spec["slug"]}">\n'
        f'        <h3>{spec["h1"]}</h3>\n'
        f'        <p>{spec["tagline"]}</p>\n'
        f'        <span class="wiki-more">Read the guide →</span>\n'
        f'      </a>'
        for spec in WIKI_PAGES if spec["slug"] != "cipher-wiki.html"
    ]
    return f"""    <section class="wiki-index" aria-label="Cipher wiki">
    <h2>Cipher wiki</h2>
    <p>The solver above breaks the puzzle; these guides explain what was going
    on underneath. Each one covers how a cipher works, how to recognise it in
    the wild, and what actually breaks it — and every article page carries the
    same solver, so you can test each idea on a real puzzle as you read.</p>
    <div class="wiki-grid">
      <a class="wiki-card featured" href="cipher-wiki.html">
        <h3>Start here: the field guide</h3>
        <p>Recognise the shape. Understand the mechanism. Know what an answer is
        worth — read a ciphertext's alphabet, frequencies and index of
        coincidence before you guess at the cipher.</p>
        <span class="wiki-more">Read the field guide →</span>
      </a>
{chr(10).join(cards)}
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
    from build_pdf import build as build_book   # imported late: needs PACKS on sys.path

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
        link = product.get("payment_link", "")
        button_id = product.get("buy_button_id", "")
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


def main() -> None:
    products, sampler = build_products()
    print(f"built {len(products)} puzzle book PDF(s)" + (" + free sampler" if sampler else ""))

    PAGES.append(dict(
        slug="downloads.html",
        title="Printable Cryptogram Puzzle Books — PDF, Instant Download",
        desc="Printable cryptogram puzzle books as PDFs: graded easy to hard, full solutions included, plus a free ten-puzzle sampler. Instant download, no account needed.",
        h1="Puzzle Books",
        tagline="Pencil-and-paper cryptograms, graded and solved, as printable PDFs.",
        preset="substitution",
        body=store_page(products, sampler),
        faqs=[
            ("What format are the books in?",
             "PDF, typeset for US Letter paper with answer blanks under every character. They print cleanly on a home printer and are equally usable on screen."),
            ("Do I need an account to buy one?",
             "No. Checkout is handled by Stripe, and the download appears immediately afterwards in your browser. There is no account, no mailing list and no subscription."),
            ("Are the solutions included?",
             "Yes, every volume has a complete solutions section listing each quotation, its author and the key that was used."),
            ("Can I print copies for my classroom or club?",
             "Yes. Print as many copies as you need for your own group. Please do not redistribute the PDF itself or resell it."),
        ],
    ))

    meta = verification_meta()
    urls = []
    # The storefront is appended above because its body depends on generated
    # products; the wiki is static and deliberately kept as a separate list so
    # a rebuild never appends duplicate reference pages in a long-lived process.
    for spec in PAGES + WIKI_PAGES:
        body = spec["body"]
        # The home page is the site's front door, and the wiki used to be one
        # nav pill deep. Surface the articles as the first content block under
        # the solver. Composed at render time rather than folded into the spec
        # so calling main() twice in one process cannot stack it twice.
        if spec["slug"] == "index.html":
            body = wiki_index_section() + "\n\n" + body
        html = page(**{**spec, "body": body})
        # A token configured but missing from a page means a silently unverified
        # property, which shows up as a Search Console failure days later. Fail
        # the build here instead, where the cause is obvious.
        if meta and meta.strip() not in html:
            raise SystemExit(f"verification tags missing from {spec['slug']}")
        (HERE / spec["slug"]).write_text(html)
        urls.append(spec["slug"])
        print(f"wrote {spec['slug']:38} {len(html):>6} bytes")

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
    if products:
        print("\nStripe setup — set each payment link's post-payment redirect to:")
        for product in products:
            state = "LINK SET" if product.get("payment_link") else "needs payment_link"
            print(f"  {product['sku']:6} {CFG['base_url']}/{product['delivery']}   [{state}]")


if __name__ == "__main__":
    main()
