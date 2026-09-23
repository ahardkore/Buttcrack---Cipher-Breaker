"""Monoalphabetic substitution -- the 26! keyspace, solved by hill climbing.

A simple substitution cipher has about 4 x 10^26 keys, so it is not enumerated;
it is *climbed*.  Quadgram fitness is a good enough approximation of English
that swapping two letters of the key and keeping improvements converges on the
right answer, and random restarts escape the local optima.

Two details make the difference between a demo and something that works:

* **Restart 0 is frequency-seeded.**  Mapping the most common ciphertext letter
  to E, the next to T, and so on starts the climb close to the truth; on 400+
  letters that single climb usually wins.
* **The winner is decided by word coverage, not by fitness.**  On short texts
  several distinct keys score within noise of each other, and the one whose
  output is made of real words is nearly always right.

:meth:`explain_key` then turns a recovered mixed alphabet back into the keyword
that generated it, so the answer reads ``key=CIPHER`` instead of a 26-letter
permutation.
"""

from __future__ import annotations

import random
from typing import Any, Iterator

from ..lang import CERTAIN_CONFIDENCE, get_model
from ..results import Candidate
from ..search import frequency_seed, parallel_restarts, restart_search, restarts_for
from ..text import A26, index_of_coincidence, keyed_alphabet, letters_only
from .base import EXPENSIVE, Cipher, CipherInfo, CrackContext, Family

#: Shortest ciphertext worth a full substitution attack.
MIN_USEFUL_LENGTH = 40


def _climb_worker(payload: tuple) -> tuple:
    """Top-level so it can be pickled for the process pool.

    Runs ``restarts`` independent climbs and returns the best one.  The language
    model is inherited copy-on-write under ``fork``, so workers do not re-read
    the data files.
    """
    ciphertext, restarts, seed, max_evals, use_seed = payload
    model = get_model()
    rng = random.Random(seed)
    seeds = [frequency_seed(ciphertext)] if use_seed and restarts else []
    key, plain, fit, conf, evals, used = restart_search(
        ciphertext,
        fitness=model.search_fitness,
        confidence=lambda t: model.score(t).confidence,
        apply_key=lambda text, k: text.translate(str.maketrans(A26, "".join(k))),
        restarts=restarts,
        rng=rng,
        max_evals=max_evals,
        seeds=seeds,
    )
    return "".join(key), plain, fit, conf, evals, used


def inverse_alphabet(decrypt_key: str) -> str:
    """Invert a cipher->plain alphabet into the plain->cipher (encryption) alphabet.

    ``decrypt_key[i]`` is the plaintext letter that ciphertext letter ``A26[i]``
    decodes to; the encryption alphabet is the cipher letter for each plaintext
    letter, i.e. the same permutation read the other way round.
    """
    return "".join(A26[decrypt_key.index(c)] for c in A26)


def explain_key(mixed_alphabet: str, dictionary: dict[str, int] | None = None, min_match: int = 20) -> tuple[str, int] | None:
    """Recover the keyword behind a keyed alphabet.

    Returns ``(keyword, uncertain_positions)`` or ``None``.

    A keyed alphabet is ``keyword letters (deduped) + the rest in A-Z order``, so
    every prefix ``p`` whose removal leaves a sorted, disjoint suffix is a valid
    key -- "ZEBR" and "ZEBRA" generate the same alphabet, because A sorts first
    either way.  Real keys are words, so dictionary membership picks the winner.

    Hill climbing cannot always fix the letters that barely occur (J, Q, X, Z),
    so the recovered alphabet may be a few positions off.  When no prefix
    reproduces it exactly, the search falls back to the dictionary word whose
    keyed alphabet agrees in the most positions, and reports how many positions
    are in doubt instead of silently printing a wrong key.
    """
    alpha = letters_only(mixed_alphabet)
    if len(alpha) != 26 or sorted(alpha) != list(A26):
        return None

    valid = [
        p
        for p in range(1, 25)
        if list(alpha[p:]) == sorted(alpha[p:]) and not (set(alpha[:p]) & set(alpha[p:]))
    ]
    # Longest dictionary word first: that is what a human setter would have used.
    if dictionary:
        for p in sorted(valid, reverse=True):
            word = alpha[:p]
            if len(word) >= 2 and word.lower() in dictionary:
                return word, 0
    # Otherwise the shortest exact explanation, provided it is keyword-shaped.
    if valid and min(valid) <= 16:
        return alpha[: min(valid)], 0

    # Fuzzy: the alphabet is probably right except for a handful of rare letters.
    best: tuple[int, str] | None = None
    for p in range(min(16, len(alpha)), 1, -1):
        word = alpha[:p]
        if dictionary and word.lower() not in dictionary:
            continue
        generated = keyed_alphabet(word)
        mismatch = sum(1 for a, b in zip(generated, alpha) if a != b)
        if 26 - mismatch >= min_match and (best is None or mismatch < best[0]):
            best = (mismatch, word)
    if best:
        return best[1], best[0]
    return None


