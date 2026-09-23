"""Cipher plugin framework: metadata, contract and shared cryptanalysis helpers.

Every cipher in :mod:`buttcrack.ciphers` implements the same three jobs:

``encrypt`` / ``decrypt``
    the cipher itself, so the tool can generate its own test material and act as
    a normal cipher playground;

``crack``
    a generator of :class:`~buttcrack.results.Candidate` plaintexts, best first,
    honouring the deadline in the context;

``likelihood``
    a 0..1 guess at "was *this* cipher used?", built from cheap statistics.  The
    engine uses these to order attacks, which is why a 40-letter Vigenere text is
    not wasted on a Playfair hill climb.

Adding a cipher means writing one class and registering it -- nothing else in the
codebase changes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Iterable, Iterator

from ..lang import LanguageModel
from ..results import EVIDENCE_CAP, Candidate, evidence_shortfall
from ..text import A26, letters_only


class Family(str, Enum):
    """Cryptographic families, used for scheduling and display."""

    SHIFT = "shift"
    POLYALPHABETIC = "polyalphabetic"
    SUBSTITUTION = "substitution"
    TRANSPOSITION = "transposition"
    POLYGRAPHIC = "polygraphic"
    CODE = "code"
    ENCODING = "encoding"
    XOR = "xor"


#: Attack cost classes.  The engine runs CHEAP before EXPENSIVE so that a Caesar
#: answer arrives in milliseconds instead of after a minute of hill climbing.
CHEAP, MODERATE, EXPENSIVE, BRUTAL = 1.0, 3.0, 10.0, 30.0


@dataclass(frozen=True)
class CipherInfo:
    """Static description of a cipher."""

    name: str
    title: str
    family: Family
    keyed: bool = True
    key_type: str = "word"
    keyspace: int | None = None
    """Number of possible keys, or ``None`` when effectively unbounded."""
    deterministic: bool = True
    """True when ``crack`` provably covers the keyspace (no randomness)."""
    min_length: int = 16
    cost: float = CHEAP
    aliases: tuple[str, ...] = ()

    description: str = ""
    example_key: Any = None
    layer: bool = False
    """True if the engine may peel this as an outer encoding layer."""
    alphabet: str = A26

    def __post_init__(self) -> None:
        # A bare string alias is an easy typo (``aliases=("hex")``) that would
        # otherwise register every character of the word as its own alias.
        if isinstance(self.aliases, str):
            object.__setattr__(self, "aliases", (self.aliases,))
        else:
            object.__setattr__(self, "aliases", tuple(str(a) for a in self.aliases))

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "family": self.family.value,
            "keyed": self.keyed,
            "key_type": self.key_type,
            "keyspace": self.keyspace,
            "deterministic": self.deterministic,
            "min_length": self.min_length,
            "cost": self.cost,
            "aliases": list(self.aliases),
            "description": self.description,
            "example_key": self.example_key,
            "layer": self.layer,
            "alphabet": self.alphabet,
        }


@dataclass
class CrackContext:
    """Everything an attack is allowed to know and spend.

    The context carries the shared language model, the deadline, and a progress
    callback.  Attacks must check :meth:`expired` inside their loops: the engine
    runs many of them concurrently and cannot interrupt a thread mid-loop.
    """

    model: LanguageModel
    budget: float = 30.0
    deadline: float = field(default_factory=lambda: time.time() + 30.0)
    workers: int = 1
    hints: dict[str, Any] = field(default_factory=dict)
    """Optional guidance: ``{"key_length": 7}``, ``{"crib": "THE"}``, ..."""
    steps: tuple[str, ...] = ()
    """Decoding chain already applied to reach this text (outermost first)."""
    progress: Callable[[str, float, dict], None] | None = None
    depth: int = 0
    max_depth: int = 4
    exhaustive: bool = False
    """When True, attacks enumerate whole keyspaces even if usually pruned."""

    @classmethod
    def create(
        cls,
        model: LanguageModel | None = None,
        budget: float = 30.0,
        workers: int = 1,
        hints: dict | None = None,
        progress: Callable[[str, float, dict], None] | None = None,
        **kw,
    ) -> "CrackContext":
        from ..lang import get_model

        return cls(
            model=model or get_model(),
            budget=budget,
            deadline=time.time() + budget,
            workers=workers,
            hints=hints or {},
            progress=progress,
            **kw,
        )

    # -- time --------------------------------------------------------------- #
    def expired(self) -> bool:
        return time.time() >= self.deadline

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.time())

    def fraction_left(self) -> float:
        return max(0.0, min(1.0, self.remaining() / self.budget)) if self.budget else 0.0

    def child(self, budget: float, *, steps: tuple[str, ...] = (), depth: int | None = None) -> "CrackContext":
        """A sub-context with its own slice of the remaining budget."""
        return CrackContext(
            model=self.model,
            budget=min(budget, self.remaining()),
            deadline=min(time.time() + budget, self.deadline),
            workers=self.workers,
            hints=dict(self.hints),
            steps=self.steps + steps,
            progress=self.progress,
            depth=self.depth if depth is None else depth,
            max_depth=self.max_depth,
            exhaustive=self.exhaustive,
        )

    def with_steps(
        self,
        steps: tuple[str, ...],
        *,
        budget: float | None = None,
        depth: int | None = None,
    ) -> "CrackContext":
        """A copy of this context carrying an *absolute* decode chain.

        :meth:`child` appends to the chain, which is right when the text being
        explored came from this node.  ``with_steps`` sets the chain outright,
        for the case where the text came from a candidate that was produced on a
        different branch of the search -- its chain is not a continuation of ours.
        """
        return replace(
            self,
            steps=tuple(steps),
            budget=self.budget if budget is None else min(budget, self.remaining()),
            deadline=self.deadline if budget is None else min(time.time() + budget, self.deadline),
            depth=self.depth if depth is None else depth,
            hints=dict(self.hints),
        )

    # -- reporting ---------------------------------------------------------- #
    def report(self, message: str, pct: float = -1.0, **extra: Any) -> None:
        if self.progress is not None:
            self.progress(message, pct, extra)

    # -- scoring ------------------------------------------------------------ #
    def score(self, text: str, *, with_words: bool = True):
        return self.model.score(text, with_words=with_words)

    def candidate(
        self,
        cipher: str,
        plaintext: str,
        key: Any,
        *,
        with_words: bool = True,
        steps: tuple[str, ...] | None = None,
        columns: int | None = None,
        **notes: Any,
    ) -> Candidate:
        """Score a decryption and wrap it in a :class:`Candidate`.

        Confidence is capped when the plaintext is too short to have pinned down
        a key of that size: an 88-bit mixed alphabet cannot be recovered from 40
        letters, so a candidate that claims otherwise is overfitting, not solving.
        ``columns`` is the period of a periodic cipher, which adds the sharper
        letters-per-column rule (see :func:`evidence_shortfall`).
        """
        s = self.model.score(plaintext, with_words=with_words)
        confidence = s.confidence
        bits, letters = evidence_shortfall(plaintext, key, columns=columns)
        if bits and confidence > EVIDENCE_CAP:
            confidence = EVIDENCE_CAP
            notes.setdefault(
                "evidence",
                f"{letters} letters is not enough to pin down a {bits:.0f}-bit key; "
                "plausible but unproven",
            )
        return Candidate(
            plaintext=plaintext,
            cipher=cipher,
            key=key,
            confidence=confidence,
            fitness=s.fitness,
            score=s,
            steps=tuple(steps if steps is not None else self.steps),
            notes=notes,
        )


class Cipher:
    """Base class for every cipher plugin."""

    info: CipherInfo

    def __init__(self) -> None:
        if not hasattr(self, "info"):
            raise TypeError(f"{type(self).__name__} must define `info`")

    # -- identity ----------------------------------------------------------- #
    @property
    def name(self) -> str:
        return self.info.name

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} {self.info.name}>"

    # -- normalisation ------------------------------------------------------ #
    def prepare(self, text: str) -> str:
        """The representation this cipher operates on.  Default: A-Z only."""
        return letters_only(text, self.info.alphabet)

    # -- the cipher --------------------------------------------------------- #
    def encrypt(self, plaintext: str, key: Any = None) -> str:
        raise NotImplementedError(f"{self.name} does not implement encrypt")

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        raise NotImplementedError(f"{self.name} does not implement decrypt")

    def keys(self) -> Iterator[Any]:
        """Enumerate the keyspace, when it is enumerable."""
        raise NotImplementedError(f"{self.name} has no enumerable keyspace")

    # -- cryptanalysis ------------------------------------------------------ #
    #: How many brute-forced keys get the expensive multi-view score.  The rest
    #: are ranked by :meth:`prescreen` only -- scoring 300 keys with a Viterbi
    #: segmentation each is 20x slower and cannot change the winner.
    top_candidates = 12

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        """Cheap ranking metric for a brute-force sweep.  Lower is better.

        Chi-squared per character against the English letter distribution: it
        needs one pass over a histogram, no n-grams and no segmentation, and it
        is monotonic with "is this English" for the shift-family ciphers.
        """
        return ctx.model.chi_squared(plaintext, per_char=True)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        """Yield candidate plaintexts, best first.

        The default implementation brute-forces :meth:`keys`, which is correct
        and complete for every cipher with a small deterministic keyspace
        (Caesar, Affine, ROT47, rail fence, ...).  Search-based ciphers override
        it.
        """
        prepared = self.prepare(ciphertext)
        if len(prepared) < self.info.min_length and not ctx.exhaustive:
            return
        swept: list[tuple[float, Any, str]] = []
        for i, key in enumerate(self.keys()):
            if i % 16 == 0 and ctx.expired():
                return
            try:
                plain = self.decrypt(prepared, key)
            except Exception:
                continue
            swept.append((self.prescreen(plain, ctx), key, plain))
        swept.sort(key=lambda t: t[0])
        for _, key, plain in swept[: self.top_candidates]:
            yield self.candidate(prepared, plain, key, ctx, method="exhaustive keyspace")

    def candidate(self, prepared: str, plaintext: str, key: Any, ctx: CrackContext, **notes) -> Candidate:
        return ctx.candidate(self.info.name, plaintext, key, steps=ctx.steps, **notes)

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """0..1 estimate that ``text`` was produced by this cipher.

        Used only to *order* attacks -- never to exclude them, because a wrong
        guess must not cost the user their plaintext.
        """
        return 0.0


class LayerCipher(Cipher):
    """A reversible encoding the layer peeler can strip (base64, hex, ROT13...).

    Layers must be *detectable*: :meth:`decodable` says whether stripping is
    plausible, so the peeler does not try to base64-decode prose.
    """

    def decodable(self, text: str) -> bool:
        raise NotImplementedError

    def decode(self, text: str) -> str | bytes | None:
        raise NotImplementedError

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        if not self.decodable(ciphertext):
            return
        try:
            out = self.decode(ciphertext)
        except Exception:
            return
        if out is None:
            return
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        yield ctx.candidate(self.info.name, out, None, steps=ctx.steps)


def helper_frequencies(text: str) -> dict[str, float]:
    from ..text import relative_frequencies

    return relative_frequencies(text, A26)


def iterable(x: Any) -> Iterable:
    return x if isinstance(x, (list, tuple)) else (x,)
