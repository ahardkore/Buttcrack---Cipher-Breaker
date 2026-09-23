"""XOR ciphers on raw bytes: single-byte and repeating-key.

XOR is where "cipher breaking" meets CTF reality: the payload arrives as hex or
base64, the key is short, and the plaintext is ASCII.  Two attacks cover the
whole family:

``single_byte``
    256 keys, so it is exhaustive.  Scoring uses the byte-level English metric
    in :meth:`LanguageModel.byte_score` (printable ratio + common letters), which
    separates the true key from the rest on as few as ~20 bytes.

``repeating_key``
    Recover the key length from the *normalised Hamming distance* between blocks
    (the correct length has markedly smaller edit distance because equal
    plaintext bytes XORed with equal key bytes cancel), corroborated by the index
    of coincidence of the cosets.  Then each key byte is an independent
    single-byte XOR, solved by frequency analysis, and the whole key is refined by
    maximising quadgram fitness of the decoded text.

Both accept hex, base64, base32 or raw bytes as input, which is what makes them
composable with the engine's layer peeler.
"""

from __future__ import annotations

import base64
import binascii
import re
from collections import Counter
from typing import Any, Iterator

from ..lang import BYTE_VALUE
from ..results import Candidate
from ..text import (
    A26,
    coset_byte_ic,
    divisors,
    index_of_coincidence,
    is_word_shaped,
    letters_only,
    normalised_hamming,
    trim,
)
from .base import CHEAP, MODERATE, Cipher, CipherInfo, CrackContext, Family

#: ``XOR_VALUE[k]`` is a ``bytes.translate`` table mapping a ciphertext byte to
#: its contribution to the English byte score when the key byte is ``k``.
#: Scoring a whole coset against all 256 candidates is then a C-level translate
#: plus a sum instead of a Python loop per byte -- the difference between a
#: 16-byte key costing milliseconds and costing seconds.  ``translate`` cannot
#: emit negative bytes, so every value is shifted up by ``BYTE_VALUE_OFFSET``;
#: the shift is the same for every candidate on a coset, so it cancels in the
#: comparison and the argmax is unchanged.
BYTE_VALUE_OFFSET = -min(BYTE_VALUE)
XOR_VALUE: tuple[bytes, ...] = tuple(
    bytes(BYTE_VALUE[b ^ k] + BYTE_VALUE_OFFSET for b in range(256)) for k in range(256)
)

#: Layers whose payload is raw bytes rather than text.  XOR sitting underneath
#: one of these is the most common constructed-cipher pattern there is, so it
#: earns a strong prior once such a layer has been peeled.
BYTE_LAYERS = frozenset(
    {"base16", "base64", "base32", "base58", "base85", "binary", "url", "decimal_ascii"}
)

#: Likelihood granted to a byte attack directly underneath a peeled byte encoding.
UNDER_BYTE_LAYER = 0.85