class Substitution(Cipher):
    """Simple (monoalphabetic) substitution with an arbitrary mixed alphabet."""

    info = CipherInfo(
        name="substitution",
        title="Simple substitution",
        family=Family.SUBSTITUTION,
        key_type="26-letter mixed alphabet",
        keyspace=None,
        deterministic=False,
        min_length=MIN_USEFUL_LENGTH,
        cost=EXPENSIVE,
        aliases=("simple_substitution", "monoalphabetic", "cryptogram", "aristocrat"),
        description="Every plaintext letter maps to a fixed ciphertext letter. Solved by quadgram hill climbing with restarts.",
        example_key="QWERTYUIOPASDFGHJKLZXCVBNM",
    )

    # -- transforms --------------------------------------------------------- #
    def _table(self, key: Any, decrypt: bool) -> dict[str, str]:
        if isinstance(key, dict):
            key = key.get("key") or key.get("alphabet")
        alpha = letters_only(str(key))
        if len(alpha) == 26 and sorted(alpha) == list(A26):
            mapping = dict(zip(alpha, A26)) if decrypt else dict(zip(A26, alpha))
        elif len(alpha) < 26:  # keyword shorthand
            mixed = keyed_alphabet(alpha)
            mapping = dict(zip(mixed, A26)) if decrypt else dict(zip(A26, mixed))
        else:
            raise ValueError("substitution key must be a permutation of A-Z or a keyword")
        return mapping

    def encrypt(self, plaintext: str, key: Any = "QWERTYUIOPASDFGHJKLZXCVBNM") -> str:
        return self.prepare(plaintext).translate(str.maketrans(self._table(key, decrypt=False)))

    def decrypt(self, ciphertext: str, key: Any = "QWERTYUIOPASDFGHJKLZXCVBNM") -> str:
        return self.prepare(ciphertext).translate(str.maketrans(self._table(key, decrypt=True)))

    # -- cryptanalysis ------------------------------------------------------ #
    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        n = len(stream)
        if n < 2:
            return
        hint = ctx.hints.get("key")
        if hint:
            plain = self.decrypt(stream, hint)
            yield ctx.candidate(self.name, plain, {"key": str(hint)}, steps=ctx.steps, method="hint")
            return

        total_restarts = restarts_for(n)
        workers = max(1, ctx.workers) if n >= 120 else 1
        # Give each worker a slice of the restarts; single-worker runs do it all
        # inline and avoid pool startup cost.
        if workers > 1:
            per = max(1, total_restarts // workers)
            payloads = [
                (stream, per, ctx_seed(ctx, i), max_evals_for(n), i == 0) for i in range(workers)
            ]
        else:
            payloads = [(stream, total_restarts, ctx_seed(ctx, 0), max_evals_for(n), True)]

        ctx.report(
            f"substitution: hill climbing over 26! keys "
            f"({total_restarts} restarts, {workers} worker{'s' if workers > 1 else ''}, {n} letters)"
        )
        results = parallel_restarts(_climb_worker, payloads, workers, ctx.deadline)
        results = [r for r in results if r]
        if not results:
            return
        results.sort(key=lambda r: (-r[3], -r[2]))
        seen: set[str] = set()
        emitted = 0
        for key_str, plain, fit, conf, evals, used in results:
            if key_str in seen:
                continue
            seen.add(key_str)
            explained = explain_key(inverse_alphabet(key_str), ctx.model.words)
            notes = {
                "restarts": used,
                "evaluations": evals,
                "method": "quadgram hill climbing with random restarts",
                "frequency_seeded": used > 0,
            }
            if explained:
                notes["keyword"], notes["keyword_uncertain_positions"] = explained
            cand = ctx.candidate(self.name, plain, {"key": key_str}, steps=ctx.steps, **notes)
            yield cand
            emitted += 1
            if cand.confidence >= CERTAIN_CONFIDENCE or emitted >= 5 or ctx.expired():
                break

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """Monoalphabetic ciphers keep English's letter *distribution* exactly."""
        stream = self.prepare(text)
        n = len(stream)
        if n < 30:
            return 0.0
        ic = index_of_coincidence(stream)
        ic_fit = max(0.0, min(1.0, (ic - 0.0385) / (0.0667 - 0.0385)))
        fit = ctx.model.ngram_score(stream)
        unreadable = max(0.0, min(1.0, (-4.6 - fit) / 1.5))
        # Caesar/Atbash are checked first and are far cheaper, so substitution
        # only needs to rank highly when the text is monoalphabetic-but-unreadable.
        return round(0.7 * ic_fit * unreadable + 0.3 * ic_fit, 4)


class KeywordSubstitution(Substitution):
    """Substitution whose mixed alphabet is generated from a keyword.

    Same keyspace as :class:`Substitution` in practice, but the *report* is
    different: instead of a 26-letter permutation the answer names the keyword
    ("CIPHER"), which is what a human setter actually used.
    """

    info = CipherInfo(
        name="keyword_substitution",
        title="Keyword substitution",
        family=Family.SUBSTITUTION,
        key_type="keyword",
        keyspace=None,
        deterministic=False,
        min_length=MIN_USEFUL_LENGTH,
        cost=EXPENSIVE,
        aliases=("keyed_alphabet", "mixed_alphabet"),
        description="Mixed alphabet built from a keyword, then the remaining letters in order.",
        example_key="CIPHER",
    )

    def encrypt(self, plaintext: str, key: Any = "CIPHER") -> str:
        if isinstance(key, dict):
            key = key.get("key", "")
        mixed = keyed_alphabet(str(key))
        return self.prepare(plaintext).translate(str.maketrans(A26, mixed))

    def decrypt(self, ciphertext: str, key: Any = "CIPHER") -> str:
        if isinstance(key, dict):
            key = key.get("key", "")
        mixed = keyed_alphabet(str(key))
        return self.prepare(ciphertext).translate(str.maketrans(mixed, A26))

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        for cand in super().crack(ciphertext, ctx):
            keyword = cand.notes.get("keyword")
            if keyword:
                cand.key = {"keyword": keyword}
                cand.cipher = self.name
                if cand.notes.get("keyword_uncertain_positions"):
                    cand.notes["key_note"] = (
                        f"{cand.notes['keyword_uncertain_positions']} rare-letter positions "
                        "in the alphabet could not be pinned down"
                    )
            yield cand


def ctx_seed(ctx: CrackContext, index: int) -> int:
    """Deterministic per-worker seed derived from the context."""
    base = ctx.hints.get("seed", 20260923)
    return (int(base) + index * 7919) % (2**31 - 1)


def max_evals_for(length: int) -> int:
    """Evaluation cap per climb.  Longer texts converge in fewer swaps."""
    if length >= 600:
        return 3000
    if length >= 250:
        return 5000
    return 9000
