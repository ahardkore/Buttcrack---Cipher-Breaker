"""The English statistical language model and plaintext scoring.

Everything Buttcrack knows about "does this look like English?" lives here.
Two independent views are combined, because each fails in a different place:

``fitness``
    Letter n-gram log-probability per character (quadgrams by default).  The
    workhorse for hill-climbing substitution and transposition attacks: smooth,
    needs no spaces, cheap to evaluate.

``words``
    Dictionary coverage from a Viterbi segmentation of the *spaceless* letter
    stream, counting only words of four letters or more.  Much sharper than
    n-grams at telling real plaintext from a high-scoring near-miss.

Distributional statistics (index of coincidence, chi-squared, entropy) are used
for *identification* rather than ranking -- period detection, transposition vs.
substitution, single-shift solving.

Calibration
-----------
The confidence ramps below were measured, not guessed, by
``scripts/calibrate_scoring.py`` over the samples in
``examples/english_samples.txt``.  Medians at every length from 40 to 800
letters::

    length    english fitness   english w4   noise fitness   reversed fitness
    40            -4.22           0.71           -7.65            -5.95
    120           -4.11           0.75           -7.88            -5.86
    800           -4.08           0.77           -7.83            -5.96

Data files live in ``buttcrack/data`` and are produced by
``scripts/build_language_model.py``; see NOTICE for source attribution.
"""

from __future__ import annotations

import gzip
import json
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import repeat
from pathlib import Path

from .text import A26, index_of_coincidence, letters_only

DATA_DIR = Path(__file__).resolve().parent / "data"

#: Scoring caps.  n-gram statistics converge fast -- measured fitness for real
#: English is within 0.15 of its asymptote by 40 letters -- so reading a prefix
#: of a long text is as informative as reading all of it, and far cheaper.
MAX_SCORE_CHARS = 4000

#: Below this many letters a verdict cannot be fully trusted, so confidence is
#: damped towards ``SHORT_SAMPLE_FLOOR`` (see :meth:`LanguageModel.score`).
MIN_TRUSTED_LETTERS = 12
SHORT_SAMPLE_FLOOR = 0.55

#: Under this many letters the verdict is capped just below ``SOLVED_CONFIDENCE``:
#: a six-letter fragment can be shown as the best guess, but it cannot be
#: declared a solve, because a wrong peeling chain produces fragments like that
#: by the thousand.
FRAGMENT_LETTERS = 8
FRAGMENT_CAP = 0.61

#: Below this many letters the dictionary view outweighs the n-gram view: on a
#: short sample most quadgrams straddle word boundaries, which are artefacts of
#: concatenation rather than evidence about the language.
SHORT_REWEIGHT_LETTERS = 40
SHORT_WEIGHTS = {"fitness": 0.35, "words": 0.65}

#: Distinct letters as a share of ``min(n, 26)``. Degenerate text -- the repeated
#: fragments a wrong transposition or a nonsense peeling chain emits -- can fool
#: an n-gram model because the same few quadgrams recur, but it never uses much
#: of the alphabet. Real prose clears VARIETY_GOOD comfortably.
VARIETY_GOOD, VARIETY_BAD = 0.45, 0.18
MAX_SEARCH_CHARS = 400
MAX_SEGMENT_CHARS = 700
MAX_WORD_LEN = 24

_NGRAM_FILES = {
    2: "english_bigrams.txt.gz",
    3: "english_trigrams.txt.gz",
    4: "english_quadgrams.txt.gz",
}

# --------------------------------------------------------------------------- #
# calibration constants (see module docstring and scripts/calibrate_scoring.py)
# --------------------------------------------------------------------------- #
FITNESS_GOOD, FITNESS_BAD = -4.30, -6.20
WORDS_GOOD, WORDS_BAD = 0.62, 0.20
SEG_GOOD, SEG_BAD = -0.80, -1.35

