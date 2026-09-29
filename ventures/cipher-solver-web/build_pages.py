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
import sys
from pathlib import Path

HERE = Path(__file__).parent
PACKS = HERE.parent / "puzzle-packs"
sys.path.insert(0, str(PACKS))
CFG = json.loads((HERE / "site.json").read_text())
SAMPLES = json.loads((HERE / "samples.json").read_text())

NAV = [
    ("index.html", "All ciphers"),
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
<link rel="canonical" href="{CFG['base_url']}/{slug}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="style.css">
{app_jsonld(title, desc)}
{faq_jsonld(faqs) if faqs else ''}{buy_button_script(body)}{adsense_head()}{analytics()}
</head>
<body data-preset="{preset}">
<header>
  <div class="wrap">
    <h1>{h1}<span class="dot">.</span></h1>
    <p class="tagline">{tagline}</p>
    {nav(slug)}
  </div>
</header>

<main class="wrap">
  <textarea id="ciphertext" spellcheck="false"
    placeholder="Paste ciphertext here — you don't need to know which cipher it is."></textarea>
  <div class="controls">
    <button class="go" id="go">Break it</button>
    <button class="ghost" id="clear">Clear</button>
    <span class="samples">{sample_buttons}</span>
  </div>
  <p class="privacy">Runs entirely in your browser. Your text is never uploaded, logged or stored.</p>

  <div id="output"></div>

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

    urls = []
    for spec in PAGES:
        html = page(**spec)
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

    # The delivery URLs are what you paste into each Stripe Payment Link as its
    # "after payment" redirect, so print them where you cannot miss them.
    if products:
        print("\nStripe setup — set each payment link's post-payment redirect to:")
        for product in products:
            state = "LINK SET" if product.get("payment_link") else "needs payment_link"
            print(f"  {product['sku']:6} {CFG['base_url']}/{product['delivery']}   [{state}]")


if __name__ == "__main__":
    main()
