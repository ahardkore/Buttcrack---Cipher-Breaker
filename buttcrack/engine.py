"""The solver: recursive layer peeling plus staged cryptanalysis.

This is the "auto-crack" part.  A real puzzle is rarely one cipher; it is a
stack, e.g. ``base64(vigenere(columnar(plaintext)))``.  The solver therefore
treats the input as a node in a decoding graph and explores it:

1. **Characterise and identify.**  :mod:`buttcrack.detect` produces ranked
   hypotheses with reasons; these order the attacks but never exclude any.
2. **Attack this node.**  Ciphers run in cost phases -- cheap (Caesar, Atbash,
   rail fence, Morse...) before moderate (Vigenere, XOR...) before expensive
   (substitution, columnar, Playfair hill climbs).  Any phase that produces
   plaintext the language model is *certain* about ends the search immediately,
   so easy inputs answer in milliseconds.
3. **Peel layers.**  Every encoding layer that plausibly applies (base64, hex,
   Morse, Bacon, A1Z26, ...) is stripped and the inner text becomes a new node,
   recursing to ``max_depth``.
4. **Peel after attacking.**  A candidate whose *plaintext* is itself base64 or
   hex gets peeled too, which covers stacks in the other order
   (``vigenere(base64(flag))``).

Visited nodes are fingerprinted so a stack of reversible layers
(reverse -> reverse -> ...) cannot loop, and every stage checks the deadline.
"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Callable, Iterable

from .ciphers import attack_ciphers, layer_ciphers
from .ciphers.base import BRUTAL, CHEAP, EXPENSIVE, MODERATE, Cipher, CrackContext, Family
from .detect import characterise, identify
from .lang import CERTAIN_CONFIDENCE, SOLVED_CONFIDENCE, LanguageModel, get_model
from .results import AttackLog, Candidate, CrackReport, Hypothesis
from .text import letters_only, respaced, restore_shape, trim

#: Families whose ciphers preserve character positions, so the original spacing
#: and case can be laid back over the solution.
#: Set ``BUTTCRACK_STRICT=1`` to let a failing attack raise instead of being
#: recorded in the attack log and skipped.
STRICT_ATTACKS = bool(os.environ.get("BUTTCRACK_STRICT"))

POSITION_PRESERVING = {Family.SHIFT, Family.SUBSTITUTION, Family.POLYALPHABETIC, Family.POLYGRAPHIC}

#: Members of those families that do *not* keep a letter in its own position:
#: ROT47 works over printable ASCII, so a letter can come out as a symbol and a
#: symbol as a letter, and Reverse changes the order outright.  Laying the
#: ciphertext's shape over the plaintext for either of them produces noise.
LAYOUT_HOSTILE = frozenset({"rot47", "reverse"})

#: Per-attack time slices by cost class.  Cheap attacks are so fast that a hard
#: cap costs nothing; expensive ones divide what is left.
PHASE_SLICES = {CHEAP: 3.0, MODERATE: 6.0, EXPENSIVE: 25.0, BRUTAL: 12.0}


def fingerprint(text: str) -> str:
    """Stable identity for a decoding-graph node."""
    return hashlib.sha1(text.encode("utf-8", "surrogateescape")).hexdigest()[:16]


class CandidatePool:
    """Deduplicated, ranked collection of every candidate found so far."""

    def __init__(self, model: LanguageModel, keep: int = 60):
        self.model = model
        self.keep = keep
        self._by_text: dict[str, Candidate] = {}
        self._order: list[str] = []

    @staticmethod
    def _key(candidate: Candidate) -> str:
        normalised = letters_only(candidate.plaintext)[:160]
        return normalised or candidate.plaintext[:160]

    def add(self, candidate: Candidate) -> bool:
        """Add a candidate; returns True when it is the new best."""
        if not candidate.plaintext:
            return False
        key = self._key(candidate)
        existing = self._by_text.get(key)
        if existing is not None:
            if candidate.sort_key() < existing.sort_key():
                self._by_text[key] = candidate
                return True
            return False
        self._by_text[key] = candidate
        self._order.append(key)
        return True

    @property
    def best(self) -> Candidate | None:
        items = list(self._by_text.values())
        return min(items, key=Candidate.sort_key) if items else None

    @property
    def best_confidence(self) -> float:
        best = self.best
        return best.confidence if best else 0.0

    @property
    def solved(self) -> bool:
        return self.best_confidence >= SOLVED_CONFIDENCE

    @property
    def certain(self) -> bool:
        return self.best_confidence >= CERTAIN_CONFIDENCE

    def ranked(self, limit: int | None = None) -> list[Candidate]:
        items = sorted(self._by_text.values(), key=Candidate.sort_key)
        return items[: limit or self.keep]


#: Minimum identification likelihood for a layer to be treated as "this text is
#: that encoding" rather than "this text might be that encoding".
STRONG_LAYER = 0.6


class Solver:
    """Automatic cipher breaker.

    >>> solver = Solver(budget=10)
    >>> report = solver.solve("Lbh penpxrq gur pbqr!")
    >>> report.solved
    True
    """

    def __init__(
        self,
        budget: float = 30.0,
        workers: int = 1,
        max_depth: int = 3,
        model: LanguageModel | None = None,
        progress: Callable[[str, float, dict], None] | None = None,
        ciphers: Iterable[Cipher] | None = None,
        hints: dict[str, Any] | None = None,
        exhaustive: bool = False,
    ):
        self.budget = float(budget)
        self.workers = max(1, int(workers))
        self.max_depth = max_depth
        self.model = model or get_model()
        self.progress = progress
        self.ciphers = list(ciphers) if ciphers is not None else attack_ciphers()
        self.hints = hints or {}
        self.exhaustive = exhaustive
        self._visited: set[str] = set()
        self._pending: list[tuple[str, tuple[str, ...], int]] = []
        #: Set while the root node is a confidently identified encoding: the
        #: "no cipher" reading is deferred so the layer gets the credit.
        self._defer_identity = False

    # -- reporting ---------------------------------------------------------- #
    def _say(self, message: str, pct: float = -1.0, **extra: Any) -> None:
        if self.progress:
            self.progress(message, pct, extra)

    # -- main entry --------------------------------------------------------- #
    def solve(self, ciphertext: str) -> CrackReport:
        started = time.time()
        text = trim(ciphertext)
        report = CrackReport(ciphertext=ciphertext, budget=self.budget, workers=self.workers)
        if not text:
            report.elapsed = time.time() - started
            return report

        hypotheses, stats = identify(text, self.model)
        report.hypotheses = hypotheses
        report.stats = stats.as_dict()
        self._say(
            f"characterised {stats.length} characters: IC {stats.ic:.4f}, "
            f"entropy {stats.entropy:.2f}, fitness {stats.fitness:.2f}",
            0.02,
        )
        for h in hypotheses[:3]:
            self._say(f"hypothesis: {h.cipher} ({h.likelihood:.0%}) -- {h.reason}", 0.04)

        ctx = CrackContext.create(
            model=self.model,
            budget=self.budget,
            workers=self.workers,
            hints=dict(self.hints),
            progress=self.progress,
            max_depth=self.max_depth,
            exhaustive=self.exhaustive,
        )
        pool = CandidatePool(self.model)

        # ...but "reads as English" is not the same as "is the plaintext":
        # percent-encoding leaves every letter in place, so the raw text scores
        # as well as its decoding does.  When the identifier is confident about
        # a structural layer, that layer gets to claim the answer, and the
        # plain-text reading is held back as a fallback.
        layer_names = {layer.info.name for layer in layer_ciphers()}
        indicated = [
            h.cipher
            for h in hypotheses
            if h.cipher in layer_names and h.likelihood >= STRONG_LAYER
        ]
        identity = ctx.candidate("none", text, None, steps=())
        if not indicated:
            pool.add(identity)
            if pool.certain:
                self._say("input already reads as English; nothing to crack", 1.0)
                return self._finish(report, pool, ctx, text, started, stats)
        else:
            self._say(f"structural layer indicated ({', '.join(indicated)})", 0.05)

        self._visited.add(fingerprint(text))
        self._defer_identity = bool(indicated)
        self._explore(
            text,
            ctx,
            0,
            pool,
            report,
            likelihoods={h.cipher: h.likelihood for h in hypotheses},
        )
        self._defer_identity = False
        if not pool.solved:
            # Nothing beat "it was never encrypted"; say so rather than return
            # an empty-handed report.
            pool.add(identity)

        return self._finish(report, pool, ctx, text, started, stats)

    # -- graph exploration -------------------------------------------------- #
    def _explore(
        self,
        text: str,
        ctx: CrackContext,
        depth: int,
        pool: CandidatePool,
        report: CrackReport,
        likelihoods: dict[str, float] | None = None,
    ) -> None:
        if ctx.expired() or pool.certain:
            return

        # Identification is per node, not inherited: once a layer is peeled the
        # text is something else entirely, and ordering attacks by the *outer*
        # text's statistics is how a Vigenere ends up reported as its
        # alphabetically-earlier equivalent.
        if likelihoods is None:
            node_hypotheses, _node_stats = identify(text, self.model)
            likelihoods = {h.cipher: h.likelihood for h in node_hypotheses}
            likelihoods = self._blend_priors(text, ctx, likelihoods)

        # The text at this node may already be the answer -- that is what a
        # peeled layer producing English looks like, and without this candidate
        # the credit goes to whichever no-op cipher restated the same letters.
        if not (depth == 0 and self._defer_identity):
            pool.add(ctx.candidate("none", text, None))

        # Strongly indicated encoding layers are peeled *first*: running a
        # substitution hill climb on a base64 blob wastes the whole budget
        # before the payload is ever seen.
        # Layers are tried in the order the identifier ranked them, not in
        # registry order: a string of 0s and 1s is *also* technically valid
        # base64, and peeling it as base64 first sends the search down a long
        # branch of nonsense before the obvious reading is ever tried.
        applicable = sorted(
            (layer for layer in layer_ciphers() if self._applies(layer, text)),
            key=lambda layer: (
                -likelihoods.get(layer.info.name, 0.0),
                layer.info.cost,
                layer.info.name,
            ),
        )
        strong = [
            layer
            for layer in applicable
            if likelihoods.get(layer.info.name, 0.0) >= STRONG_LAYER
        ]
        before = pool.best.confidence if pool.best else 0.0
        if depth < self.max_depth and strong and not ctx.expired():
            for layer in strong:
                if pool.certain or ctx.expired():
                    break
                self._descend(layer, text, ctx, depth, pool, report)
            if pool.certain:
                return
            # A structural reading that produces English ends the question: no
            # amount of hill climbing on the encoded blob beats "this was
            # base64, and inside it was a sentence".
            if (
                pool.best
                and pool.best.confidence >= SOLVED_CONFIDENCE
                and pool.best.confidence > before
            ):
                return

        # Cheap attacks are fast enough to run before peeling anything else, and
        # they catch the common case where the outer layer is not an encoding at
        # all (Caesar, Atbash, rail fence, Morse, A1Z26 ...).
        self._attack(text, ctx, pool, likelihoods, report, costs=(CHEAP,))
        if pool.certain or ctx.expired():
            return

        # Peel every remaining plausible encoding layer and recurse on the inside.
        if depth < self.max_depth and strong and pool.best and pool.best.confidence >= SOLVED_CONFIDENCE:
            return  # a strongly indicated layer already explained this text
        if depth < self.max_depth:
            for layer in applicable:
                if ctx.expired() or pool.certain:
                    return
                self._descend(layer, text, ctx, depth, pool, report)

        # Everything else: the moderate and expensive attacks.
        self._attack(text, ctx, pool, likelihoods, report, costs=(MODERATE, EXPENSIVE, BRUTAL))
        if pool.certain or ctx.expired():
            return

        # Attack-then-peel: a candidate plaintext may itself be an encoding.
        if depth < self.max_depth and not pool.certain:
            for candidate in pool.ranked(6):
                if ctx.expired():
                    break
                body = candidate.plaintext
                if letters_only(body) and self.model.score(body).confidence >= SOLVED_CONFIDENCE:
                    continue  # already readable, nothing to peel
                for layer in layer_ciphers():
                    inner = self._peel(layer, body)
                    if inner is None:
                        continue
                    fp = fingerprint(inner)
                    if fp in self._visited:
                        continue
                    self._visited.add(fp)
                    self._say(f"peeling {layer.info.name} from a {candidate.cipher} solution", 0.7)
                    chain = list(candidate.steps)
                    if candidate.cipher != "none":
                        chain.append(candidate.cipher)
                    chain.append(layer.info.name)
                    child = ctx.with_steps(
                        tuple(chain),
                        budget=max(2.0, ctx.remaining() * 0.4),
                        depth=depth + 1,
                    )
                    self._explore(inner, child, depth + 1, pool, report)
                    break

    def _blend_priors(
        self, text: str, ctx: CrackContext, likelihoods: dict[str, float]
    ) -> dict[str, float]:
        """Take each cipher's own reading of the text into account when ordering.

        :meth:`identify` looks at the text alone, but a cipher can also see where
        it is in the chain: XOR underneath a peeled hex layer is the classic
        construction, and the byte attacks should run before the letter ones there
        instead of after them.  ``Cipher.likelihood`` exists for exactly this, and
        it only ever *reorders* attacks -- nothing is excluded on a low prior.
        """
        blended = dict(likelihoods)
        for cipher in self.ciphers:
            try:
                own = cipher.likelihood(text, ctx)
            except Exception:
                continue
            if own and own > blended.get(cipher.info.name, 0.0):
                blended[cipher.info.name] = own
        return blended

    @staticmethod
    def _applies(layer, text: str) -> bool:
        try:
            return bool(layer.decodable(text))
        except Exception:
            return False

    def _descend(
        self,
        layer,
        text: str,
        ctx: CrackContext,
        depth: int,
        pool: CandidatePool,
        report: CrackReport,
    ) -> None:
        """Strip one layer and explore what is underneath."""
        inner = self._peel(layer, text)
        if inner is None:
            return
        fp = fingerprint(inner)
        if fp in self._visited:
            return
        self._visited.add(fp)
        self._say(
            f"peeling {layer.info.title} layer (depth {depth + 1}, {len(inner)} characters inside)",
            0.2 + depth * 0.2,
        )
        # child() appends to the chain, so pass only the new step: passing the
        # whole chain here records every ancestor layer twice.
        child = ctx.child(
            budget=max(2.0, ctx.remaining() * 0.6),
            steps=(layer.info.name,),
            depth=depth + 1,
        )
        self._explore(inner, child, depth + 1, pool, report)

    @staticmethod
    def _peel(layer, text: str) -> str | None:
        """Try to strip one encoding layer; ``None`` when it does not apply."""
        try:
            if not layer.decodable(text):
                return None
            out = layer.decode(text)
        except Exception:
            return None
        if out is None:
            return None
        if isinstance(out, bytes):
            # latin-1, always: it is the only decode that maps every byte to a
            # character and back unchanged, and the byte-oriented attacks below
            # (XOR above all) need the peeled payload to be bit-exact.  A UTF-8
            # preference here silently re-encodes high bytes as two.
            out = out.decode("latin-1")
        out = trim(out)
        if len(out) < 2 or out == trim(text):
            return None
        return out

    # -- attacking one node ------------------------------------------------- #
    def _attack(
        self,
        text: str,
        ctx: CrackContext,
        pool: CandidatePool,
        likelihoods: dict[str, float],
        report: CrackReport,
        costs: tuple[float, ...] = (CHEAP, MODERATE, EXPENSIVE, BRUTAL),
    ) -> None:
        letters = letters_only(text)
        for cost in costs:
            if ctx.expired() or pool.certain:
                return
            group = [c for c in self.ciphers if c.info.cost == cost]
            if not group:
                continue
            # Within a phase: likely ciphers first, then the canonical name among
            # equivalent readings (Vigenere before its variant spellings -- they
            # decrypt identically, and the search stops at the first certain
            # answer, so whichever runs first is the one the user is told about),
            # then alphabetical for determinism.
            group.sort(
                key=lambda c: (
                    -likelihoods.get(c.info.name, 0.0),
                    Candidate.EQUIVALENT_CIPHER_RANK.get(c.info.name, 1),
                    c.info.name,
                )
            )
            for cipher in group:
                if ctx.expired() or pool.certain:
                    return
                self._run(cipher, text, letters, ctx, pool, report, cost, len(group))

    def _run(
        self,
        cipher: Cipher,
        text: str,
        letters: str,
        ctx: CrackContext,
        pool: CandidatePool,
        report: CrackReport,
        cost: float,
        group_size: int,
    ) -> None:
        prepared = cipher.prepare(text)
        alphabet = cipher.info.alphabet
        usable = prepared if alphabet is None else prepared
        if len(usable) < max(cipher.info.min_length, 2) and not ctx.exhaustive:
            return
        # Expensive attacks divide what is left of the budget between them;
        # cheap ones just get their cap.
        remaining = ctx.remaining()
        if cost >= EXPENSIVE:
            share = max(2.0, remaining / max(1, group_size))
            slice_seconds = min(PHASE_SLICES[cost], max(share, remaining * 0.5))
        else:
            slice_seconds = min(PHASE_SLICES[cost], max(1.0, remaining))
        sub = ctx.child(budget=slice_seconds)
        log = AttackLog(cipher.info.name, time.time())
        tried = 0
        best_before = pool.best_confidence
        self._say(
            f"attacking with {cipher.info.title} "
            f"({cipher.info.family.value}, {slice_seconds:.0f}s slice)",
            -1.0,
            cipher=cipher.info.name,
        )
        try:
            for candidate in cipher.crack(usable, sub):
                tried += 1
                pool.add(candidate)
                if candidate.certain:
                    log.status = "solved"
                    log.detail = f"key {candidate.key_repr}"
                    break
        except Exception as exc:  # a broken attack must never kill the solve
            log.status = "error"
            log.detail = f"{type(exc).__name__}: {exc}"
            if STRICT_ATTACKS:
                # Development aid: BUTTCRACK_STRICT=1 turns a swallowed bug in one
                # attack into a traceback instead of a silently missing candidate.
                raise
        log.finished = time.time()
        log.tried = tried
        log.best_confidence = pool.best_confidence
        if log.status == "running":
            if pool.best_confidence > best_before:
                log.status = "improved"
            elif sub.expired():
                log.status = "budget"
            else:
                log.status = "exhausted"
        report.attacks.append(log)
        if pool.best_confidence >= SOLVED_CONFIDENCE:
            self._say(
                f"{cipher.info.title} produced readable plaintext "
                f"(confidence {pool.best_confidence:.2f}, key {pool.best.key_repr})",
                -1.0,
                cipher=cipher.info.name,
            )

    # -- finishing ---------------------------------------------------------- #
    def _finish(
        self,
        report: CrackReport,
        pool: CandidatePool,
        ctx: CrackContext,
        original: str,
        started: float,
        stats,
    ) -> CrackReport:
        ranked = pool.ranked(12)
        report.candidates = ranked
        report.best = ranked[0] if ranked else None
        report.solved = bool(report.best and report.best.confidence >= SOLVED_CONFIDENCE)
        report.elapsed = time.time() - started
        if report.best is not None:
            self._present(report, original, stats)
        self._say(
            f"{'solved' if report.solved else 'best effort'} in {report.elapsed:.2f}s "
            f"({len(report.attacks)} attacks, confidence {report.confidence:.2f})",
            1.0,
        )
        return report

    def _present(self, report: CrackReport, original: str, stats) -> None:
        """Add human-friendly renderings of the winning plaintext."""
        best = report.best
        if best is None:
            return
        notes = best.notes
        cipher = None
        from .ciphers import try_get

        cipher = try_get(best.cipher)
        family = cipher.info.family if cipher else None
        letters = letters_only(best.plaintext)
        # The ciphertext's layout can only be laid back over the plaintext when
        # the ciphertext *is* that layout: a position-preserving cipher, no
        # encoding peeled away underneath it, letter-shaped input, and the same
        # number of letters.  Otherwise word breaks are re-derived instead.
        if (
            family in POSITION_PRESERVING
            and best.cipher not in LAYOUT_HOSTILE
            and not best.steps
            and stats.is_letter_text
            and len(letters) == stats.letters
        ):
            shaped = restore_shape(letters, original)
            if shaped is not None:
                notes["formatted"] = shaped
        if "formatted" not in notes and letters:
            score = best.score or self.model.score(best.plaintext)
            if score.words_found:
                notes["respaced"] = respaced(letters, score.words_found)
        if best.cipher == "caesar" and str(best.key_repr) == "13":
            notes["also_known_as"] = "ROT13"
        elif best.cipher == "vigenere":
            digits = gronsfeld_key(best.key)
            if digits:
                # A Vigenere key that only ever uses shifts 0-9 is a Gronsfeld
                # digit key.  For an n-letter key the odds of that by chance are
                # (10/26)^n, so naming the more specific cipher is the honest
                # reading -- and the digit key is the secret the user actually
                # wants back.
                best.cipher = "gronsfeld"
                best.key = {"key": digits}
                notes["also_known_as"] = f"Vigenere with key {_vigenere_word(digits)}"
            else:
                # Variant Beaufort with the complementary key reads the same
                # message; saying so is cheaper than the user wondering which
                # convention the key is in.
                complement = complementary_key(best.key)
                if complement:
                    notes["also_known_as"] = f"variant Beaufort with key {complement}"
        if best.steps or best.cipher != "none":
            chain = list(best.steps) + ([] if best.cipher == "none" else [best.cipher])
            notes["decode_chain"] = " -> ".join(chain)


def gronsfeld_key(key: Any) -> str:
    """The digit key behind a Vigenere solve, when there is one.

    Gronsfeld is Vigenere restricted to the shifts 0-9, written as digits.  A
    recovered key using only A-J is therefore a Gronsfeld key with overwhelming
    likelihood, and the digits are the form the user encrypted with.
    """
    from .text import A26

    word = key.get("key") if isinstance(key, dict) else key
    if not isinstance(word, str) or not word:
        return ""
    upper = word.upper()
    if any(ch not in A26[:10] for ch in upper):
        return ""
    return "".join(str(A26.index(ch)) for ch in upper)


def _vigenere_word(digits: str) -> str:
    """``"31415"`` -> ``"DBEBF"``: the same key in Vigenere letters."""
    from .text import A26

    return "".join(A26[int(d) % 26] for d in digits if d.isdigit())


def complementary_key(key: Any) -> str:
    """The key that reads the same message under the variant-Beaufort convention.

    Vigenere decrypts with ``plain = cipher - key``; variant Beaufort decrypts
    with ``plain = cipher + key``.  The two are the same transformation with the
    key negated mod 26, so a Vigenere solve always has a variant-Beaufort twin.
    """
    from .text import A26

    word = key.get("key") if isinstance(key, dict) else key
    if not isinstance(word, str) or not word:
        return ""
    return "".join(A26[(26 - A26.index(ch)) % 26] for ch in word.upper() if ch in A26)


def solve(
    ciphertext: str,
    *,
    budget: float = 30.0,
    workers: int = 1,
    max_depth: int = 3,
    hints: dict[str, Any] | None = None,
    progress: Callable[[str, float, dict], None] | None = None,
    model: LanguageModel | None = None,
    exhaustive: bool = False,
) -> CrackReport:
    """Convenience wrapper around :class:`Solver`."""
    return Solver(
        budget=budget,
        workers=workers,
        max_depth=max_depth,
        model=model,
        hints=hints,
        progress=progress,
        exhaustive=exhaustive,
    ).solve(ciphertext)