#: How much each view contributes to ``confidence``.
WEIGHTS = {"fitness": 0.55, "words": 0.45}

#: Above this confidence the engine treats a candidate as solved plaintext.
SOLVED_CONFIDENCE = 0.62
#: Above this the engine stops searching immediately -- no point continuing.
CERTAIN_CONFIDENCE = 0.86
#: Minimum word length counted towards the ``words`` view.
WORD_COVERAGE_MIN_LEN = 4

#: Cost of a letter in a string that is not in the dictionary (log10 units).
#: The per-letter term is what makes the Viterbi pass prefer
#: ``riveratdawn`` -> ``river at dawn`` over one long invented word.
UNKNOWN_WORD_PER_CHAR = 1.55
UNKNOWN_FLOOR_MARGIN = 1.5


def ramp(value: float, good: float, bad: float) -> float:
    """Map ``value`` onto 0..1 where ``good`` -> 1.0 and ``bad`` -> 0.0."""
    if good == bad:
        return 0.0
    return max(0.0, min(1.0, (value - bad) / (good - bad)))


@dataclass(frozen=True)
class EnglishScore:
    """Multi-view assessment of how English a candidate plaintext is."""

    fitness: float
    """n-gram log10 probability per character (higher is better)."""

    words: float
    """fraction of letters inside dictionary words of 4+ letters, 0..1."""

    segmentation: float
    """Viterbi segmentation log10 probability per character."""

    ic: float
    """index of coincidence of the sample."""

    chi_squared: float
    """chi-squared distance per character from the English letter distribution."""

    confidence: float
    """0..1 combined verdict -- the number the engine ranks and thresholds on."""

    sample_size: int
    """characters actually scored."""

    words_found: tuple[str, ...] = field(default=())
    """the recovered word breaks, e.g. ``('attack', 'at', 'dawn')``."""

    start_word: str = ""
    """first recovered word -- used to break ties between equally scored candidates."""

    start_quality: float = 0.0
    """0..2: does the message begin with a common English word?

    Transposition solutions on ragged grids are only unique up to *rotation*:
    moving the final letter to the front yields text with identical letter
    statistics and almost identical quadgram fitness.  A message almost always
    begins on a common word, so this is the tie-break that picks the canonical
    reading.  It is deliberately kept out of ``confidence`` -- it is evidence
    about message framing, not about whether the text is English.
    """

    @property
    def solved(self) -> bool:
        return self.confidence >= SOLVED_CONFIDENCE

    @property
    def certain(self) -> bool:
        return self.confidence >= CERTAIN_CONFIDENCE

    def as_dict(self) -> dict:
        return {
            "fitness": round(self.fitness, 4),
            "words": round(self.words, 4),
            "segmentation": round(self.segmentation, 4),
            "ic": round(self.ic, 5),
            "chi_squared": round(self.chi_squared, 3),
            "confidence": round(self.confidence, 4),
            "sample_size": self.sample_size,
            "solved": self.solved,
            "words_found": list(self.words_found),
            "start_word": self.start_word,
            "start_quality": round(self.start_quality, 3),
        }


#: Bytes that carry the most English weight: space and the frequent letters, in
#: either case.
COMMON_BYTES = frozenset(b" etaoinshrdlcumwfgypbETAOINSHRDLCUMWFGYPB")


def _is_printable_byte(b: int) -> bool:
    return 32 <= b < 127 or b in (9, 10, 13)


#: Per-byte contribution to :meth:`LanguageModel.byte_score`, precomputed so that
#: the byte-oriented attacks can score a *coset* instead of the whole window:
#: the score is a sum of independent per-byte terms, so changing one key byte
#: only changes its own column, and a 16-byte key stays affordable.
BYTE_VALUE: tuple[int, ...] = tuple(
    (3 if b in COMMON_BYTES else 1) if _is_printable_byte(b) else -8 for b in range(256)
)
#: 1 for bytes that count towards the printable ratio, 0 otherwise.
BYTE_PRINTABLE: tuple[int, ...] = tuple(1 if _is_printable_byte(b) else 0 for b in range(256))


