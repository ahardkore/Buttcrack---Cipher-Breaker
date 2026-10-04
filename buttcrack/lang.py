"""Statistical language models and plaintext scoring.

Everything Buttcrack knows about "does this look like <language>?" lives here.
Two independent views are combined, because each fails in a different place:

``fitness``
    Letter n-gram log-probability per character (quadgrams by default).  The
    workhorse for hill-climbing substitution and transposition attacks: smooth,
    needs no spaces, cheap to evaluate.

``words``
    Dictionary coverage from a Viterbi segmentation of the *spaceless* letter
    stream, counting only words of four letters or more.  Much sharper than
    n-grams at telling real plaintext from a high-scoring near-miss.  Available
    for English only: the other five languages ship n-gram tables but no
    frequency dictionary, so their verdicts rest on fitness alone (with the
    per-language fitness ramps measured at import time to compensate).

Languages
---------
Six models ship in ``buttcrack/data``:

``english``
    The original: 258k quadgrams plus an 80,000-word frequency dictionary,
    distilled from a 25-million-word corpus (see NOTICE).  The only model with
    the ``words`` view, and the one whose thresholds were measured directly by
    ``scripts/calibrate_scoring.py``.

``french``, ``german``, ``italian``, ``latin``, ``spanish``
    n-gram counts from practicalcryptography.com (Wortschatz corpora), imported
    by ``scripts/import_ngram_tables.py``.  Each language carries its own
    fitness ramp, derived from its table's self-entropy using the relationship
    measured on English (``GOOD = H - 0.14``, ``BAD = GOOD - 1.90``) and
    validated against real text: native prose scores 0.8-1.0 confidence,
    prose from a sibling Romance language stays below the solve bar, random
    letters and wrong shifts score zero.

Distributional statistics (index of coincidence, chi-squared, entropy) are used
for *identification* rather than ranking -- period detection, transposition vs.
substitution, single-shift solving.  Chi-squared is measured against each
model's own letter distribution.

Calibration
-----------
The English confidence ramps below were measured, not guessed, by
``scripts/calibrate_scoring.py`` over the samples in
``examples/english_samples.txt``.  Medians at every length from 40 to 800
letters::

    length    english fitness   english w4   noise fitness   reversed fitness
    40            -4.22           0.71           -7.65            -5.95
    120           -4.11           0.75           -7.88            -5.86
    800           -4.08           0.77           -7.83            -5.96

Data files live in ``buttcrack/data`` and are produced by
``scripts/build_language_model.py`` (English) and
``scripts/import_ngram_tables.py`` (the other five); see NOTICE for source
attribution.
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
#: The languages that ship in ``data/``, in the order ``--language auto`` probes
#: them.  English leads because it is the one model with a dictionary view and
#: the calibrated baseline everything else is measured against; the rest follow
#: alphabetically so the cascade is deterministic.
LANGUAGE_ALIASES = {
    "en": "english",
    "eng": "english",
    "fr": "french",
    "fra": "french",
    "de": "german",
    "ger": "german",
    "it": "italian",
    "ita": "italian",
    "la": "latin",
    "lat": "latin",
    "es": "spanish",
    "spa": "spanish",
}


@dataclass(frozen=True)
class LanguageSpec:
    """Per-language model configuration.

    ``fitness_good`` / ``fitness_bad`` are the ramp endpoints for the
    fitness-only confidence used when a language has no dictionary.  English's
    were measured directly (``calibrate_scoring.py``); the others were derived
    from each quadgram table's self-entropy at import time (see the module
    docstring) and are recorded here so the code states its numbers.
    """

    name: str
    ngram_files: dict[int, str]
    dictionary: str | None = None
    fitness_good: float = FITNESS_GOOD
    fitness_bad: float = FITNESS_BAD


#: English first (probing order), then alphabetical.
LANGUAGES: dict[str, LanguageSpec] = {
    "english": LanguageSpec(
        name="english",
        ngram_files=_NGRAM_FILES,
        dictionary="english_words.json.gz",
        fitness_good=-4.30,
        fitness_bad=-6.20,
    ),
    "french": LanguageSpec(
        name="french",
        ngram_files={
            2: "french_bigrams.txt.gz",
            3: "french_trigrams.txt.gz",
            4: "french_quadgrams.txt.gz",
        },
        # H = -3.921 (scripts/import_ngram_tables.py)
        fitness_good=-4.06,
        fitness_bad=-5.96,
    ),
    "german": LanguageSpec(
        name="german",
        ngram_files={
            2: "german_bigrams.txt.gz",
            3: "german_trigrams.txt.gz",
            4: "german_quadgrams.txt.gz",
        },
        # H = -3.752
        fitness_good=-3.89,
        fitness_bad=-5.79,
    ),
    "italian": LanguageSpec(
        name="italian",
        ngram_files={
            2: "italian_bigrams.txt.gz",
            3: "italian_trigrams.txt.gz",
            4: "italian_quadgrams.txt.gz",
        },
        # H = -3.936
        fitness_good=-4.08,
        fitness_bad=-5.98,
    ),
    "latin": LanguageSpec(
        name="latin",
        ngram_files={
            2: "latin_bigrams.txt.gz",
            3: "latin_trigrams.txt.gz",
            4: "latin_quadgrams.txt.gz",
        },
        # H = -3.899.  Classical Latin barely uses J and W (the source table
        # carries neither), so the model scores them only through the unseen
        # floor -- correct, if harsh on mediaeval spellings.
        fitness_good=-4.04,
        fitness_bad=-5.94,
    ),
    "spanish": LanguageSpec(
        name="spanish",
        ngram_files={
            2: "spanish_bigrams.txt.gz",
            3: "spanish_trigrams.txt.gz",
            4: "spanish_quadgrams.txt.gz",
        },
        # H = -3.937
        fitness_good=-4.08,
        fitness_bad=-5.98,
    ),
}


def resolve_language(name: str) -> str:
    """Canonical language name for ``name`` (full, alias or ISO code)."""
    key = str(name).strip().lower()
    if key in ("auto", "detect"):
        return key
    if key in LANGUAGES:
        return key
    resolved = LANGUAGE_ALIASES.get(key)
    if resolved is not None:
        return resolved
    # BCP-47 style tags with a region ("de-DE", "es-419"): the model set has
    # no regional variants, so the subtag is dropped rather than rejected.
    base = key.split("-", 1)[0].split("_", 1)[0]
    resolved = LANGUAGE_ALIASES.get(base)
    if resolved is not None:
        return resolved
    known = ", ".join(LANGUAGES)
    raise ValueError(f"unknown language {name!r}; known: {known} (or 'auto')")


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
class LanguageScore:
    """Multi-view assessment of how language-like a candidate plaintext is.

    ``words``, ``segmentation`` and ``start_quality`` are empty for models
    without a dictionary (every language but English).
    """

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
    """Letter n-gram (+ dictionary, English only) model of a language.

    Instances cost ~0.2 s to load (the non-English tables are smaller and
    load faster), so use :meth:`get`, which caches one per
    (language, order) per process and is thread-safe.
    """

    def __init__(self, language: str = "english", data_dir: Path | str | None = None, order: int = 4):
        self.language = resolve_language(language)
        self.spec = LANGUAGES[self.language]
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

    @property
    def has_dictionary(self) -> bool:
        """True when this model also carries the ``words`` view (English)."""
        return self.spec.dictionary is not None

    @classmethod
    @lru_cache(maxsize=8)
    def get(cls, language: str = "english", order: int = 4) -> LanguageModel:
        return cls(language=language, order=order).load()

    def load(self) -> LanguageModel:
        if self._loaded:
            return self
        with self._lock:
            if self._loaded:
                return self
            for n, filename in self.spec.ngram_files.items():
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
            if self.spec.dictionary is not None:
                with gzip.open(self.data_dir / self.spec.dictionary, "rt", encoding="utf-8") as fh:
                    self.words = json.load(fh)
                self._word_total = sum(self.words.values())
                self._unknown_floor = math.log10(1.0 / self._word_total) - UNKNOWN_FLOOR_MARGIN
            meta_path = self.data_dir / "model_meta.json"
            if meta_path.exists():
                full = json.loads(meta_path.read_text())
                # English provenance lives at the top level of the meta file;
                # the imported languages under "languages" (see
                # scripts/import_ngram_tables.py).
                self._meta = full.get("languages", {}).get(self.language, full)
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

    def ngram_floor(self, order: int | None = None) -> float:
        """Log10 penalty charged to an n-gram absent from the table."""
        order = self.order if order is None else order
        if order not in self._floors:
            order = max(self._floors)
        return self._floors[order]

    # -- n-gram scoring ----------------------------------------------------- #
    def ngram_score(
        self,
        text: str,
        order: int | None = None,
        *,
        total: bool = False,
        normalise: bool = True,
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
        """This language's letter proportions, derived from its bigram table."""
        if self._monograms is None:
            counts: Counter = Counter()
            with gzip.open(self.data_dir / self.spec.ngram_files[2], "rt", encoding="ascii") as fh:
                for line in fh:
                    gram, _, count = line.partition(" ")
                    counts[gram[0]] += int(count)
            total = sum(counts.values()) or 1
            self._monograms = {c: counts.get(c, 0) / total for c in A26}
        return dict(self._monograms)

    def chi_squared(self, text: str, *, per_char: bool = False) -> float:
        """Chi-squared distance from this model's letter distribution.

        Near zero for text in the model's language, large for random text or a
        wrongly-shifted decryption.  This is what solves Caesar/Affine/Vigenere
        columns without any search at all.
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
        known_long = sum(len(w) for w in words if len(w) >= WORD_COVERAGE_MIN_LEN and w in self.words)
        return known_all / letters, known_long / letters, words

    # -- composite ---------------------------------------------------------- #
    def score(self, text: str, *, with_words: bool = True) -> LanguageScore:
        """Full multi-view score of a candidate plaintext.

        Models without a dictionary (all but English) score on fitness alone,
        using their own measured ramp endpoints, whatever ``with_words`` says.
        """
        sample = letters_only(text, A26)[:MAX_SCORE_CHARS]
        if not sample:
            return LanguageScore(-9.0, 0.0, -9.0, 0.0, 999.0, 0.0, 0)
        fit = self.ngram_score(sample, normalise=False)
        chi = self.chi_squared(sample, per_char=True)
        ic = index_of_coincidence(sample)
        with_words = with_words and self.has_dictionary
        if with_words:
            seg_total, words = self.segment(sample)
            seg = seg_total / len(sample)
            _, coverage_long, _ = self.word_coverage(sample)
        else:
            seg, coverage_long, words = -9.0, 0.0, []
        n = len(sample)
        weights = SHORT_WEIGHTS if n < SHORT_REWEIGHT_LETTERS else WEIGHTS
        if with_words:
            confidence = weights["fitness"] * ramp(fit, FITNESS_GOOD, FITNESS_BAD) + weights["words"] * ramp(
                coverage_long, WORDS_GOOD, WORDS_BAD
            )
        else:
            # No dictionary view: the fitness ramp has to carry the verdict on
            # its own, against this language's own endpoints.  Measured on real
            # text: native prose 0.8-1.0, sibling languages below the solve
            # bar, random letters and wrong shifts zero.
            confidence = ramp(fit, self.spec.fitness_good, self.spec.fitness_bad)
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
            confidence *= SHORT_SAMPLE_FLOOR + (1.0 - SHORT_SAMPLE_FLOOR) * (n / MIN_TRUSTED_LETTERS)
            if n < FRAGMENT_LETTERS:
                confidence = min(confidence, FRAGMENT_CAP)
        return LanguageScore(
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


#: Backwards-compatible alias: the score class was English-only until the
#: 1.1 multi-language models, and downstream code imports the old name.
EnglishScore = LanguageScore


def get_model(language: str = "english", order: int = 4) -> LanguageModel:
    """Return (and cache) the language model for ``language`` (or its alias)."""
    return LanguageModel.get(resolve_language(language), order)


def detect_language(text: str, *, limit: int | None = None) -> list[tuple[str, float]]:
    """Rank the shipped models by how well ``text`` reads under each.

    Returns ``[(language, confidence), ...]``, best first.  This is plaintext
    language identification, not cipher identification: it answers "which
    model should judge this text", which is what ``--language auto`` and the
    "this reads better as French" note in the report need.

    Every model scores under its own fitness ramp *without* the dictionary
    view, even English's.  That is deliberate: the dictionary inflates English
    confidence on French or Italian prose (the languages share enough
    vocabulary to cover half of each other's words), and a ranking that
    compares fitness views only is the one that actually picks the right
    model -- measured on real prose in all six languages, the diagonal wins
    every time, by 0.07 (French, the closest) to 0.5.
    """
    ranked = [(name, get_model(name).score(text, with_words=False).confidence) for name in LANGUAGES]
    ranked.sort(key=lambda pair: -pair[1])
    return ranked[:limit] if limit else ranked