def minimal_period(key: bytes) -> bytes:
    """Shortest repeating unit of a solved key.

    A 16-byte key of ``LAMPLAMPLAMPLAMP`` decrypts exactly what ``LAMP`` does,
    and the key-length detector is free to report the multiple: cosets taken at
    four times the true period are still monoalphabetic, so they solve just as
    well.  Reducing to the smallest period is what makes the reported key the one
    the sender actually used.
    """
    n = len(key)
    for size in range(1, n + 1):
        if n % size == 0 and key == key[:size] * (n // size):
            return key[:size]
    return key


def key_text(key: bytes) -> str:
    """Render a solved byte key so it can be handed straight back as ``--key``.

    Printable keys are shown as text; anything else becomes ``hex:…``, which both
    :meth:`RepeatingKeyXOR._key_bytes` and the CLI's key parser understand.
    """
    reduced = minimal_period(key)
    if reduced and all(32 <= b < 127 for b in reduced):
        return reduced.decode("ascii")
    return f"hex:{reduced.hex()}"


def byte_layer_prior(ctx: "CrackContext") -> float:
    """Strong prior for XOR when a byte encoding has just been peeled away.

    ``hex -> XOR`` and ``base64 -> XOR`` are how constructed puzzles are built,
    and the payload of such a layer is bytes rather than letters -- exactly the
    case where the letter attacks only waste budget.  Ordering the byte attacks
    first there turns a ten second solve into a two second one.
    """
    steps = getattr(ctx, "steps", ()) or ()
    return UNDER_BYTE_LAYER if any(step in BYTE_LAYERS for step in steps) else 0.0


HEX_RE = re.compile(r"^[0-9a-fA-F\s]+$")
B64_RE = re.compile(r"^[A-Za-z0-9+/\s]+=*$")
B32_RE = re.compile(r"^[A-Z2-7\s]+=*$")

#: Relative frequencies of English letters plus space, for byte-level chi-squared.
#: Relative frequency of each byte in English prose, for the chi-squared column
#: solver.  Uppercase letters, digits and punctuation are included deliberately:
#: a table that says "capitals never happen" will happily trade the 'T' that
#: starts a sentence for a lowercase letter that fits the model better, and the
#: message comes back one character wrong.  The rates below are the classic
#: letter frequencies, with capitals at ~4% of their lowercase rate (weighted
#: towards the letters that actually start sentences), digits at ~0.1% each and
#: punctuation at its measured share.
_LOWER_RATES = {
    b" ": 0.172, b"e": 0.102, b"t": 0.075, b"a": 0.065, b"o": 0.062, b"i": 0.057,
    b"n": 0.057, b"s": 0.051, b"r": 0.049, b"h": 0.049, b"l": 0.033, b"d": 0.033,
    b"c": 0.023, b"u": 0.022, b"m": 0.020, b"f": 0.018, b"p": 0.016, b"g": 0.016,
    b"w": 0.016, b"y": 0.015, b"b": 0.012, b"v": 0.008, b"k": 0.005, b"x": 0.001,
    b"j": 0.001, b"q": 0.001, b"z": 0.001,
}
#: Letters that disproportionately open sentences and proper nouns.
_SENTENCE_STARTERS = frozenset(b"TAISWMHBDCLEPRGFNO")

ENGLISH_BYTES: dict[bytes, float] = dict(_LOWER_RATES)
for _b, _rate in _LOWER_RATES.items():
    if _b.isalpha():
        _upper = _b.upper()
        ENGLISH_BYTES[_upper] = _rate * (0.09 if _upper[0] in _SENTENCE_STARTERS else 0.02)
for _b, _rate in {b",": 0.006, b".": 0.007, b"'": 0.004, b'"': 0.002, b"-": 0.002,
                  b":": 0.001, b";": 0.0005, b"!": 0.0004, b"?": 0.0006,
                  b"(": 0.0005, b")": 0.0005, b"\n": 0.001, b"\t": 0.0002}.items():
    ENGLISH_BYTES[_b] = _rate
for _digit in b"0123456789":
    ENGLISH_BYTES[bytes([_digit])] = 0.0011
#: IC of uniformly random bytes -- the floor a real period has to beat.
RANDOM_BYTE_IC = 1.0 / 256

#: Floor for bytes the model has never seen: small, but not "impossible".
UNKNOWN_BYTE_RATE = 0.0004
_TOTAL = sum(ENGLISH_BYTES.values())
ENGLISH_BYTES = {b: v / _TOTAL for b, v in ENGLISH_BYTES.items()}
UNKNOWN_BYTE_RATE /= _TOTAL

def to_payload(text: str) -> tuple[bytes, str]:
    """Best-effort decode of a ciphertext into raw bytes.

    Returns ``(payload, encoding)`` where encoding is ``hex``, ``base64``,
    ``base32`` or ``raw``.  Detection is deliberately conservative: hex requires
    an even number of hex digits, base64 requires the right alphabet and a
    plausible length, and anything else is taken as raw bytes.
    """
    stripped = re.sub(r"[\s]", "", text)
    if not stripped:
        return b"", "raw"
    # Word-shaped text is a message, not a payload.  "Zdvkph uh dg qrrq" fits the
    # base64 alphabet exactly and decodes to bytes, which would make every short
    # Caesar ciphertext look like an XOR puzzle underneath an encoding.  Real
    # payloads are one unbroken run, MIME-wrapped at a fixed column, or separated
    # into byte pairs -- none of which are three-letter alphabetic words.
    word_shaped = is_word_shaped(text)
    if not word_shaped and HEX_RE.match(stripped) and len(stripped) % 2 == 0 and len(stripped) >= 4:
        # Digits-only strings are ambiguous with decimal; require at least one a-f.
        if re.search(r"[a-fA-F]", stripped):
            try:
                return bytes.fromhex(stripped), "hex"
            except ValueError:
                pass
    if not word_shaped and B32_RE.match(stripped) and len(stripped) >= 8 and not stripped.isdigit():
        try:
            padded = stripped + "=" * (-len(stripped) % 8)
            decoded = base64.b32decode(padded, casefold=False)
            if decoded:
                return decoded, "base32"
        except (binascii.Error, ValueError):
            pass
    if not word_shaped and B64_RE.match(stripped) and len(stripped) >= 8 and re.search(r"[A-Za-z]", stripped):
        try:
            padded = stripped + "=" * (-len(stripped) % 4)
            decoded = base64.b64decode(padded, validate=True)
            if decoded:
                return decoded, "base64"
        except (binascii.Error, ValueError):
            pass
    # latin-1 first: the engine peels encoding layers with latin-1 so that bytes
    # survive the round trip exactly, and XOR lives or dies on that -- re-encoding
    # a peeled 0xff as UTF-8 turns one byte into two and destroys the key
    # alignment.  Text with characters above 0xff can only be user-supplied.
    try:
        return text.encode("latin-1"), "raw"
    except UnicodeEncodeError:
        return text.encode("utf-8", "surrogateescape"), "raw"


def from_payload(payload: bytes, encoding: str) -> str:
    """Render decoded bytes back into text for scoring and display."""
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1", "replace")


class XORCipher(Cipher):
    """Shared input handling for byte-oriented attacks."""

    def prepare(self, text: str) -> str:
        return trim(text)

    def _payload(self, text: str) -> tuple[bytes, str]:
        return to_payload(text)


class SingleByteXOR(XORCipher):
    """Single-byte (repeating key of length 1) XOR."""

    info = CipherInfo(
        name="xor_single",
        title="Single-byte XOR",
        family=Family.XOR,
        key_type="one byte",
        keyspace=256,
        min_length=4,
        cost=CHEAP,
        aliases=("xor", "xor1", "single_byte_xor"),
        description="Every byte XORed with the same key byte. Exhaustively solvable over 256 keys.",
        example_key=0x42,
    )

    def encrypt(self, plaintext: str, key: Any = 0x42) -> str:
        data = plaintext.encode("utf-8", "surrogateescape")
        k = self._key_byte(key)
        return bytes(b ^ k for b in data).hex()

    def decrypt(self, ciphertext: str, key: Any = 0x42) -> str:
        payload, encoding = self._payload(ciphertext)
        k = self._key_byte(key)
        return from_payload(bytes(b ^ k for b in payload), encoding)

    @staticmethod
    def _key_byte(key: Any) -> int:
        if isinstance(key, dict):
            key = key.get("key", 0)
        if isinstance(key, bytes):
            return key[0] if key else 0
        if isinstance(key, str):
            # Every form this module reports has to be accepted back: "0x42",
            # "hex:42", "42", "B", "*".
            text = key.strip()
            prefixed = re.fullmatch(r"(?:0x|hex:)([0-9a-fA-F]{1,2})", text)
            if prefixed:
                return int(prefixed.group(1), 16)
            if re.fullmatch(r"[0-9a-fA-F]{2}", text):
                return int(text, 16)
            if re.fullmatch(r"\d{1,3}", text):
                return int(text) & 0xFF
            return ord(text[0]) if text else 0
        return int(key) & 0xFF

    def keys(self) -> Iterator[int]:
        yield from range(1, 256)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        payload, encoding = self._payload(ciphertext)
        if len(payload) < 2:
            return
        scored: list[tuple[float, int]] = []
        # Key 0x00 is the identity, so it is not a candidate answer.
        for k in range(1, 256):
            decoded = bytes(b ^ k for b in payload)
            scored.append((ctx.model.byte_score(decoded), k))
        scored.sort(key=lambda t: -t[0])
        for byte_score, k in scored[:8]:
            decoded = bytes(b ^ k for b in payload)
            text = from_payload(decoded, encoding)
            notes = {
                "key_byte": k,
                "key_hex": f"{k:02x}",
                "input_encoding": encoding,
                "byte_score": round(byte_score, 4),
                "method": "exhaustive 256-key search scored on English byte statistics",
            }
            letters = letters_only(text)
            if len(letters) >= 12:
                yield ctx.candidate(self.name, text, f"0x{k:02x}", steps=ctx.steps, **notes)
            else:
                # Not English text: report it anyway with a neutral confidence so
                # binary payloads (images, archives) are still surfaced.
                yield Candidate(
                    plaintext=text,
                    cipher=self.name,
                    key=f"0x{k:02x}",
                    confidence=0.0,
                    fitness=-9.0,
                    steps=ctx.steps,
                    notes=notes,
                )

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        payload, encoding = self._payload(text)
        if len(payload) < 4:
            return 0.0
        prior = byte_layer_prior(ctx)
        if encoding != "raw":
            # Hex/base64 payloads are worth a cheap 256-key sweep regardless.
            return max(0.55, prior)
        # Raw high-byte content is the classic single-byte XOR signature, and so
        # is simply sitting underneath a peeled byte encoding.
        high = sum(1 for b in payload if b > 126) / len(payload)
        return round(max(min(1.0, high * 2.0), prior), 4)


class RepeatingKeyXOR(XORCipher):
    """Repeating-key (multi-byte) XOR."""

    info = CipherInfo(
        name="xor_repeating",
        title="Repeating-key XOR",
        family=Family.XOR,
        key_type="byte string",
        min_length=16,
        cost=MODERATE,
        aliases=("repeating_xor", "xor_multi", "vigenere_bytes"),
        description="XOR with a repeating byte key. Key length from normalised Hamming distance, then per-byte frequency analysis.",
        example_key="KEY",
    )
    max_key_length = 40
    #: Cosets shorter than this give an IC estimate that is mostly noise.  Eight
    #: is a compromise: it lets a 16-byte key be considered on a 150-byte payload
    #: (marginal, but the plaintext decides) without letting 40-byte keys into a
    #: ranking that is then pure noise.
    MIN_COSET_BYTES = 8
    #: How many key lengths get a full column solve before the plaintext decides.
    LENGTH_SHORTLIST = 8
    #: A divisor of a leading length is worth attacking when it measures this
    #: close to its multiple (both are monoalphabetic at the true period).
    DIVISOR_IC_TOLERANCE = 0.85
    #: Lengths within this factor of the best IC are treated as tied, and the
    #: smallest of a tied group is attacked first.
    TIE_IC_TOLERANCE = 0.85

    def _key_bytes(self, key: Any) -> bytes:
        """Interpret a key given as text, bytes, an int or ``{"key": ...}``.

        A bare string is *text*: guessing that ``"AB"`` meant the byte 0xAB would
        silently decrypt with the wrong key, and ``AB`` is a perfectly ordinary
        two-byte key.  Raw bytes are written ``hex:ff10`` (or ``0xff10``), which is
        exactly the form :func:`key_text` reports, so a recovered key can always be
        fed back in.
        """
        if isinstance(key, dict):
            key = key.get("key", b"")
        if isinstance(key, str):
            text = key.strip()
            prefix = re.match(r"(?:hex:|0x)", text)
            if prefix:
                digits = text[prefix.end() :].replace(" ", "")
                try:
                    if re.fullmatch(r"[0-9a-fA-F]*", digits) and len(digits) % 2 == 0:
                        return bytes.fromhex(digits)
                except ValueError:
                    pass
            return key.encode("utf-8", "surrogateescape")
        if isinstance(key, int):
            return bytes([key & 0xFF])
        return bytes(key)

    def encrypt(self, plaintext: str, key: Any = "KEY") -> str:
        kb = self._key_bytes(key)
        if not kb:
            raise ValueError("empty key")
        data = plaintext.encode("utf-8", "surrogateescape")
        return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(data)).hex()

    def decrypt(self, ciphertext: str, key: Any = "KEY") -> str:
        payload, encoding = self._payload(ciphertext)
        kb = self._key_bytes(key)
        if not kb:
            raise ValueError("empty key")
        return from_payload(bytes(b ^ kb[i % len(kb)] for i, b in enumerate(payload)), encoding)

    # -- key length --------------------------------------------------------- #
    def candidate_key_lengths(self, payload: bytes, ctx: CrackContext) -> list[tuple[int, float]]:
        """Rank candidate key lengths, best explanation first.

        The statistic is the mean byte IC of the cosets (see
        :func:`~buttcrack.text.coset_byte_ic`): at the true key length every coset
        is monoalphabetic and keeps the skew of English bytes, while a wrong
        length mixes key bytes and flattens.  The classic normalised Hamming
        distance is kept as a tie-breaker -- it is the sharper test on long,
        letter-like payloads and the weaker one on short or binary ones, so the
        two cover each other.

        Multiples of the true length measure at least as well as the length
        itself (their cosets are monoalphabetic too, just shorter), so the
        divisors of the leaders are pulled into the list as well: solving a
        column is cheap, and the recovered plaintext is the final judge.
        """
        n = len(payload)
        max_len = min(self.max_key_length, max(2, n // self.MIN_COSET_BYTES))
        if max_len < 2 or n < 2 * self.MIN_COSET_BYTES:
            return []
        sizes = range(2, max_len + 1)
        ic = {size: coset_byte_ic(payload, size) for size in sizes}
        ham = {size: normalised_hamming(payload[: size * 16], size) for size in sizes}
        finite = [d for d in ham.values() if d != float("inf")]
        if not finite:
            return []
        best = max(ic.values())
        if best <= RANDOM_BYTE_IC:
            return []

        leaders = sorted(ic, key=lambda s: (-ic[s], ham[s]))[:8]
        shortlist: list[int] = []
        for size in leaders:
            for cand in (size, *divisors(size)):
                if cand < 2 or cand in shortlist or cand not in ic:
                    continue
                if cand != size and ic[cand] < self.DIVISOR_IC_TOLERANCE * ic[size]:
                    continue  # a divisor that measures badly is not the key
                shortlist.append(cand)

        # Among lengths that are statistically indistinguishable from the best,
        # the smallest is the key: a multiple can only look as good, never better
        # in expectation, so preferring it would fit 5-byte keys to a 20th of the
        # evidence each and get every fourth byte wrong.
        tie_line = self.TIE_IC_TOLERANCE * best
        shortlist.sort(key=lambda s: (0 if ic[s] >= tie_line else 1, s, ham[s]))
        span = max(best - RANDOM_BYTE_IC, 1e-9)
        out: list[tuple[int, float]] = []
        for size in shortlist[: self.LENGTH_SHORTLIST]:
            ic_quality = max(0.0, min(1.0, (ic[size] - RANDOM_BYTE_IC) / span))
            ham_quality = max(0.0, min(1.0, min(finite) / max(ham[size], 1e-9)))
            out.append((size, round(0.7 * ic_quality + 0.3 * ham_quality, 4)))
        return out

    def solve_key_byte(self, column: bytes) -> int:
        """Frequency-analysis solve of one key byte against English byte stats."""
        counts = Counter(column)
        total = len(column)
        best_key, best_chi = 0, float("inf")
        for k in range(256):
            chi = 0.0
            for byte, count in counts.items():
                plain = bytes([byte ^ k])
                expected = ENGLISH_BYTES.get(plain, UNKNOWN_BYTE_RATE) * total
                chi += (count - expected) ** 2 / max(expected, 1e-6)
            if chi < best_chi:
                best_chi, best_key = chi, k
        return best_key

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        payload, encoding = self._payload(ciphertext)
        if len(payload) < self.info.min_length:
            return
        hint = ctx.hints.get("key")
        if hint:
            kb = self._key_bytes(hint)
            text = from_payload(bytes(b ^ kb[i % len(kb)] for i, b in enumerate(payload)), encoding)
            yield ctx.candidate(self.name, text, key_text(kb), steps=ctx.steps, method="hint")
            return
        lengths = self.candidate_key_lengths(payload, ctx) or [(2, 0.0)]
        results: list[Candidate] = []
        for size, quality in lengths[: self.LENGTH_SHORTLIST]:
            if ctx.expired():
                break
            columns = [payload[i::size] for i in range(size)]
            if any(len(c) < 4 for c in columns):
                continue
            key = bytes(self.solve_key_byte(c) for c in columns)
            # Chi-squared gets an individual byte wrong whenever its column is
            # short, and one wrong key byte corrupts every size-th character of
            # the message, so the key is then refined and polished.
            key = self._refine_key(key, payload[: self.REFINE_WINDOW], ctx)
            key = self._polish(key, payload, ctx)
            decoded = bytes(b ^ key[i % size] for i, b in enumerate(payload))
            text = from_payload(decoded, encoding)
            printable = sum(1 for b in decoded if 32 <= b < 127 or b in (9, 10, 13)) / max(len(decoded), 1)
            results.append(
                ctx.candidate(
                    self.name,
                    text,
                    key_text(key),
                    steps=ctx.steps,
                    key_length=size,
                    key_hex=key.hex(),
                    input_encoding=encoding,
                    printable_ratio=round(printable, 4),
                    length_quality=quality,
                    method="coset IC key length + per-byte chi-squared + quadgram refinement",
                )
            )
            # A length that produces certain plaintext is the answer: the evidence
            # rule already refuses to call a column-starved fit certain, so there
            # is nothing to gain from solving the remaining lengths.
            if results[-1].certain:
                break
        results.sort(key=Candidate.sort_key)
        yield from results

    #: Payload bytes the cheap refinement pass looks at.
    REFINE_WINDOW = 1600
    #: Payload bytes the language-model polish pass looks at (``model.score`` is
    #: orders of dearer than a byte table lookup).
    POLISH_WINDOW = 600
    #: Above this many payload bytes per key byte the chi-squared solve and the
    #: byte-table refinement are decisive, and the polish pass is skipped.
    POLISH_MAX_BYTES_PER_KEY = 40

    def _refine_key(self, key: bytes, window: bytes, ctx: CrackContext) -> bytes:
        """Coordinate ascent on the byte score, scored one coset at a time.

        The score is a sum of per-byte terms, so a candidate for ``key[pos]`` is
        judged on ``window[pos::size]`` alone -- O(window) per pass instead of
        O(window * size), which is what makes a 16-byte key affordable.
        """
        size = len(key)
        if not size or len(window) < 2 * size:
            return key
        cosets = [window[i::size] for i in range(size)]
        for _ in range(3):
            improved = False
            for pos in range(size):
                if ctx.expired():
                    return key
                coset = cosets[pos]
                current = key[pos]
                best_byte = current
                best_value = sum(coset.translate(XOR_VALUE[current]))
                for cand in range(256):
                    if cand == current:
                        continue
                    value = sum(coset.translate(XOR_VALUE[cand]))
                    if value > best_value:
                        best_value, best_byte = value, cand
                if best_byte != current:
                    key = key[:pos] + bytes([best_byte]) + key[pos + 1 :]
                    improved = True
            if not improved:
                break
        return key

    def _polish(self, key: bytes, payload: bytes, ctx: CrackContext) -> bytes:
        """Re-check every key byte against the full language model.

        The column solver and the byte-statistic refinement are both unigram
        evidence, and unigram evidence has a blind spot: a single observation can
        decide a byte, so the capital 'T' that opens a sentence loses to whatever
        lowercase letter the frequency table likes better.  Quadgrams and the
        dictionary see the difference immediately ("The archive" vs "he archive"),
        so each key position gets its few most plausible alternatives re-scored
        properly.  Only the near-misses are tried, which keeps this cheap.
        """
        size = len(key)
        if not size or len(payload) >= size * self.POLISH_MAX_BYTES_PER_KEY:
            return key
        window = payload[: self.POLISH_WINDOW]
        if len(window) < 24:
            return key
        best = ctx.model.score(from_payload(bytes(b ^ key[i % size] for i, b in enumerate(window)), "raw"))
        for pos in range(size):
            if ctx.expired():
                break
            counts = Counter(window[pos::size])
            ranked = sorted(
                range(256),
                key=lambda k: -sum(n * ENGLISH_BYTES.get(bytes([b ^ k]), UNKNOWN_BYTE_RATE) for b, n in counts.items()),
            )
            for cand in ranked[:6]:
                if cand == key[pos] or ctx.expired():
                    continue
                trial = key[:pos] + bytes([cand]) + key[pos + 1 :]
                text = from_payload(bytes(b ^ trial[i % size] for i, b in enumerate(window)), "raw")
                score = ctx.model.score(text)
                if score.confidence > best.confidence:
                    best, key = score, trial
        return key

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        payload, encoding = self._payload(text)
        if len(payload) < 16:
            return 0.0
        prior = byte_layer_prior(ctx)
        if encoding != "raw":
            return max(0.5, prior)
        high = sum(1 for b in payload if b > 126) / len(payload)
        return round(max(min(1.0, high * 2.0) * 0.8, prior), 4)