class LanguageModel:
    """Letter n-gram + dictionary model of English.

    Instances cost ~0.2 s to load, so use :meth:`get`, which caches one per
    (language, order) per process and is thread-safe.
    """

    def __init__(self, language: str = "english", data_dir: Path | str | None = None, order: int = 4):
        self.language = language
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.order = order
        self._tables: dict[int, dict[str, float]] = {}
        self._totals: dict[int, int] = {}
        self._floors: dict[int, float] = {}
        self.words: dict[str, int] = {}
        self._word_total = 1
        self._unknown_floor = -12.0
        self._meta: dict = {}
        self._monograms: dict[str, float] | None = None
        self._lock = threading.Lock()
        self._loaded = False

    # -- loading ------------------------------------------------------------ #
    @classmethod
    @lru_cache(maxsize=8)
    def get(cls, language: str = "english", order: int = 4) -> "LanguageModel":
        return cls(language=language, order=order).load()

    def load(self) -> "LanguageModel":
        if self._loaded:
            return self
        with self._lock:
            if self._loaded:
                return self
            for n, filename in _NGRAM_FILES.items():
                if n > self.order:
                    continue
                counts: dict[str, int] = {}
                with gzip.open(self.data_dir / filename, "rt", encoding="ascii") as fh:
                    for line in fh:
                        gram, _, count = line.partition(" ")
                        counts[gram] = int(count)
                total = sum(counts.values())
                self._totals[n] = total
                log_total = math.log10(total)
                self._tables[n] = {g: math.log10(c) - log_total for g, c in counts.items()}
                # An unseen n-gram is charged a tenth of a single occurrence:
                # harsh but finite, so hill climbing still sees a gradient.
                self._floors[n] = math.log10(0.1 / total)
            with gzip.open(self.data_dir / "english_words.json.gz", "rt", encoding="utf-8") as fh:
                self.words = json.load(fh)
            self._word_total = sum(self.words.values())
            self._unknown_floor = math.log10(1.0 / self._word_total) - UNKNOWN_FLOOR_MARGIN
            meta_path = self.data_dir / "model_meta.json"
            if meta_path.exists():
                self._meta = json.loads(meta_path.read_text())
            self._loaded = True
        return self

    @property
    def meta(self) -> dict:
        """Build provenance: corpus size, source, build time."""
        return dict(self._meta)

    @property
    def ngrams(self) -> dict[int, dict[str, float]]:
        """Loaded n-gram log-probability tables, keyed by order."""
        return self._tables

    def ngram_count(self, order: int | None = None) -> int:
        """How many n-grams of ``order`` (default: the model's order) are known."""
        return len(self._tables.get(self.order if order is None else order, {}))

    # -- n-gram scoring ----------------------------------------------------- #
    def ngram_score(
        self, text: str, order: int | None = None, *, total: bool = False, normalise: bool = True,
        max_chars: int = MAX_SCORE_CHARS,
    ) -> float:
        """Mean (or summed) log10 probability of ``text`` under the n-gram model.

        Pass ``normalise=False`` from hot loops that already hold an A-Z string.
        """
        if not self._loaded:
            self.load()
        order = order or self.order
        if order not in self._tables:
            order = max(self._tables)
        stream = letters_only(text, A26)[:max_chars] if normalise else text[:max_chars]
        n = len(stream)
        if n < order:
            return self._floors[order]
        table = self._tables[order]
        floor = self._floors[order]
        score = sum(map(table.get, (stream[i : i + order] for i in range(n - order + 1)), repeat(floor)))
        return score if total else score / (n - order + 1)

    def fitness(self, text: str, order: int | None = None, **kw) -> float:
        """Per-character n-gram fitness.  English ~ -4.1, random ~ -7.8."""
        return self.ngram_score(text, order, **kw)

    def search_fitness(self, text: str, order: int | None = None) -> float:
        """Fitness on a short prefix -- the cheap variant for search inner loops."""
        return self.ngram_score(text, order, normalise=False, max_chars=MAX_SEARCH_CHARS)

    # -- distributional statistics ----------------------------------------- #
    def monogram_reference(self) -> dict[str, float]:
        """English letter proportions, derived from the shipped bigram table."""
        if self._monograms is None:
            counts: Counter = Counter()
            with gzip.open(self.data_dir / _NGRAM_FILES[2], "rt", encoding="ascii") as fh:
                for line in fh:
                    gram, _, count = line.partition(" ")
                    counts[gram[0]] += int(count)
            total = sum(counts.values()) or 1
            self._monograms = {c: counts.get(c, 0) / total for c in A26}
        return dict(self._monograms)

    def chi_squared(self, text: str, *, per_char: bool = False) -> float:
        """Chi-squared distance from the English letter distribution.

        Near zero for English, large for random text or a wrongly-shifted
        decryption.  This is what solves Caesar/Affine/Vigenere columns without
        any search at all.
        """
        ref = self.monogram_reference()
        stream = letters_only(text, A26)[:MAX_SCORE_CHARS]
        counts = Counter(stream)
        n = len(stream)
        if n == 0:
            return 0.0
        chi = 0.0
        for letter, p in ref.items():
            expected = p * n
            if expected <= 0:
                continue
            chi += (counts.get(letter, 0) - expected) ** 2 / expected
        return chi / n if per_char else chi

    def index_of_coincidence(self, text: str) -> float:
        return index_of_coincidence(letters_only(text, A26)[:MAX_SCORE_CHARS])

    # -- dictionary / segmentation ------------------------------------------ #
    def word_logprob(self, word: str) -> float:
        """log10 P(word) for the segmentation DP."""
        count = self.words.get(word)
        if count:
            return math.log10(count / self._word_total)
        return self._unknown_floor - UNKNOWN_WORD_PER_CHAR * len(word)

    def segment(self, text: str, max_chars: int = MAX_SEGMENT_CHARS) -> tuple[float, list[str]]:
        """Viterbi segmentation of a spaceless letter stream.

        Returns ``(log10 probability, words)``.  Norvig's algorithm: the best
        split of a prefix is the best split of a shorter prefix plus the best
        final word, so the cost is O(n * MAX_WORD_LEN).
        """
        stream = letters_only(text, A26).lower()[:max_chars]
        n = len(stream)
        if n == 0:
            return 0.0, []
        best = [0.0] * (n + 1)
        back = [0] * (n + 1)
        logprob = self.word_logprob
        for i in range(1, n + 1):
            best_score, best_j = float("-inf"), 0
            for j in range(i - 1, max(0, i - MAX_WORD_LEN) - 1, -1):
                cand = best[j] + logprob(stream[j:i])
                if cand > best_score:
                    best_score, best_j = cand, j
            best[i], back[i] = best_score, best_j
        words: list[str] = []
        i = n
        while i > 0:
            j = back[i]
            words.append(stream[j:i])
            i = j
        words.reverse()
        return best[n], words

    def word_coverage(self, text: str, max_chars: int = MAX_SEGMENT_CHARS) -> tuple[float, float, list[str]]:
        """``(coverage_all, coverage_long, words)`` for a letter stream.

        ``coverage_long`` counts only words of :data:`WORD_COVERAGE_MIN_LEN` or
        more letters.  That restriction matters: *reversed* and *shuffled*
        English reach ~0.95 on ``coverage_all`` because two-letter fragments
        like "on"/"no" and "era"/"are" are real words, but they collapse to
        ~0.15-0.20 on ``coverage_long`` while genuine English stays above 0.65.
        """
        _, words = self.segment(text, max_chars)
        letters = sum(len(w) for w in words)
        if not letters:
            return 0.0, 0.0, words
        known_all = sum(len(w) for w in words if len(w) > 1 and w in self.words)
        known_long = sum(
            len(w) for w in words if len(w) >= WORD_COVERAGE_MIN_LEN and w in self.words
        )
        return known_all / letters, known_long / letters, words

    # -- composite ---------------------------------------------------------- #
    def score(self, text: str, *, with_words: bool = True) -> EnglishScore:
        """Full multi-view score of a candidate plaintext."""
        sample = letters_only(text, A26)[:MAX_SCORE_CHARS]
        if not sample:
            return EnglishScore(-9.0, 0.0, -9.0, 0.0, 999.0, 0.0, 0)
        fit = self.ngram_score(sample, normalise=False)
        chi = self.chi_squared(sample, per_char=True)
        ic = index_of_coincidence(sample)
        if with_words:
            seg_total, words = self.segment(sample)
            seg = seg_total / len(sample)
            _, coverage_long, _ = self.word_coverage(sample)
        else:
            seg, coverage_long, words = -9.0, 0.0, []
        n = len(sample)
        weights = SHORT_WEIGHTS if n < SHORT_REWEIGHT_LETTERS else WEIGHTS
        if with_words:
            confidence = weights["fitness"] * ramp(fit, FITNESS_GOOD, FITNESS_BAD) + weights[
                "words"
            ] * ramp(coverage_long, WORDS_GOOD, WORDS_BAD)
        else:
            confidence = ramp(fit, FITNESS_GOOD, FITNESS_BAD)
        # Variety: text that reuses three letters thirty times is not English,
        # however well its quadgrams happen to score.
        variety = len(set(sample)) / min(n, 26)
        if variety < VARIETY_GOOD:
            confidence *= ramp(variety, VARIETY_GOOD, VARIETY_BAD)
        # Evidence is proportional to how much text we have: five letters can
        # look English by pure accident, and every peeling chain that emits a
        # short fragment would otherwise be able to claim a confident solve and
        # outrank a real, longer answer.
        if n < MIN_TRUSTED_LETTERS:
            confidence *= SHORT_SAMPLE_FLOOR + (1.0 - SHORT_SAMPLE_FLOOR) * (
                n / MIN_TRUSTED_LETTERS
            )
            if n < FRAGMENT_LETTERS:
                confidence = min(confidence, FRAGMENT_CAP)
        return EnglishScore(
            fitness=fit,
            words=coverage_long,
            segmentation=seg,
            ic=ic,
            chi_squared=chi,
            confidence=confidence,
            sample_size=len(sample),
            words_found=tuple(words[:40]),
            start_word=words[0] if words else "",
            start_quality=self._start_quality(words[0] if words else ""),
        )

    def _start_quality(self, word: str) -> float:
        """Score for "the message starts with a common English word"."""
        if len(word) < 2 or word not in self.words:
            return 0.0
        return 1.0 + min(1.0, math.log10(self.words[word]) / 10.0)

    def plaintext_confidence(self, text: str) -> float:
        """Cheap accessor for the 0..1 verdict."""
        return self.score(text).confidence

    # -- byte level --------------------------------------------------------- #
    @staticmethod
    def byte_score(data: bytes) -> float:
        """English-likeness of raw bytes, for XOR and binary attacks.

        Rewards printable ASCII and the common letters, charges control bytes
        heavily, and penalises a low printable ratio -- the classic metric that
        makes single-byte XOR solvable by brute force over 256 keys.
        """
        if not data:
            return 0.0
        score = 0
        printable = 0
        for b in data:
            score += BYTE_VALUE[b]
            printable += BYTE_PRINTABLE[b]
        ratio = printable / len(data)
        return score / len(data) - (0.0 if ratio > 0.95 else (0.95 - ratio) * 20)


def get_model(language: str = "english", order: int = 4) -> LanguageModel:
    """Return (and cache) the language model for ``language``."""
    return LanguageModel.get(language, order)
