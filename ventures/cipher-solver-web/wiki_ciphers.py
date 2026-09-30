"""Wiki content: one page per cipher, plus the history articles.

Two sources feed these pages, deliberately separated.

*Facts* come from the solver's own registry at build time -- family, key type,
keyspace, cost class, minimum text, aliases, and the description each cipher
carries in its `CipherInfo`. Nothing here restates them by hand, so a page
cannot drift out of step with the code: change a cipher and its page changes.
The worked example is generated the same way, by actually encrypting a sample
with the cipher, so no page can show a ciphertext the tool would not produce.

*Context* -- where a cipher came from, who broke it, what it is worth knowing
for -- is written by hand below, because a registry cannot tell you that
Painvin broke ADFGVX in three months of 1918 or that Babbage kept quiet about
Vigenere for a decade.

The split matters for honesty as much as maintenance: the measurable claims are
machine-generated from the thing being described, and the historical claims are
editorial and stated as such.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buttcrack.ciphers import all_ciphers, get  # noqa: E402

#: Ciphers that already have a hand-written, long-form article. Generated pages
#: skip these rather than overwrite them -- a hand-written page on the Caesar
#: cipher can say more than a template ever will.
HAND_WRITTEN = {"caesar", "vigenere", "substitution", "playfair", "m94"}

#: The M-94's hand-written article predates the generated wiki and lives at a
#: URL search engines have already indexed, so it keeps its legacy slug.
#: Everything else follows the uniform ``<name>-cipher-wiki.html`` pattern.
SLUG_OVERRIDES = {"m94": "m94-wheel-cipher.html"}


def wiki_slug(name: str) -> str:
    """The page slug for a registered cipher, hand-written or generated."""
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    slug = f"{name}-cipher-wiki.html" if name in HAND_WRITTEN \
        else f"{name.replace('_', '-')}-cipher-wiki.html"
    return slug


#: What the compact browser solver on every page can break by itself. Used for
#: an honest category and infobox row: a visitor should be able to tell, from
#: the article alone, whether to press the button or install the full tool.
BROWSER_BREAKABLE = {
    "caesar", "rot13", "atbash", "affine", "vigenere", "substitution",
    "rail_fence", "xor_single", "base64", "base16", "binary", "decimal_ascii",
    "morse", "reverse",
}

#: Which preloaded sample fits each family, so an article about a Vigenere-type
#: cipher offers a Vigenere-type puzzle in the solver beneath it.
FAMILY_PRESETS = {
    "shift": "caesar",
    "polyalphabetic": "vigenere",
    "substitution": "substitution",
    "transposition": "layered",
    "polygraphic": "substitution",
    "wheel": "vigenere",
    "xor": "layered",
    "code": "morse",
    "encoding": "layered",
}

SAMPLE_PLAINTEXT = "MEET ME BY THE OLD CLOCK TOWER AT DAWN"

#: Quoted-printable is the identity on plain ASCII -- that *is* the encoding
#: working correctly -- so its page needs a sample with something to escape,
#: or the worked example would show the input unchanged and teach nothing.
SAMPLE_OVERRIDES = {"quoted_printable": "Meet me by the café at dawn — bring the map"}

FAMILY_TITLES = {
    "shift": "Shift and reciprocal alphabets",
    "polyalphabetic": "Polyalphabetic ciphers",
    "substitution": "Monoalphabetic substitution",
    "transposition": "Transposition ciphers",
    "polygraphic": "Polygraphic ciphers",
    "wheel": "Wheel and rotor devices",
    "xor": "Byte-level ciphers",
    "code": "Codes and alphabets",
    "encoding": "Encodings",
}

FAMILY_BLURBS = {
    "shift": "One fixed rule applied to every letter. The whole family falls to "
             "exhaustive search, which is why it survives as teaching material rather "
             "than as security.",
    "polyalphabetic": "Several alphabets in rotation, so one plaintext letter has several "
                      "ciphertext forms. Broken in two stages: find the period, then solve "
                      "each position as a simple shift.",
    "substitution": "A scrambled alphabet, fixed for the whole message. Letter frequencies "
                    "survive the substitution, which is exactly what breaks it.",
    "transposition": "The letters are the plaintext's own, only reordered. Frequencies are "
                     "untouched, so the attack is anagramming rather than statistics.",
    "polygraphic": "Letters are enciphered in groups, so single-letter frequencies flatten "
                   "and the unit of attack becomes the pair or the block.",
    "wheel": "Physical devices: a stack of mixed alphabets on a spindle. The key is the "
             "order of the disks, and the keyspace is enormous.",
    "xor": "Byte arithmetic rather than letter arithmetic. The natural home of CTF puzzles "
           "and the one family here that routinely carries non-text payloads.",
    "code": "Fixed symbol tables rather than keys. There is nothing to search: recognise "
            "the table and the message reads out.",
    "encoding": "Not secrecy at all -- transport formats. They are in the solver because "
                "puzzles wrap ciphers in them, often several deep.",
}

#: Per-cipher editorial context. ``how`` expands on the mechanism, ``breaking``
#: on what actually defeats it, ``history`` on where it came from. Kept short
#: on purpose: the registry supplies the specification, this supplies the part
#: a specification cannot.
NOTES: dict[str, dict[str, str]] = {
    "caesar": {
        "how": "Every letter moves the same number of places around the alphabet.",
        "breaking": "Twenty-six keys, one of which is the identity. Try them all.",
        "history": "Named for Julius Caesar, who Suetonius says shifted by three in his "
                   "private correspondence.",
    },
    "rot13": {
        "how": "A Caesar shift of thirteen. Because thirteen is half of twenty-six, "
               "encryption and decryption are the same operation.",
        "breaking": "There is no key to find. Apply it and read.",
        "history": "A Usenet convention from the early 1980s for hiding punchlines and "
                   "spoilers -- politeness rather than secrecy, and still used that way.",
    },
    "atbash": {
        "how": "The alphabet reversed onto itself: A becomes Z, B becomes Y. Applying it "
               "twice returns the original.",
        "breaking": "Keyless, so recognising it is the whole job.",
        "history": "A Hebrew scribal device older than any European cipher, and used in the "
                   "Book of Jeremiah, where Babel appears as Sheshach.",
    },
    "affine": {
        "how": "A linear map on letter positions: multiply by a, add b, reduce modulo 26. "
               "The multiplier must be coprime with 26 or the map is not reversible.",
        "breaking": "Twelve legal multipliers times twenty-six additions is 312 keys -- "
                    "an exhaustive sweep that takes milliseconds.",
        "history": "The generalisation that makes Caesar (a = 1) and Atbash (a = 25, b = 25) "
                   "the same cipher with different parameters.",
    },
    "rot47": {
        "how": "Caesar arithmetic over the 94 printable ASCII characters instead of 26 "
               "letters, so digits and punctuation rotate too.",
        "breaking": "Ninety-four keys. The catch is that a reading can be mostly "
                    "punctuation and still look plausible to a letters-only scorer, which "
                    "is why this solver checks letter density before believing one.",
        "history": "A programmer's joke that outlived the joke, now standard in CTF "
                   "puzzles where the payload is ASCII rather than prose.",
    },
    "reverse": {
        "how": "The message written backwards.",
        "breaking": "Keyless. Its real role is as a layer inside something else.",
        "history": "The oldest trick in the book, and Leonardo da Vinci's habit in his "
                   "notebooks -- mirror writing rather than cryptography.",
    },
    "vigenere": {
        "how": "A keyword selects a different Caesar shift for each position, repeating "
               "for the length of the message.",
        "breaking": "Find the period, then solve each column as a Caesar shift.",
        "history": "Misattributed for centuries: Giovan Battista Bellaso published it in "
                   "1553, and Blaise de Vigenere's name stuck to it anyway.",
    },
    "beaufort": {
        "how": "C = K - P rather than P + K, which makes the cipher its own inverse: "
               "encrypting a ciphertext with the same key returns the plaintext.",
        "breaking": "Identical to Vigenere -- period, then columns -- with the sign of the "
                    "column solve flipped.",
        "history": "Named for Sir Francis Beaufort, the admiral behind the wind scale, and "
                   "sold as a slide rule for the Royal Navy after his death.",
    },
    "variant_beaufort": {
        "how": "C = P - K. Vigenere's rule run in the decryption direction.",
        "breaking": "The same two-stage attack. A message solved under this name also "
                    "solves under Vigenere with the complementary key, which is why the "
                    "solver reports the better-known name on a tie.",
        "history": "The German army's variant, and a good illustration that a cipher's "
                   "identity is the algebra, not the label.",
    },
    "gronsfeld": {
        "how": "Vigenere with a numeric key, so each column has ten possible shifts "
               "instead of twenty-six.",
        "breaking": "Easier than Vigenere: the reduced alphabet cuts the per-column search "
                    "by more than half and makes short keys fall quickly.",
        "history": "Attributed to Count Gronsfeld in the seventeenth century, and popular "
                   "precisely because a digit key is easy to remember and to dictate.",
    },
    "porta": {
        "how": "Thirteen reciprocal alphabets, one per pair of key letters. No letter ever "
               "encrypts to itself, and the cipher is its own inverse.",
        "breaking": "Period finding as usual, then thirteen possibilities per column "
                    "rather than twenty-six -- a Porta column is easier than a Vigenere one.",
        "history": "Giambattista della Porta, 1563. His De Furtivis Literarum Notis also "
                   "described the first known digraphic cipher, three centuries before "
                   "Playfair made the idea practical.",
    },
    "quagmire3": {
        "how": "Vigenere arithmetic performed in a keyed alphabet's index space rather "
               "than A to Z, so the keyword and the alphabet are two separate secrets.",
        "breaking": "Given the alphabet it is Vigenere in disguise. Not given it, the "
                    "alphabet has to be searched too -- and a solver that assumes A = 0 "
                    "recovers nothing at all, because the per-column shift it finds is a "
                    "shift of the wrong alphabet.",
        "history": "The form used on the Kryptos sculpture at CIA headquarters, whose K1 "
                   "and K2 panels use the keyed alphabet KRYPTOSABCDEFGHIJLMNQUVWXZ. This "
                   "solver reproduces the published Paradigm Kryptos PK1 answer, keyword "
                   "PROVENANCE, from ciphertext alone.",
    },
    "sum_clock": {
        "how": "Several short wheels added together modulo 26, so the effective key is "
               "the least common multiple of their periods.",
        "breaking": "Four wheels of 4, 5, 6 and 7 give a key of period 420 -- longer than "
                    "a 153-letter message -- so no column repeats and column statistics "
                    "have nothing to work with. Two wheels are solved exactly: fix the "
                    "short one and what remains is a plain Vigenere of known period.",
        "history": "The engine behind several Paradigm Kryptos CTF challenges. PK3's two "
                   "wheels are literally the words ORDINATE and PENTIMENTO, which this "
                   "solver recovers in about five seconds.",
    },
    "trithemius": {
        "how": "The shift advances by a fixed step at every letter: a progressive key "
               "rather than a repeating one.",
        "breaking": "Only the starting point and the step are unknown, so 676 "
                    "possibilities cover every variant.",
        "history": "Johannes Trithemius, abbot and occultist, whose Polygraphia (1518) was "
                   "the first printed book on cryptography -- and whose Steganographia "
                   "looked so much like sorcery that it spent two centuries on the Index.",
    },
    "autokey": {
        "how": "A short primer starts the key and the plaintext itself continues it, so "
               "the key never repeats.",
        "breaking": "No period to find, which defeats the standard attack. Instead the key "
                    "is unwound in chains: guess the primer, and each recovered letter "
                    "reveals the next key letter.",
        "history": "Vigenere's own contribution, in 1586 -- the genuinely strong idea in "
                   "the book, and the one that did not catch on, because a single error "
                   "destroys everything after it.",
    },
    "substitution": {
        "how": "Each plaintext letter maps to a fixed ciphertext letter under a scrambled "
               "alphabet.",
        "breaking": "Letter frequencies, doubled letters and short words survive the "
                    "substitution; modern solvers hill climb over alphabets on n-gram "
                    "fitness.",
        "history": "The cipher al-Kindi broke in ninth-century Baghdad, inventing frequency "
                   "analysis and, with it, cryptanalysis.",
    },
    "keyword_substitution": {
        "how": "The mixed alphabet is generated from a keyword followed by the unused "
               "letters in order, which makes it memorable.",
        "breaking": "Exactly as hard as a random mixed alphabet to break by statistics, "
                    "but far easier to guess at, because the tail of the alphabet stays in "
                    "order and betrays the keyword's length.",
        "history": "The practical compromise of the pencil-and-paper era: a full random "
                   "alphabet is stronger but nobody can carry one in their head.",
    },
    "columnar": {
        "how": "The plaintext is written into a grid by rows and read out by columns in "
               "the order a keyword dictates.",
        "breaking": "Anagramming. Score every ordering of the columns by how well adjacent "
                    "letters form English bigrams, then refine the best.",
        "history": "The workhorse field cipher of both world wars, usually applied twice "
                   "(double transposition) because one pass leaves too much structure.",
    },
    "rail_fence": {
        "how": "The message zigzags across a number of rails and is read off rail by rail.",
        "breaking": "The only unknowns are the rail count and the starting offset, so a "
                    "few dozen readings cover every possibility.",
        "history": "A Civil War field cipher on both sides, valued for needing no "
                   "equipment beyond a stick to scratch lines in the dirt.",
    },
    "skip": {
        "how": "Take every k-th letter, then every k-th starting from the next, and so on.",
        "breaking": "One small unknown. Try every stride.",
        "history": "The scytale of Sparta in modern clothing: a strip of leather wound "
                   "round a baton of an agreed thickness, described by Plutarch.",
    },
    "route": {
        "how": "Letters fill a grid and are read out along a path -- spiral, boustrophedon, "
               "diagonal -- rather than straight down the columns.",
        "breaking": "The route and the width are the key, and there are not many plausible "
                    "routes, so the search is small.",
        "history": "The Union army's Route Cipher carried Lincoln's dispatches, mixing "
                   "transposition with codewords for names and places.",
    },
    "myszkowski": {
        "how": "A columnar transposition whose keyword has repeated letters: columns with "
               "equal key letters are read together, row by row, instead of one after "
               "another.",
        "breaking": "The interleaving means the ciphertext is no longer a concatenation of "
                    "whole columns, so the usual segment-boundary assumption fails. The key "
                    "space is the ordered Bell number of the width -- 4,683 at width six, "
                    "which this solver enumerates exactly.",
        "history": "Emile Myszkowski's 1902 answer to the obvious objection that a keyword "
                   "with repeated letters has no defined column order.",
    },
    "amsco": {
        "how": "The grid is filled with alternating runs of one and two letters, so the "
               "columns come out different lengths before the key even reorders them.",
        "breaking": "Two unknowns at once -- the column order and whether the first cell "
                    "took one letter or two -- and the uneven columns mean the attacker "
                    "cannot tell where in the ciphertext each column begins.",
        "history": "A twentieth-century American Cryptogram Association construction, "
                   "designed specifically to defeat the standard columnar attack.",
    },
    "playfair": {
        "how": "Letter pairs are transformed by their positions in a keyed five-by-five "
               "grid, with I and J sharing a cell.",
        "breaking": "Single-letter frequencies flatten, so the attack works on digraphs "
                    "and hill climbs the grid.",
        "history": "Invented by Charles Wheatstone in 1854 and promoted by Lord Playfair, "
                   "whose name it kept. Used in the Boer War and both world wars.",
    },
    "bifid": {
        "how": "Each letter becomes a pair of grid coordinates; the coordinates are written "
               "out in rows, then re-read in pairs within a fixed period.",
        "breaking": "Fractionation smears each plaintext letter across two ciphertext "
                    "letters, so the period and the grid must be recovered together. The "
                    "solver hill climbs per period and is honest that it is experimental.",
        "history": "Felix Delastelle, around 1901 -- the first practical cipher to combine "
                   "substitution with fractionation, an idea that runs straight through to "
                   "the rotor machines.",
    },
    "hill": {
        "how": "Blocks of n letters are treated as a vector and multiplied by an n-by-n "
               "matrix modulo 26. The matrix must be invertible mod 26, which means its "
               "determinant must be odd and not a multiple of 13.",
        "breaking": "Linearity is fatal. Decryption is row-separable -- each plaintext "
                    "position depends on one row of the inverse matrix -- so rows are "
                    "scored independently. That turns 157,248 invertible 2x2 keys into 676 "
                    "row evaluations, and makes 3x3 tractable at all.",
        "history": "Lester Hill, 1929, in the American Mathematical Monthly: the first "
                   "cipher built on linear algebra, and a teaching example ever since of "
                   "why linearity and secrecy sit badly together.",
    },
    "four_square": {
        "how": "Four five-by-five grids in a square; the plaintext pair is located in the "
               "two plain grids and read out of the opposite corners of the rectangle.",
        "breaking": "Fifty key cells -- two Playfair grids -- so a from-scratch search does "
                    "not finish. With either keyword known the rest follows quickly.",
        "history": "Delastelle again. It fixes Playfair's two embarrassments: doubled "
                   "letters need no padding, and no pair ever encrypts to itself reversed.",
    },
    "trifid": {
        "how": "Bifid in three dimensions: three coordinates per letter in a 3x3x3 cube, "
               "recombined within a period, so every output letter depends on three inputs.",
        "breaking": "The strongest fractionation in this collection, and the hardest to "
                    "attack from nothing: the 27-cell cube and the period have to be "
                    "recovered together.",
        "history": "Delastelle's last cipher, published posthumously in 1902.",
    },
    "m94": {
        "how": "Twenty-five disks, each carrying a mixed alphabet, threaded on a spindle in "
               "a secret order. Line up the plaintext along one row and read the ciphertext "
               "off another.",
        "breaking": "Polyalphabetic with period exactly 25 and no column that is a simple "
                    "shift. The attack hill climbs over disk orders, scoring each by its "
                    "best read row; it wants 200 letters and real time.",
        "history": "The US Army's M-94, in service from 1922 to the early 1940s, descended "
                   "from a wheel cipher Thomas Jefferson designed in the 1790s and then "
                   "left in his papers, unpublished, for a century.",
    },
    "xor_single": {
        "how": "Every byte is XORed with the same key byte.",
        "breaking": "Two hundred and fifty-six keys, scored by byte frequency. The first "
                    "exercise in every CTF crypto track.",
        "history": "Not a classical cipher but the most common one in practice, because it "
                   "is four lines of code and looks like encryption to anyone who does not "
                   "look twice.",
    },
    "xor_repeating": {
        "how": "A repeating byte key, XORed across the message. Vigenere over bytes.",
        "breaking": "Key length from normalised Hamming distance between blocks, then each "
                    "key byte by frequency analysis of its coset.",
        "history": "The cipher behind a long line of broken products, and still the answer "
                   "when a vendor says the data is 'encrypted' without naming an algorithm.",
    },
    "morse": {
        "how": "Dots and dashes per letter, with spacing carrying the boundaries.",
        "breaking": "A code, not a cipher: recognise the two symbols and decode. Puzzles "
                    "usually strip the spacing to make the boundaries ambiguous.",
        "history": "Samuel Morse and Alfred Vail, 1830s-40s. Vail reportedly set the code "
                   "lengths by counting type in a printer's case, which is why E is a "
                   "single dot -- frequency analysis put to constructive use.",
    },
    "bacon": {
        "how": "Five binary symbols per letter, so any two distinguishable things -- two "
               "typefaces, two letters, upright and italic -- can carry a message.",
        "breaking": "Find the two symbols and read off groups of five.",
        "history": "Francis Bacon, 1605: not merely a cipher but the first clear statement "
                   "that five bits suffice for an alphabet, three centuries before anyone "
                   "wrote 'bit'.",
    },
    "bacon_case": {
        "how": "Bacon's biliteral system hidden in the letter case of ordinary prose, so "
               "the message looks like innocent text.",
        "breaking": "Steganography rather than cryptography: the detection is the attack. "
                    "A mixed-case run whose length is a multiple of five is the tell.",
        "history": "Bacon's own intent -- he cared about concealing that a message exists, "
                   "which is a different problem from concealing what it says.",
    },
    "a1z26": {
        "how": "Letters replaced by their position in the alphabet.",
        "breaking": "Nothing to break. The only ambiguity is where numbers are split when "
                    "the separators are removed.",
        "history": "The first cipher most children invent, and a staple of escape rooms and "
                   "treasure hunts for exactly that reason.",
    },
    "polybius": {
        "how": "A five-by-five grid turns each letter into a pair of coordinates, with I "
               "and J sharing a cell.",
        "breaking": "Unkeyed, it is a decode. Keyed, it is a substitution cipher wearing "
                    "coordinates, and falls to the same statistics.",
        "history": "Polybius described the square in the second century BC as a way to "
                   "signal letters with two groups of torches -- telegraphy two millennia "
                   "early. Every fractionating cipher since is built on it.",
    },
    "tap_code": {
        "how": "The Polybius square struck out as taps: row, pause, column.",
        "breaking": "Recognise the two runs per letter. The arithmetic gives it away -- "
                    "every run is between one and five.",
        "history": "Taught by Captain Carlyle Harris to fellow prisoners in the Hanoi "
                   "Hilton in 1965, where it carried messages through cell walls for years. "
                   "C is sent as K to fit 25 cells.",
    },
    "nato": {
        "how": "One spelling-alphabet word per letter: Alfa, Bravo, Charlie.",
        "breaking": "Vocabulary. It is a code table, and the words announce themselves.",
        "history": "Adopted by NATO and ICAO in 1956 after testing which words survive a "
                   "bad radio link. Alfa and Juliett are spelled oddly on purpose, for "
                   "speakers who would not pronounce 'ph' or a final 't'.",
    },
    "braille": {
        "how": "Six-dot cells, one per letter, here in their Unicode form.",
        "breaking": "A reading system, not a cipher -- but puzzles use it as a layer.",
        "history": "Louis Braille, 1824, aged fifteen, adapting a military night-writing "
                   "system that Charles Barbier had designed so soldiers could read "
                   "dispatches without a lamp.",
    },
    "baudot": {
        "how": "Five bits per character on teleprinter tape, in the ITA2 letter table.",
        "breaking": "A five-bit stream is also valid Bacon, so both tables are decoded and "
                    "the one that reads as English wins.",
        "history": "Emile Baudot's 1870 code, later revised by Donald Murray, is why "
                   "'baud' is a unit -- and it is the tape that fed the Lorenz machine, "
                   "whose traffic Bletchley called Tunny.",
    },
    "base64": {"how": "Six bits per character over A-Z, a-z, 0-9, + and /.",
               "breaking": "Not encryption. Decode it.",
               "history": "The MIME workhorse: how binary survives systems that assume text."},
    "base32": {"how": "Five bits per character over A-Z and the digits 2-7.",
               "breaking": "Decode it.",
               "history": "Chosen so the alphabet survives being read aloud or typed by "
                          "hand -- no lowercase, and no 0/O or 1/l confusion."},
    "base16": {"how": "Hexadecimal: four bits per character.",
               "breaking": "Decode it.",
               "history": "The default way to show bytes to a human, and the usual outer "
                          "wrapper on a CTF XOR challenge."},
    "base58": {"how": "Base58 over the Bitcoin alphabet, which omits 0, O, I and l.",
               "breaking": "Decode it.",
               "history": "Designed by Satoshi Nakamoto for addresses that survive being "
                          "copied by eye."},
    "base85": {"how": "Five characters per four bytes, denser than base64.",
               "breaking": "Decode it.",
               "history": "From Adobe PostScript and PDF, where every byte of overhead "
                          "cost print time."},
    "url": {"how": "Percent escapes: %20 for a space.",
            "breaking": "Decode it.",
            "history": "RFC 3986. It appears in puzzles because URL-encoded text still "
                       "reads as English once the escapes are dropped, which fools naive "
                       "detectors."},
    "binary": {"how": "Eight bits per byte, usually space-separated.",
               "breaking": "Decode it.",
               "history": "The most recognisable encoding on earth, and therefore the most "
                          "common outer layer in a beginner puzzle."},
    "decimal_ascii": {"how": "Byte values in decimal.",
                      "breaking": "Decode it.",
                      "history": "Distinguishable from A1Z26 by arithmetic alone: values "
                                 "above 26 mean bytes, not letter positions."},
    "quoted_printable": {"how": "MIME quoted-printable: =XX escapes and soft line breaks.",
                         "breaking": "Decode it.",
                         "history": "The encoding email bodies arrive in, and the identity "
                                    "on plain ASCII -- which is why it can hide in plain "
                                    "sight until a single accented character appears."},
    "uuencode": {"how": "A begin header, length-prefixed lines of printable ASCII, then end.",
                 "breaking": "Decode it.",
                 "history": "Unix-to-Unix encoding, the pre-MIME way to post binaries to "
                            "Usenet, and still found in archived puzzle dumps."},
}


def _format_key(key) -> str:
    """Render a key the way a reader would type it, not the way Python prints it."""
    if key in (None, ""):
        return ""
    if isinstance(key, dict):
        return ", ".join(f"{k}={v}" for k, v in key.items())
    if isinstance(key, (list, tuple)):
        return ", ".join(str(v) for v in key)
    return str(key)


def _html_escape(s: str) -> str:
    """Example output goes into <pre><code>; base85 and friends emit <, > and &."""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


_COST_WORDS = {1.0: "cheap", 3.0: "moderate", 10.0: "expensive", 30.0: "brutal"}


def _cost_word(cost) -> str:
    return _COST_WORDS.get(cost, str(cost))


def _keyspace_text(info) -> str:
    if info.keyspace is None:
        return "unbounded"
    return f"{info.keyspace:,}"


def infobox_html(info, example=None) -> str:
    """The article infobox: the registry's facts, presented like an encyclopedia.

    Everything in the table is machine-generated from the cipher's own
    ``CipherInfo`` -- the same numbers the solver works from -- with the worked
    example's key shown so a reader can reproduce the round trip above.
    """
    rows = [
        ("Family", f'<a href="cipher-wiki.html#family-{info.family.value}">'
                   f"{FAMILY_TITLES.get(info.family.value, info.family.value)}</a>"),
        ("Key", info.key_type),
        ("Keyspace", _keyspace_text(info)),
        ("Search cost", _cost_word(info.cost)),
        ("Minimum text", f"{info.min_length} characters"),
    ]
    if info.aliases:
        rows.append(("Also known as", ", ".join(info.aliases)))
    if example and example[2]:
        rows.append(("Example key", f"<code>{_html_escape(example[2])}</code>"))
    rows.append((
        "Breaks in this browser",
        "yes — press Solve above" if info.name in BROWSER_BREAKABLE
        else "no — needs the <a href=\"https://github.com/ahardkore/Buttcrack---Cipher-Breaker\">full solver</a>",
    ))
    body = "".join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows)
    return (
        '<aside class="wiki-infobox" aria-label="Cipher facts">\n'
        f'      <div class="wiki-infobox-title">{info.title}</div>\n'
        f'      <div class="wiki-infobox-sub">{FAMILY_TITLES.get(info.family.value, info.family.value)}</div>\n'
        '      <table class="wiki-infobox-table"><tbody>\n'
        f'        {body}\n'
        '      </tbody></table>\n'
        '      <div class="wiki-infobox-note">Generated from the solver\'s cipher registry — '
        'these figures describe the implementation, not an idealised cipher.</div>\n'
        '    </aside>'
    )


def categories_for(info) -> list[tuple[str, str]]:
    """The category bar at the foot of the article, Wikipedia-style."""
    cats = [(
        FAMILY_TITLES.get(info.family.value, info.family.value),
        f"cipher-wiki.html#family-{info.family.value}",
    )]
    cats.append((
        "Breakable in the browser" if info.name in BROWSER_BREAKABLE
        else "Full-version ciphers",
        "cipher-wiki.html#family-" + info.family.value,
    ))
    cats.append(("Cipher wiki", "cipher-wiki.html"))
    return cats


def _example(name: str) -> tuple[str, str, str] | None:
    """Encrypt the sample with this cipher, live, at build time, and check it.

    Returns ``(plaintext, ciphertext, key)``. Generated rather than written out
    so a page can never show a ciphertext the solver would not produce -- and
    the round trip is verified here, so a page cannot show an example that does
    not decrypt back. A cipher that loses information by design (Playfair pads,
    Bacon merges I/J) is compared on the letters it promises to preserve.
    """
    cipher = get(name)
    key = cipher.info.example_key
    sample = SAMPLE_OVERRIDES.get(name, SAMPLE_PLAINTEXT)
    try:
        ciphertext = (
            cipher.encrypt(sample, key)
            if key not in (None, "")
            else cipher.encrypt(sample)
        )
        recovered = (
            cipher.decrypt(ciphertext, key)
            if key not in (None, "")
            else cipher.decrypt(ciphertext)
        )
    except Exception:
        return None
    if not ciphertext or ciphertext == sample:
        return None

    def letters(text: str) -> str:
        return "".join(c for c in text.upper() if c.isalpha())

    want, got = letters(sample), letters(recovered)
    lossy = {"playfair", "bifid", "polybius", "bacon", "bacon_case", "tap_code", "trifid"}
    if name not in lossy and not got.startswith(want[: min(len(want), len(got))][:20]):
        return None
    shown = ciphertext if len(ciphertext) <= 240 else ciphertext[:237] + "..."
    return sample, shown, _format_key(key)


def related_links(info, by_family) -> list[tuple[str, str]]:
    """Up to six sibling ciphers, as (title, slug) pairs, for the See-also box."""
    siblings = [
        c for c in by_family.get(info.family.value, [])
        if c.info.name != info.name
    ][:6]
    return [(c.info.title, wiki_slug(c.info.name)) for c in siblings]


def cipher_page_specs() -> list[dict]:
    """One page spec per registered cipher that has no hand-written article."""
    by_family: dict[str, list] = {}
    for cipher in all_ciphers():
        by_family.setdefault(cipher.info.family.value, []).append(cipher)

    specs = []
    for cipher in all_ciphers():
        info = cipher.info
        if info.name in HAND_WRITTEN:
            continue
        # The notes are written in plain ASCII for readability in the source;
        # the site's typography uses real dashes.
        notes = {k: v.replace(" -- ", " — ") for k, v in NOTES.get(info.name, {}).items()}
        family = info.family.value
        example = _example(info.name)
        related = related_links(info, by_family)

        if example:
            plain_shown, cipher_text, key = example
            key_line = f"<p>Key: <code>{_html_escape(key)}</code></p>" if key else "<p>No key — the transformation is fixed.</p>"
            example_html = f"""    <h2>A worked example</h2>
    <p>Encrypting a sample with the cipher itself, at build time:</p>
    <pre><code>{_html_escape(plain_shown)}</code></pre>
    {key_line}
    <p>produces the ciphertext</p>
    <pre><code>{_html_escape(cipher_text)}</code></pre>
    <p class="note">This example is generated by running the cipher when the page is built,
    and the round trip is checked, so it always matches what the solver does.</p>
