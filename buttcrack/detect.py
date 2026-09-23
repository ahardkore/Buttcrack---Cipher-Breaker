"""Cipher identification: work out what we are looking at before attacking.

Identification is a rule-based expert system over cheap statistics, and it
returns *reasons* rather than just a label -- the CLI and web UI print them, so a
user can see why the engine chose an attack.

The two most useful facts:

* A **monoalphabetic** cipher (Caesar, Affine, substitution) permutes the letter
  distribution, so its chi-squared distance from English is large while its index
  of coincidence stays English-like (~0.066).
* A **transposition** moves letters without changing them, so its chi-squared
  distance from English stays *small* (~0.1) while its n-gram fitness collapses.

Those two numbers together separate substitution from transposition from
polyalphabetic ciphers before a single key is tried.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Any

from .lang import LanguageModel, get_model
from .results import Hypothesis
from .text import (
    A26,
    best_key_length,
    entropy,
    index_of_coincidence,
    is_word_shaped,
    letters_only,
)

ENGLISH_IC = 0.0667
RANDOM_IC = 0.0385

#: chi-squared per character above which the letter distribution is clearly not English.
CHI2_ENGLISH_MAX = 0.6
#: IC below which the text is polyalphabetic or noise rather than monoalphabetic.
IC_MONO_MIN = 0.058
#: Chi-squared per character is noisy on short samples, so the "is this
#: distribution English?" threshold relaxes as the text gets shorter.
CHI2_SHORT_TEXT_RELAXATION = 25.0

#: Below this many letters the shift test is reported as inconclusive rather than
#: negative, and a shift this far above the threshold is not worth mentioning.
SHORT_SHIFT_LETTERS = 60
SHORT_SHIFT_SLACK = 2.0


def chi2_english_max(letters: int) -> float:
    """Length-aware chi-squared ceiling for "this distribution is English"."""
    return CHI2_ENGLISH_MAX + CHI2_SHORT_TEXT_RELAXATION / max(letters, 1)

_MORSE_CHARS = set(".-/ \t\n")
_TWO_SYMBOL_THRESHOLD = 2


@dataclass
class TextStats:
    """Cheap characterisation of a ciphertext."""

    length: int
    letters: int
    digits: int
    spaces: int
    punctuation: int
    other: int
    upper: int
    lower: int
    unique: int
    entropy: float
    ic: float
    chi2_per_char: float
    fitness: float
    confidence: float
    high_bytes: int
    charset: str
    letters_only_text: str = field(default="", repr=False)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def letter_ratio(self) -> float:
        return self.letters / self.length if self.length else 0.0

    @property
    def is_letter_text(self) -> bool:
        """True when the payload is essentially alphabetic.

        Whitespace is excluded from the denominator: real ciphertexts arrive with
        their spaces and commas intact, and "the quick brown fox" is letter text
        even though a quarter of its characters are layout.  Digits still count
        against it, which is what keeps base64 and hex out of the letter-only
        statistics.
        """
        payload = self.length - self.spaces
        return payload > 0 and self.letters / payload > 0.85

    def as_dict(self) -> dict:
        return {
            "length": self.length,
            "letters": self.letters,
            "digits": self.digits,
            "spaces": self.spaces,
            "punctuation": self.punctuation,
            "other": self.other,
            "upper": self.upper,
            "lower": self.lower,
            "unique_chars": self.unique,
            "entropy": round(self.entropy, 4),
            "index_of_coincidence": round(self.ic, 5),
            "chi_squared_per_char": round(self.chi2_per_char, 4),
            "quadgram_fitness": round(self.fitness, 4),
            "plaintext_confidence": round(self.confidence, 4),
            "high_bytes": self.high_bytes,
            "charset": self.charset,
            "extra": self.extra,
        }


def charset_summary(text: str) -> str:
    """Short human description of the character set in use."""
    kinds = []
    if re.search(r"[A-Z]", text):
        kinds.append("A-Z")
    if re.search(r"[a-z]", text):
        kinds.append("a-z")
    if re.search(r"[0-9]", text):
        kinds.append("0-9")
    if re.search(r"[+/=]", text):
        kinds.append("+/=")
    if re.search(r"[_\-]", text):
        kinds.append("-_")
    if re.search(r"[!-/:-@[-`{-~]", text):
        kinds.append("punct")
    if re.search(r"\s", text):
        kinds.append("space")
    if any(ord(c) > 126 for c in text):
        kinds.append("non-ascii")
    return "+".join(kinds) or "empty"


def characterise(text: str, model: LanguageModel | None = None) -> TextStats:
    """Collect every statistic the identification rules need, in one pass."""
    model = model or get_model()
    letters = letters_only(text)
    score = model.score(text) if letters else None
    distinct_chars = sorted(set(text))
    high_bytes = sum(1 for c in text if ord(c) > 126)
    extra: dict[str, Any] = {}
    if len(letters) >= 20:
        period, period_ic = best_key_length(letters, 20)
        extra["best_period"] = period
        extra["best_period_ic"] = round(period_ic, 4)
    return TextStats(
        length=len(text),
        letters=sum(c.isalpha() and c.isascii() for c in text),
        digits=sum(c.isdigit() for c in text),
        spaces=sum(c.isspace() for c in text),
        punctuation=sum(c in string.punctuation for c in text),
        other=len(text) - sum(c.isalpha() or c.isdigit() or c.isspace() or c in string.punctuation for c in text),
        upper=sum(c.isupper() for c in text),
        lower=sum(c.islower() for c in text),
        unique=len(distinct_chars),
        entropy=entropy(text.encode("utf-8", "replace")),
        ic=index_of_coincidence(letters),
        chi2_per_char=model.chi_squared(letters, per_char=True) if letters else 0.0,
        fitness=score.fitness if score else -9.0,
        confidence=score.confidence if score else 0.0,
        high_bytes=high_bytes,
        charset=charset_summary(text),
        letters_only_text=letters,
        extra=extra,
    )


def _playfair_tells(text: str) -> tuple[float, str]:
    """Playfair's structural signature.

    Every tell here is weak on its own and they are weighted by how much text
    there is to judge: "no doubled letter in a digraph position" happens by pure
    chance half the time on a 35-letter message ((25/26)^17 = 0.51), so it only
    earns its full weight once there are 25 pairs or more.
    """
    stream = letters_only(text).replace("J", "")
    if len(stream) < 30:
        return 0.0, ""
    pairs = [stream[i : i + 2] for i in range(0, len(stream) - 1, 2)]
    doubles = sum(1 for p in pairs if p[0] == p[1])
    reasons = []
    score = 0.0
    if doubles == 0:
        weight = min(1.0, len(pairs) / 25.0)
        score += 0.6 * weight
        reasons.append(
            f"no doubled letter in any digraph position ({len(pairs)} pairs"
            + ("" if weight >= 1.0 else f", {weight:.0%} of the 25 needed to trust it")
            + ")"
        )
    if len(stream) % 2 == 0:
        score += 0.1
        reasons.append("even letter count")
    if "J" not in letters_only(text):
        score += 0.05
        reasons.append("no J (folded into I)")
    ic = index_of_coincidence(stream)
    if 0.040 <= ic <= 0.058:
        score += 0.25 * min(1.0, len(stream) / 150.0)
        reasons.append(f"IC {ic:.4f} is flatter than monoalphabetic")
    return min(1.0, score), "; ".join(reasons)


def _url_evidence(stripped: str) -> tuple[float, str]:
    """Likelihood that ``stripped`` is percent-encoded text.

    A single ``%4B`` shows up by chance in dense printable encodings (ASCII85 is
    full of them), so require a couple of escapes *and* that what is left looks
    like prose: URL-encoding leaves every letter in place and only escapes the
    awkward characters.
    """
    escapes = re.findall(r"%[0-9A-Fa-f]{2}", stripped)
    if len(escapes) < 2:
        return 0.0, ""
    remainder = re.sub(r"%[0-9A-Fa-f]{2}", "", stripped)
    if not remainder:
        return 0.85, f"{len(escapes)} percent escapes"
    plain = sum(c.isalnum() or c.isspace() for c in remainder) / len(remainder)
    if plain < 0.9:
        return 0.0, ""
    return 0.9, f"{len(escapes)} percent escapes over otherwise ordinary text"


def _bacon_groups(stripped: str) -> bool:
    """True when a two-symbol stream is written in groups of five.

    Bacon's cipher is five symbols per letter.  Binary ASCII is eight symbols per
    letter and uses the same two characters, so the group width -- not the total
    length -- is what tells them apart.
    """
    groups = [g for g in re.split(r"[\s,;|/_-]+", stripped) if g]
    if len(groups) >= 4:
        return all(len(g) == 5 for g in groups)
    return len([c for c in stripped if not c.isspace()]) % 5 == 0


def identify(text: str, model: LanguageModel | None = None, limit: int = 6) -> tuple[list[Hypothesis], TextStats]:
    """Rank the ciphers that could have produced ``text``.

    Returns ``(hypotheses, stats)``.  Hypotheses are ordered by likelihood and
    each carries a human-readable reason.  The engine uses them to *order*
    attacks -- never to exclude them, because a misidentification must not cost
    the user their plaintext.
    """
    model = model or get_model()
    stats = characterise(text, model)
    out: list[Hypothesis] = []

    def add(cipher: str, likelihood: float, reason: str) -> None:
        if likelihood > 0:
            out.append(Hypothesis(cipher, round(min(1.0, likelihood), 4), reason))

    stripped = text.strip()
    compact = re.sub(r"\s+", "", stripped)

    # 0. Structural markers first: a percent escape is worth more than any amount
    # of "this reads as English", because URL-encoded text still reads as English
    # once the non-letters are dropped.
    url_likelihood, url_reason = _url_evidence(stripped)
    if url_likelihood:
        add("url", url_likelihood, url_reason)
    if stats.confidence >= 0.62:
        add("none", min(1.0, stats.confidence), "text already reads as English")
        if not any(h.cipher != "none" for h in out):
            return sorted(out, key=lambda h: -h.likelihood)[:limit], stats

    # 1. Structural detection: the character set often names the format outright.
    symbols = set(stripped)
    morse_only = bool(stripped) and symbols <= _MORSE_CHARS and (("." in symbols) or ("-" in symbols))
    if morse_only:
        add("morse", 0.95, f"input uses only Morse symbols ({stats.charset})")

    digit_groups = [g for g in re.split(r"[\s,;|/_-]+", stripped) if g]
    # A digit stream with no separators at all is still a numeric code: read it
    # as pairs, which is how decimal ASCII and Polybius are written when the
    # sender omits the spaces.
    if len(digit_groups) == 1 and compact.isdigit() and len(compact) % 2 == 0 and len(compact) >= 8:
        digit_groups = [compact[i : i + 2] for i in range(0, len(compact), 2)]
    if digit_groups and all(g.isdigit() for g in digit_groups):
        digits = "".join(digit_groups)
        values = [int(g) for g in digit_groups]
        # Polybius writes *coordinates*: every digit is 1-5 and they come in
        # pairs.  Decimal ASCII writes byte values, which need 0 and 6-9 as well,
        # and A1Z26 writes 1-26 -- so the digits themselves settle it.
        if len(digits) >= 8 and len(digits) % 2 == 0 and set(digits) <= set("12345"):
            add(
                "polybius",
                0.92,
                f"{len(digits) // 2} digit pairs, all restricted to 1-5: a 5x5 coordinate grid",
            )
        elif len(values) >= 3 and all(1 <= v <= 26 for v in values) and sum(values) / len(values) < 30:
            add("a1z26", 0.9, f"{len(values)} numbers all within 1-26 (mean {sum(values)/len(values):.1f})")
        if all(9 <= v <= 126 for v in values) and not set(digits) <= set("12345"):
            add("decimal_ascii", 0.8, "numbers all in the printable ASCII range")

    if compact and set(compact) <= set("01") and len(compact) % 8 == 0 and len(compact) >= 16:
        add("binary", 0.9, f"{len(compact)//8} groups of 8 bits")
    if (
        compact
        and len(compact) % 2 == 0
        and re.fullmatch(r"[0-9a-fA-F]+", compact)
        and re.search(r"[a-fA-F]", compact)
        and re.search(r"[0-9]", compact)  # a hex stream with no digits is not hex
    ):
        add("base16", 0.8, "even number of hexadecimal digits")
        add("xor_single", 0.55, "hex payload: could be XOR over the decoded bytes")
        add("xor_repeating", 0.5, "hex payload: could be repeating-key XOR")

    # base58 is a strict subset of the base64 alphabet, so both fire on the same
    # text.  Missing 0OIl and the +/= punctuation is what says "58".
    # Word-shaped whitespace means prose, not a blob: real base64/base58 arrives
    # as one run or MIME-wrapped at 64 or 76 columns.  "Wkh txlfn eurzq ira"
    # matches the base64 alphabet perfectly and is still a Caesar ciphertext, so
    # the layout is what tells the two apart.
    prose_shaped = is_word_shaped(stripped)
    b58_match = (
        bool(compact)
        and not prose_shaped
        and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", compact)
        and len(compact) >= 16
    )
    if b58_match and any(c.isdigit() for c in compact) and any(c.isupper() for c in compact) and any(
        c.islower() for c in compact
    ):
        add("base58", 0.7, "base58 alphabet (no 0OIl, no +/=) with mixed case and digits")
    # Base32 is a strict subset of the base64 alphabet, so both tests fire on a
    # base32 blob.  Uppercase A-Z with only the digits 2-7 is base32's signature:
    # base64 of real data nearly always carries lowercase, 0/1/8/9, + or /.
    b32_match = bool(compact) and re.fullmatch(r"[A-Z2-7]+=*", compact) and any(c in "234567" for c in compact)
    if compact and not prose_shaped and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", compact) and len(compact) >= 12:
        has_letters = any(c.isalpha() for c in compact)
        mixed = any(c.isupper() for c in compact) and any(c.islower() for c in compact)
        # Base64 output is a whole number of 4-character groups, padding included.
        # An unaligned run is either truncated or not base64, so it earns less.
        aligned = len(compact) % 4 == 0
        if has_letters and (mixed or any(c.isdigit() for c in compact) or "=" in compact):
            add(
                "base64",
                (0.4 if b32_match else (0.5 if b58_match else 0.75)) if aligned else 0.4,
                f"base64 alphabet, length {len(compact)}"
                + ("" if aligned else " (not a multiple of 4)")
                + f" ({stats.charset})",
            )
    if b32_match and not prose_shaped:
        add("base32", 0.75, "A-Z2-7 alphabet with base32 digits")
    if (
        compact
        and not morse_only
        and len(compact) >= 10
        and len(compact) % 5 != 1
        and re.fullmatch(r"[\x21-\x75]+", compact)
    ):
        punct = [c for c in compact if not c.isalnum()]
        alnum = 1.0 - len(punct) / len(compact)
        # ASCII85 is three quarters alphanumerics and a quarter punctuation; Morse
        # is all punctuation and no letters, which is how the two are told apart.
        if len(punct) / len(compact) >= 0.10 and len(set(punct)) >= 3 and alnum >= 0.5:
            add(
                "base85",
                0.8,
                f"printable 0x21-0x75 saturated with punctuation ({len(punct)} of {len(compact)} characters)",
            )
    if stats.high_bytes or stats.entropy > 7.5:
        add("xor_single", 0.7, f"non-ASCII/high-entropy bytes (entropy {stats.entropy:.2f} bits)")
        add("xor_repeating", 0.55, "high-entropy byte stream")

    # Two symbols in groups of five is Bacon.
    non_space = [c for c in stripped if not c.isspace()]
    if non_space:
        distinct = sorted(set(non_space))
        if (
            len(distinct) == _TWO_SYMBOL_THRESHOLD
            and len(non_space) >= 20
            and len(non_space) % 5 == 0
            and _bacon_groups(stripped)
        ):
            add("bacon", 0.9, f"only two symbols ({distinct[0]!r}/{distinct[1]!r}) in groups of five")

    # Mixed case in otherwise ordinary text can be a Bacon cover.
    if stats.letters > 40 and stats.upper and stats.lower:
        ratio = stats.upper / max(stats.letters, 1)
        if 0.15 < ratio < 0.85 and stats.confidence < 0.4:
            add("bacon_case", 0.35, f"mixed case ({ratio:.0%} uppercase) in unreadable text")

    # 2. Letter-text statistics: separate the classical families.  When the
    # character set has already named a format, these are scaled down -- never
    # removed, because a misidentification must not cost the user their plaintext.
    # (base64 of English looks exactly like a Vigenere ciphertext, for instance.)
    structural = max((h.likelihood for h in out if h.cipher != "none"), default=0.0)
    damping = 0.5 if structural >= 0.75 else 1.0

    def add_stat(cipher: str, likelihood: float, reason: str, damped: bool = True) -> None:
        """Record a statistical hypothesis.

        ``damped=False`` is for hypotheses that are *decryptions* rather than
        guesses: "shift 7 restores the English letter distribution" is a
        measurement of the message, and halving it because the character set also
        looked like base64 would let a surface pattern outrank an actual reading.
        Family guesses (Vigenere, columnar, Playfair) stay damped -- base64 of
        English really does look like a Vigenere ciphertext.
        """
        add(cipher, likelihood * damping if damped else likelihood, reason)

    if stats.is_letter_text and len(stats.letters_only_text) >= 20:
        stream = stats.letters_only_text
        ic, chi2, fit = stats.ic, stats.chi2_per_char, stats.fitness

        # The shift test comes first and beats every statistic below it: on a
        # short message the index of coincidence is noisy enough to send a Caesar
        # ciphertext down the polyalphabetic branch, while "does one of the 26
        # shifts restore the English distribution?" is a direct measurement.
        chi2_max = chi2_english_max(len(stream))
        # k == 0 is the identity, which "solves" any text whose distribution is
        # already English -- including every transposition -- so it is not a
        # Caesar hypothesis.
        shifts = [
            (model.chi_squared(stream.translate(str.maketrans(A26, A26[k:] + A26[:k])), per_char=True), k)
            for k in range(1, 26)
        ]
        best_shift_chi, best_shift = min(shifts)

        if best_shift_chi <= chi2_max:
            reason = (
                f"shift {best_shift} restores the English letter distribution "
                f"(chi-squared {best_shift_chi:.3f} per character)"
            )
            if best_shift == 13:
                add_stat("rot13", 0.96, reason + " -- and 13 is ROT13", damped=False)
            add_stat("caesar", 0.95, reason, damped=False)
            add_stat("affine", 0.45, "a shift-solvable distribution is also reachable by an affine map")
        else:
            # No shift reads this text.  What follows are separate questions -- was
            # the distribution preserved (a transposition), permuted (a
            # substitution) or flattened (polyalphabetic/polygraphic)? -- and on a
            # short message more than one of them can be plausible at once, so an
            # inconclusive shift test is reported *alongside* the others instead of
            # in place of them.
            if len(stream) < SHORT_SHIFT_LETTERS and best_shift_chi <= chi2_max * SHORT_SHIFT_SLACK:
                # Below ~60 letters the chi-squared distributions of "English under
                # a shift" and of a Vigenere or Atbash text overlap almost
                # completely: measured, English at n=35 reaches 1.47 at p99 while
                # Vigenere starts at 0.90.  Say so rather than staying silent.
                window = chi2_max * SHORT_SHIFT_SLACK
                closeness = max(0.0, min(1.0, (window - best_shift_chi) / window))
                add_stat(
                    "caesar",
                    round(0.2 + 0.35 * closeness, 2),
                    f"best shift {best_shift} (chi-squared {best_shift_chi:.2f} per character) is "
                    f"inconclusive at {len(stream)} letters",
                    damped=False,
                )
            if chi2 <= chi2_max:
                # The distribution is intact but no shift explains the text: letters
                # were *moved*, not replaced.  Chi-squared alone is the test here --
                # the index of coincidence says the same thing but is far noisier on
                # a short message, where English itself can measure 0.047.
                reason = (
                    f"chi-squared {chi2:.3f} per character shows the English letter distribution is "
                    f"intact (IC {ic:.4f}), but no single shift reads it -- letters were moved, not replaced"
                )
                add_stat("columnar", 0.85, reason)
                add_stat("rail_fence", 0.7, reason)
                add_stat("skip", 0.6, reason)
                add_stat("route", 0.6, reason)
            elif ic >= IC_MONO_MIN:
                add_stat("substitution", 0.9, f"IC {ic:.4f} is English-like but the distribution is permuted (chi2 {chi2:.2f})")
                add_stat("keyword_substitution", 0.8, "same evidence as simple substitution, keyword-generated alphabet")
                add_stat("atbash", 0.35, "a reciprocal alphabet map is a special case of substitution")
            else:
                pf_score, pf_reason = _playfair_tells(stream)
                if pf_score >= 0.6:
                    add_stat("playfair", pf_score * 0.9, pf_reason)
                    add_stat("bifid", pf_score * 0.5, "polygraphic ciphers flatten IC the same way")
                period = stats.extra.get("best_period", 1)
                period_ic = stats.extra.get("best_period_ic", 0.0)
                # A period is only believable when its columns hold enough letters
                # to measure; on a short text some spurious period always looks
                # English.
                if period >= 2 and period_ic >= 0.058 and len(stream) >= period * 10:
                    add_stat(
                        "vigenere",
                        0.85,
                        f"IC {ic:.4f} is flat overall but period {period} splits it into English-like "
                        f"columns (mean coset IC {period_ic:.4f})",
                    )
                    add_stat("beaufort", 0.6, f"same periodic structure as Vigenere (period {period})")
                    add_stat("variant_beaufort", 0.6, f"same periodic structure as Vigenere (period {period})")
                    add_stat("gronsfeld", 0.35, "a digit-keyed Vigenere is a special case")
                    add_stat("autokey", 0.4, "autokey also flattens IC; worth a try when Vigenere fails")
                else:
                    # Flat IC and no period the columns can support.  Fitness would
                    # be a weak gate here -- on 35 letters a Vigenere ciphertext can
                    # score better than -5.5 by luck -- so the honest report is
                    # always "polyalphabetic, polygraphic, or a short monoalphabetic
                    # text", scaled by how much of it there is to judge.
                    weight = min(1.0, len(stream) / 120.0)
                    add_stat(
                        "vigenere",
                        round(0.2 + 0.3 * weight, 2),
                        f"IC {ic:.4f} is flat and no period has enough letters per column to believe; "
                        "may need more text",
                    )
                    add_stat("trithemius", 0.25, "a progressive key also flattens IC without a repeating period")
                    add_stat(
                        "substitution",
                        round(0.2 + 0.2 * weight, 2),
                        f"IC {ic:.4f} is low for a monoalphabetic cipher, but at {len(stream)} letters IC is noisy",
                    )
                    add_stat("playfair", round(0.15 + 0.2 * weight, 2), "a polygraphic cipher flattens IC the same way")

    # 3. Fall back to each cipher's own likelihood estimate.
    if not out:
        from .ciphers import all_ciphers
        from .ciphers.base import CrackContext

        ctx = CrackContext(model=model, budget=0.0)
        for cipher in all_ciphers():
            try:
                score = cipher.likelihood(text, ctx)
            except Exception:
                continue
            if score > 0.05:
                add(cipher.info.name, score * 0.5, f"{cipher.info.title} self-assessment")

    out.sort(key=lambda h: -h.likelihood)
    return out[:limit], stats
