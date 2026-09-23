"""Result types shared by the engine, the CLI and the web API."""

from __future__ import annotations

import math
import string
import time
from dataclasses import dataclass, field
from typing import Any

from .lang import CERTAIN_CONFIDENCE, SOLVED_CONFIDENCE, EnglishScore


@dataclass
class Candidate:
    """One proposed plaintext, with the key and reasoning that produced it."""

    plaintext: str
    cipher: str
    key: Any = None
    confidence: float = 0.0
    fitness: float = -9.0
    score: EnglishScore | None = None
    steps: tuple[str, ...] = ()
    """Decoding chain from the original ciphertext, outermost first."""
    notes: dict[str, Any] = field(default_factory=dict)
    """Attack-specific evidence: key length, IC, restarts, cribs used, ..."""

    @property
    def key_repr(self) -> str:
        """Human-readable key, e.g. ``shift=7``, ``key=LEMON``, ``a=5,b=8``."""
        if self.key is None:
            return "-"
        if isinstance(self.key, dict):
            return ",".join(f"{k}={_fmt(v)}" for k, v in sorted(self.key.items()))
        if isinstance(self.key, (list, tuple)):
            return ",".join(_fmt(v) for v in self.key)
        return _fmt(self.key)

    @property
    def solved(self) -> bool:
        return self.confidence >= SOLVED_CONFIDENCE

    @property
    def certain(self) -> bool:
        return self.confidence >= CERTAIN_CONFIDENCE

    @property
    def path(self) -> str:
        """The decode chain, outermost layer first: ``base64 -> caesar``."""
        chain = list(self.steps) + ([] if self.cipher == "none" else [self.cipher])
        return " -> ".join(chain) if chain else "none"

    #: Equivalent readings, canonical name first.  Variant Beaufort with key K
    #: decrypts exactly what Vigenere decrypts with key -K (and Gronsfeld is
    #: Vigenere restricted to digits), so a solved message can be reported under
    #: any of those names with the same confidence and the same plaintext.  The
    #: name people recognise wins the tie; nothing but ties is affected, because
    #: this is the last element of :meth:`sort_key`.
    EQUIVALENT_CIPHER_RANK = {
        "vigenere": 0,
        "beaufort": 1,
        "variant_beaufort": 2,
        "gronsfeld": 3,
    }

    def sort_key(self) -> tuple:
        """Rank candidates for presentation.

        Confidence first, then fitness -- but both rounded, because differences
        below ~0.1 are noise from the language model rather than evidence.  Ties
        are then broken by how well the message *starts* (see
        ``EnglishScore.start_quality``), which is what separates a correct
        transposition reading from a rotation of it, and finally by explanation
        simplicity: fewer decoding steps and a shorter key are preferred.
        """
        start = self.score.start_quality if self.score else 0.0
        return (
            -round(self.confidence, 3),
            -round(self.fitness, 1),
            -start,
            len(self.steps),
            len(str(self.key_repr)),
            self.EQUIVALENT_CIPHER_RANK.get(self.cipher, 1),
        )

    def as_dict(self, *, plaintext_limit: int | None = None) -> dict:
        pt = self.plaintext if plaintext_limit is None else self.plaintext[:plaintext_limit]
        return {
            "plaintext": pt,
            "cipher": self.cipher,
            "key": self.key_repr,
            "confidence": round(self.confidence, 4),
            "fitness": round(self.fitness, 4),
            "steps": list(self.steps),
            "notes": self.notes,
            "score": self.score.as_dict() if self.score else None,
        }


#: Bits of secret held by one key character.
_LETTER_BITS = math.log2(26)
#: ``log2(26!)`` -- the entropy of a full mixed alphabet, the ceiling for any key.
_ALPHABET_BITS = math.lgamma(27) / math.log(2)

#: A solve needs more evidence than the key holds. Below this fraction of the
#: key's entropy in plaintext letters, a candidate is capped under the solve
#: threshold: with 40 letters there are simply too many 26-letter keys that
#: produce plausible-looking English, and saying "solved" would be a lie.
EVIDENCE_RATIO = 0.6
EVIDENCE_CAP = 0.61


def key_entropy_bits(key: Any) -> float:
    """Estimate how many bits of secret ``key`` holds.

    Deliberately rough: it only has to separate "a shift" (5 bits) from "a mixed
    alphabet" (88 bits), because that is what decides how much ciphertext is
    needed before an answer can be believed.
    """
    if key is None or isinstance(key, bool):
        return 0.0
    if isinstance(key, (int, float)):
        return _LETTER_BITS
    if isinstance(key, bytes):
        return float(len(key) * 8)
    if isinstance(key, str):
        text = key.strip()
        if not text:
            return 0.0
        if len(set(text)) == len(text) and len(text) >= 20 and set(text) <= set(string.ascii_uppercase):
            return math.lgamma(len(text) + 1) / math.log(2)
        # A repeated or over-long keyword does not hold more secret than the
        # distinct material it is built from.
        return min(_ALPHABET_BITS, min(len(text), 26) * _LETTER_BITS)
    if isinstance(key, dict):
        return min(_ALPHABET_BITS, sum(key_entropy_bits(v) for v in key.values()))
    if isinstance(key, (list, tuple)):
        return min(_ALPHABET_BITS, sum(key_entropy_bits(v) for v in key))
    return _LETTER_BITS