"""
        else:
            example_html = ""

        see_also = " · ".join(
            f'<a href="{slug}">{title}</a>' for title, slug in related
        ) or "See the field guide."
        family_title = FAMILY_TITLES.get(family, family)
        lead = (
            f"<p><b>{info.title}</b> — {notes.get('how', info.description)}</p>\n"
            f"    <p>{info.description}</p>"
        )

        body = f"""{example_html}
    <h2>How it is broken</h2>
    <p>{notes.get('breaking', 'See the field guide for the general approach to this family.')}</p>

    <h2>History and context</h2>
    <p>{notes.get('history', 'A member of the ' + family_title + ' family.')}</p>

    <h2>See also</h2>
    <p>{see_also}</p>
    <p class="wiki-seealso-more">Browse every cipher in the
    <a href="cipher-wiki.html#family-{family}">{family_title}</a> family, read the
    <a href="history-of-codebreaking.html">history of codebreaking</a>, or return to the
    <a href="cipher-wiki.html">wiki main page</a>.</p>"""

        browser = info.name in BROWSER_BREAKABLE
        specs.append({
            "slug": wiki_slug(info.name),
            "title": f"{info.title} — How It Works and How It Is Broken",
            "desc": (f"{info.title}: {info.description} How to recognise it, "
                     f"a worked example, and the attack that breaks it."),
            "h1": info.title,
            "tagline": notes.get("how", info.description)[:150],
            "preset": FAMILY_PRESETS.get(family, "caesar"),
            "faqs": [
                (f"How is the {info.title} broken?",
                 notes.get("breaking", info.description)),
                (f"What key does the {info.title} use?",
                 f"{info.key_type}. "
                 + ("The keyspace is unbounded in practice."
                    if info.keyspace is None else f"There are {info.keyspace:,} possible keys.")),
                ("How much ciphertext do I need?",
                 f"At least {info.min_length} characters for this solver to attempt it; "
                 "short messages can be readable and still not be proof."),
                (f"Can I break a {info.title} on this page?",
                 ("Yes — the browser solver on this page handles it directly. Paste the "
                  "ciphertext into the solver and press the button."
                  if browser else
                  "Not with the browser build, which targets the common puzzle families. "
                  "The full version of the solver searches it — "
                  "pip install buttcrack, then buttcrack \"&lt;ciphertext&gt;\".")),
            ],
            "body": body,
            "wiki": {
                "family": family,
                "family_title": family_title,
                "infobox": infobox_html(info, example),
                "categories": categories_for(info),
                "lead": lead,
            },
        })
    return specs