#: Letters a *column* needs before its key symbol counts as recovered.  Periodic
#: ciphers are solved one Caesar column at a time, so the evidence per key symbol
#: is ``letters / period``: a 7-letter key fitted to 30 letters sees four letters
#: a column, and any English-looking output there is the search finding itself.
MIN_LETTERS_PER_COLUMN_TRUST = 6


def evidence_shortfall(plaintext: str, key: Any, columns: int | None = None) -> tuple[float, int]:
    """Return ``(key_bits, letters)`` when the text is too short to trust the key.

    ``(0.0, n)`` means the evidence is sufficient.  ``columns`` is the number of
    independently solved key symbols for a periodic cipher; when it is given, the
    letters-per-column rule applies on top of the entropy rule.
    """
    from .text import letters_only

    letters = len(letters_only(plaintext))
    bits = key_entropy_bits(key)
    if columns and columns > 0 and letters < MIN_LETTERS_PER_COLUMN_TRUST * columns:
        return max(bits, columns * _LETTER_BITS), letters
    if bits and letters < EVIDENCE_RATIO * bits:
        return bits, letters
    return 0.0, letters


def _fmt(value: Any) -> str:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


@dataclass
class AttackLog:
    """What one attack did -- surfaced in the CLI and the web UI's live log."""

    cipher: str
    started: float
    finished: float = 0.0
    status: str = "running"  # running | solved | exhausted | skipped | budget
    tried: int = 0
    best_confidence: float = 0.0
    detail: str = ""

    @property
    def elapsed(self) -> float:
        return (self.finished or time.time()) - self.started

    def as_dict(self) -> dict:
        return {
            "cipher": self.cipher,
            "elapsed": round(self.elapsed, 3),
            "status": self.status,
            "tried": self.tried,
            "best_confidence": round(self.best_confidence, 4),
            "detail": self.detail,
        }


@dataclass
class Hypothesis:
    """An identification guess about the cipher in front of us."""

    cipher: str
    likelihood: float
    reason: str

    def as_dict(self) -> dict:
        return {"cipher": self.cipher, "likelihood": round(self.likelihood, 4), "reason": self.reason}


@dataclass
class CrackReport:
    """The complete answer: verdict, best plaintext, evidence and audit trail."""

    ciphertext: str
    solved: bool = False
    best: Candidate | None = None
    candidates: list[Candidate] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    attacks: list[AttackLog] = field(default_factory=list)
    elapsed: float = 0.0
    budget: float = 0.0
    workers: int = 1
    stats: dict[str, Any] = field(default_factory=dict)
    """Characterisation of the input: length, IC, entropy, alphabet, ..."""

    @property
    def plaintext(self) -> str:
        return self.best.plaintext if self.best else ""

    @property
    def confidence(self) -> float:
        return self.best.confidence if self.best else 0.0

    @property
    def cipher(self) -> str:
        return self.best.cipher if self.best else ""

    @property
    def key(self) -> Any:
        return self.best.key if self.best else None

    @property
    def key_repr(self) -> str:
        return self.best.key_repr if self.best else "-"

    @property
    def steps(self) -> tuple[str, ...]:
        return self.best.steps if self.best else ()

    @property
    def path(self) -> str:
        """Decode chain of the winning candidate, outermost layer first."""
        return self.best.path if self.best else "none"

    @property
    def notes(self) -> dict[str, Any]:
        return dict(self.best.notes) if self.best else {}

    @property
    def formatted(self) -> str:
        """Plaintext with the ciphertext's original spacing and case restored."""
        notes = self.notes
        return str(notes.get("formatted") or self.plaintext)

    @property
    def evidence(self) -> dict[str, Any]:
        """The measurements behind the winning confidence, as plain numbers.

        This is what a human reads to decide whether to believe the answer: how
        English the plaintext scores, how much of it is dictionary words, how far
        its letter distribution is from English, and how much text there was to
        judge.  Empty when the search produced nothing.
        """
        best = self.best
        if best is None:
            return {}
        out: dict[str, Any] = {
            "cipher": best.cipher,
            "key": best.key_repr,
            "confidence": round(best.confidence, 4),
            "fitness": round(best.fitness, 4),
            "method": best.notes.get("method", ""),
        }
        score = best.score
        if score is not None:
            out.update(
                {
                    "words": round(score.words, 4),
                    "ic": round(score.ic, 5),
                    "chi_squared": round(score.chi_squared, 4),
                    "segmentation": round(score.segmentation, 4),
                    "sample_size": score.sample_size,
                    "words_found": list(score.words_found),
                }
            )
        for key in ("key_length", "period", "decode_chain", "caveat", "letters", "columns"):
            if key in best.notes:
                out[key] = best.notes[key]
        return out

    @property
    def respaced(self) -> str:
        """Plaintext with word boundaries recovered by dictionary segmentation."""
        return str(self.notes.get("respaced") or self.plaintext)

    def as_dict(self, *, plaintext_limit: int | None = None, max_candidates: int = 12) -> dict:
        return {
            "solved": self.solved,
            "confidence": round(self.confidence, 4),
            "best": self.best.as_dict(plaintext_limit=plaintext_limit) if self.best else None,
            "candidates": [
                c.as_dict(plaintext_limit=plaintext_limit) for c in self.candidates[:max_candidates]
            ],
            "hypotheses": [h.as_dict() for h in self.hypotheses],
            "attacks": [a.as_dict() for a in self.attacks],
            "elapsed": round(self.elapsed, 3),
            "budget": self.budget,
            "workers": self.workers,
            "stats": self.stats,
        }
