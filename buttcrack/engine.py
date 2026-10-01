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
5. **Attack after attacking.**  A candidate from a cipher that rearranges or
   reflects text rather than encoding it (reverse, rail fence, skip, route) is
   explored as a node in its own right, so ``reverse(vigenere(...))`` and
   ``rail_fence(caesar(...))`` come apart one cipher at a time.

The default search depth is six steps, which is what a layered puzzle actually
looks like (``base64 -> hex -> reverse -> morse -> caesar -> plaintext``).  Depth
is affordable because three things bound it: visited nodes are fingerprinted so
a stack of reversible layers cannot loop, the whole search shares one deadline
that every stage checks, and :data:`MAX_NODES` caps how many nodes a single
solve may open however the branching works out.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Iterable
from typing import Any, Callable

from .ciphers import attack_ciphers, layer_ciphers
from .ciphers.base import BRUTAL, CHEAP, EXPENSIVE, MODERATE, Cipher, CrackContext, Family
from .detect import identify
from .lang import (
    CERTAIN_CONFIDENCE,
    LANGUAGES,
    SOLVED_CONFIDENCE,
    LanguageModel,
    detect_language,
    get_model,
    resolve_language,
)
from .results import AttackLog, Candidate, CrackReport
from .text import A26, letters_only, respaced, restore_shape, trim

#: Families whose ciphers preserve character positions, so the original spacing
#: and case can be laid back over the solution.
#: Set ``BUTTCRACK_STRICT=1`` to let a failing attack raise instead of being
#: recorded in the attack log and skipped.
STRICT_ATTACKS = bool(os.environ.get("BUTTCRACK_STRICT"))

POSITION_PRESERVING = {Family.SHIFT, Family.SUBSTITUTION, Family.POLYALPHABETIC, Family.POLYGRAPHIC, Family.WHEEL}

#: Members of those families that do *not* keep a letter in its own position:
#: ROT47 works over printable ASCII, so a letter can come out as a symbol and a
#: symbol as a letter, and Reverse changes the order outright.  Laying the
#: ciphertext's shape over the plaintext for either of them produces noise.
LAYOUT_HOSTILE = frozenset({"rot47", "reverse"})

#: Ciphers whose output is worth exploring as a *node* rather than just scored.
#: These rearrange or reflect the text instead of encoding it, so what comes out
#: of them is frequently another cipher rather than the plaintext -- the classic
#: ``reverse(vigenere(...))`` and ``rail_fence(caesar(...))`` constructions.
#:
#: Substitution-family ciphers are deliberately absent: two stacked shifts are
#: just one shift, and a substitution on top of a substitution is a single
#: substitution, so recursing into them can only re-find what the sweep at this
#: node already found.
RECURSIVE_CIPHERS = frozenset({"reverse", "rail_fence", "skip", "route",
                               "columnar", "myszkowski", "amsco"})

#: ROT47 is deliberately absent: it is an involution over printable ASCII, so
#: applying it to a letters-only text produces punctuation, and a chain of them
#: is noise.  It kept being followed because that noise scores unpredictably.

#: The subset whose output is a *fact* rather than a search result.  Only
#: `reverse` qualifies -- it is keyless, so its output is the one text it could
#: possibly be.  Everything else here picked a key out of a search and is
#: followed only after `reverse`.
EXACT_RECURSIVE = frozenset({"reverse"})

#: How many *cipher* unwraps one chain may contain.  Encoding layers are
#: self-announcing and cheap to verify, so six of them stack happily; ciphers
#: are not, and an unbounded cipher-on-cipher search finds a plausible-looking
#: three-cipher chain for any input whatsoever.  Two is enough for the
#: constructions that occur in practice (a transposition or a reflection
#: wrapped around a real cipher) and is the point where the evidence for each
#: extra step stops outweighing the extra freedom it buys.
MAX_CIPHER_UNWRAPS = 2

#: Ceiling on cipher unwraps across the whole solve, so a text with many
#: plausible transposition readings cannot spend the budget on all of them.
#: Cheap readings get their own, looser ceiling: they are the ones that come in
#: dozens, and each costs a fraction of a second.
MAX_CIPHER_NODES = 10
MAX_CHEAP_CIPHER_NODES = 40

#: How thorough an exploration of a node was.  A node first seen from the cheap
#: pass may be revisited by a later pass that is allowed to try more; a node
#: already explored as thoroughly is skipped.
MODE_RANK = {"cheap": 0, "bounded": 1, "full": 2}

#: Ciphers whose whole keyspace is small enough that the *correct* key cannot be
#: recognised from the output alone.  A transposition permutes letters, so every
#: key produces the same letter distribution and the same chi-squared score; if
#: what is underneath is itself enciphered, the correct key's output is
#: indistinguishable from the rest.  Several readings are therefore followed
#: rather than just the best-scoring one.
AMBIGUOUS_RECURSIVE = frozenset({"rail_fence", "skip", "reverse"})

#: Ciphers used to probe a transposition reading on the first pass.  Three
#: keyless-or-tiny sweeps over about twenty readings is roughly sixty
#: decryptions -- small enough to run at every node without noticing.  Affine
#: (312 keys) and the periodic ciphers are held back for the last-resort pass,
#: because twenty readings times 312 keys is no longer free and would come out
#: of the budget of the attack that was going to work.
PROBE_CHEAP = ("caesar", "atbash", "rot13")

def descent_evidence(depth: int) -> float:
    """How convincing a layer must look to be peeled at this depth.

    Zero at the top (try everything once), rising to a real bar further down.
    The numbers are set against the sniffers: the structural decodes score
    0.8-0.95 when they are right, and the "this is also valid base64" readings
    land near 0.4, so the ramp separates the two by depth 2.
    """
    return (0.0, 0.2, 0.35, 0.5, 0.5, 0.5)[min(depth, 5)]


#: Smallest share of a phase any cipher gets, however unlikely the identifier
#: thinks it is.  Identification orders the search; it must never veto it.
LIKELIHOOD_FLOOR = 0.15

#: Attacks tried before any layer is peeled: keyless or 312-key, instant, and
#: incapable of inventing a plausible-looking wrong answer.
PRE_PEEL_CIPHERS = ("caesar", "rot13", "atbash", "rot47", "affine", "reverse")

#: The expensive probe set, used only as a last resort (see `_probe_readings`).
PROBE_PERIODIC = ("vigenere", "beaufort", "quagmire3", "porta", "affine", "variant_beaufort", "gronsfeld")

#: Time that must remain before the last-resort probe is worth starting.
LAST_RESORT_SECONDS = 4.0

#: Absolute ceiling on states the deep chain search may open, and the rate it
#: gets through them (measured on this machine: 12,700 states a second at 160
#: letters, a state being one decryption plus one n-gram scoring).  The working cap is whichever is smaller, the
#: ceiling or what the remaining time buys -- so a short budget stays short and
#: a long one searches a level deeper instead of overrunning.
CHAIN_STATE_CAP = 250_000
CHAIN_STATES_PER_SECOND = 12_000

#: Share of the remaining time the chain search may spend.  It is generous
#: because of *when* it runs: the deep pass only starts after every attack has
#: had its turn and none of them produced a certain answer, so what is left is
#: better spent here than held back for nothing.
CHAIN_SHARE = 0.7

#: Share of that going to the best-ranked substitution.  The histogram nearly
#: always ranks the true one first, so it gets the lion's share -- but not all
#: of it, because "nearly always" is not "always".
CHAIN_FIRST_SHARE = 0.6

#: N-gram fitness a state must reach before it is worth a full scoring, and how
#: much of the state to judge it on.  A transposition permutes the whole text,
#: so its first 120 characters are as representative as any other slice.
CHAIN_FITNESS_GATE = -5.6
CHAIN_GATE_CHARS = 120

#: How many composed transposition steps the deep chain search may stack.  With
#: the substitution it tests for underneath, six is the advertised depth of a
#: pure cipher stack.
MAX_CHAIN_STEPS = 5

#: Depth of the early pass, which runs before the expensive attacks.  Two steps
#: is about two hundred states -- twenty milliseconds -- and covers the common
#: `rail_fence(caesar)` shape without taking anything from the attacks.
CHAIN_SHALLOW_STEPS = 2

#: Chi-squared per letter, against English and best of 26 rotations plus
#: Atbash, below which a text could be a transposition stack (see
#: `_transposition_shaped`).  English scores 0.116, Vigenere 1.711.
CHAIN_GATE_CHI = 0.6

#: Per-probe time cap.  Deliberately tight: a periodic cipher that is going to
#: fall on a 140-letter reading falls in well under a second, and the pass is
#: judged on how many readings it covers before the clock runs out, not on how
#: thoroughly it fails on the first few.
PROBE_SECONDS = 1.5

#: Share of the remaining time one cipher's sweep over all readings may take.
PROBE_CIPHER_SHARE = 0.5

#: How many readings to follow for those, and the per-reading time cap.  Many
#: cheap children beat a few expensive ones here: the reading that matters is
#: not the best-scoring one but *some* one of them, and a wrong reading is
#: rejected in well under a second.
AMBIGUOUS_FOLLOW = 8
AMBIGUOUS_CHILD_SECONDS = 4.0

#: Fraction of a node's remaining time held back from the expensive attacks so
#: the recursion that follows them is not starved.
RECURSION_RESERVE = 0.4

#: Per-attack time slices by cost class.  Cheap attacks are so fast that a hard
#: cap costs nothing; expensive ones divide what is left.  BRUTAL holds the
#: searches that cannot promise anything in bounded time (Bifid, M-94); its cap
#: is high because a wheel-cipher climb measured ~2-in-3 solves inside 20 s on
#: 250 letters and essentially nothing inside 12.
PHASE_SLICES = {CHEAP: 3.0, MODERATE: 6.0, EXPENSIVE: 25.0, BRUTAL: 20.0}

#: How much of a cipher's own likelihood survives into the scheduling order.
#: Self-assessments are systematically more optimistic than the identifier's
#: view, which is built from text statistics across all the families at once.
SELF_ASSESSMENT_WEIGHT = 0.8

#: Likelihood at which an attack stops being speculative.  Above this the
#: scheduler guarantees it enough time to actually run.
WELL_EVIDENCED = 0.5

#: The smallest slice worth giving a well-evidenced attack.  Below a few
#: seconds a stochastic search cannot complete a single restart, so the time
#: is spent with no chance of a result.
MIN_VIABLE_SLICE = 8.0

#: Hard cap on decoding-graph nodes per solve.  Depth alone does not bound the
#: search -- a text that is plausibly five different encodings at once branches
#: five ways at every level -- and the deadline alone would spend the whole
#: budget opening nodes it never gets to attack.  400 is far above what a real
#: puzzle needs (a six-layer stack with two plausible readings per level is 63)
#: and well below the point where bookkeeping shows up in a profile.
MAX_NODES = 400

#: Share of the remaining time a child node may take.  Deeper nodes get a
#: larger share of a smaller pot: at depth 5 the answer is either down this
#: branch or nowhere, so splitting the remainder evenly with hypothetical
#: siblings wastes it.  With the ramp a six-deep chain still reaches its
#: innermost node with ~9% of the original budget instead of 0.6**6 = 4.7%.
def layer_share(depth: int) -> float:
    return min(0.9, 0.6 + 0.06 * depth)


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
        #: Cached leader, invalidated on every add (see `best`).
        self._best: Candidate | None = None

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
                self._best = None
                return True
            return False
        self._by_text[key] = candidate
        self._order.append(key)
        self._best = None
        return True

    @property
    def best(self) -> Candidate | None:
        """The leading candidate, cached between additions.

        This is read constantly -- every attack loop asks `pool.certain` after
        each candidate, and the deep chain search asks it hundreds of thousands
        of times -- and recomputing it walked the whole pool and rebuilt a
        formatted key string per candidate through `sort_key`.  Profiling a
        30-second solve found 7.4 of its 8 seconds in that one property.  The
        pool only changes on `add`, so the answer is cached there.
        """
        if self._best is None and self._by_text:
            self._best = min(self._by_text.values(), key=Candidate.sort_key)
        return self._best

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
        max_depth: int = 6,
        model: LanguageModel | None = None,
        progress: Callable[[str, float, dict], None] | None = None,
        ciphers: Iterable[Cipher] | None = None,
        hints: dict[str, Any] | None = None,
        exhaustive: bool = False,
        language: str = "english",
    ):
        self.budget = float(budget)
        self.workers = max(1, int(workers))
        self.max_depth = max_depth
        #: Identification likelihoods for the node being attacked, so the
        #: scheduler can guarantee a workable slice to a well-evidenced
        #: cipher instead of handing it its arithmetic share of the dregs.
        self._likelihood_floor: dict[str, float] = {}
        #: ``language`` only names the model to load; an explicit ``model``
        #: always wins, so callers that built their own model keep control.
        self.language = resolve_language(language)
        self.model = model or get_model(self.language)
        self.progress = progress
        self.ciphers = list(ciphers) if ciphers is not None else attack_ciphers()
        self.hints = hints or {}
        self.exhaustive = exhaustive
        self._visited: set[str] = set()
        #: fingerprint -> how thoroughly that text has already been explored.
        self._explored: dict[str, int] = {}
        self._pending: list[tuple[str, tuple[str, ...], int]] = []
        self._nodes = 0
        self._cipher_nodes = 0
        self._cheap_cipher_nodes = 0
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
        report = CrackReport(
            ciphertext=ciphertext, budget=self.budget, workers=self.workers,
            language=self.model.language,
        )
        if not text:
            report.elapsed = time.time() - started
            return report

        self._nodes = 0
        self._cipher_nodes = 0
        self._cheap_cipher_nodes = 0
        self._explored.clear()
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
            # Blend in each cipher's own reading of the text, exactly as the
            # child nodes do.  Identification works from text statistics and
            # does not know, for instance, that the M-94's own detector is
            # confident: without this the root node scheduled attacks on the
            # identifier's view alone, and a cipher whose self-assessment was
            # the strongest signal available could be left with no time.
            likelihoods=self._blend_priors(
                text, ctx, {h.cipher: h.likelihood for h in hypotheses}
            ),
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
        mode: str = "full",
        cipher_depth: int = 0,
    ) -> None:
        """Explore one node of the decoding graph.

        ``mode`` says how much this node is worth:

        ``full``
            the default, and what every node reached by peeling an *encoding*
            gets.  Encodings are self-announcing, so what is inside one deserves
            the whole attack set.
        ``bounded``
            reached by unwrapping a cipher whose key was searched for.  Cheap
            and moderate attacks only -- the branching factor of cipher-on-cipher
            recursion is high, and a Playfair climb at every such node would
            spend the entire budget on the least likely branches.
        ``cheap``
            reached by unwrapping one *reading* of a transposition, of which
            there are a dozen and eleven are wrong.  Cheap attacks only, so
            being wrong costs milliseconds.  This is the pass that catches
            ``rail_fence(caesar)``.
        """
        if ctx.expired() or pool.certain:
            return
        self._explored[fingerprint(text)] = max(
            self._explored.get(fingerprint(text), -1), MODE_RANK[mode]
        )
        self._nodes += 1
        if self._nodes > MAX_NODES:
            self._say(f"node budget reached ({MAX_NODES}); ranking what was found", 0.95)
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

        # Strongly indicated encoding layers are peeled next, before the
        # expensive attacks: running a substitution hill climb on a base64 blob
        # wastes the whole budget before the payload is ever seen.
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
        # A handful of keyless substitutions run before anything is peeled.
        # They cost a millisecond each and they close a real hole: ROT47 output
        # is punctuation-heavy ASCII, which is *also* valid base85, so the
        # base85 layer was peeled first and something three levels down scraped
        # past the solved threshold before the one-step answer was ever tried.
        #
        # Only these ciphers go first -- they have no key to search, so they
        # cannot invent a plausible wrong answer -- and the search stops here
        # only when nothing else is indicated.  When a layer *is* strongly
        # indicated both readings are produced and the ranking decides between
        # them, because "this is ROT47" and "this is a NATO spelling alphabet"
        # can both look compelling and only one of them will read as English.
        produced: list[Candidate] = []
        self._quick_attacks(text, ctx, pool, report, produced, likelihoods)
        if ctx.expired() or (pool.certain and not strong):
            return

        before = pool.best.confidence if pool.best else 0.0
        if depth < self.max_depth and strong and not ctx.expired():
            for layer in strong:
                if pool.certain or ctx.expired():
                    break
                self._descend(
                    layer, text, ctx, depth, pool, report,
                    likelihoods.get(layer.info.name, 0.0),
                )
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

        # The rest of the cheap tier: fast enough to run before peeling
        # anything else, and it catches the common case where the outer layer
        # is not an encoding at all (rail fence, Morse, A1Z26, XOR ...).
        self._attack(text, ctx, pool, likelihoods, report, costs=(CHEAP,), sink=produced)
        if pool.certain or ctx.expired():
            return

        # Peel every remaining plausible encoding layer and recurse on the inside.
        if depth < self.max_depth and strong and pool.best and pool.best.confidence >= SOLVED_CONFIDENCE:
            return  # a strongly indicated layer already explained this text
        if depth < self.max_depth:
            floor = descent_evidence(depth)
            for layer in applicable:
                if ctx.expired() or pool.certain:
                    return
                # Deeper peels need better evidence.  Almost any text is
                # *technically* valid base64 or base85, so at depth 0 those
                # readings are worth a look and by depth 3 they are noise: a
                # string of Polybius digits would otherwise sprout a base64
                # branch, and that branch its own, until the budget was gone
                # and the substitution search that would have solved it never
                # ran.  A strongly indicated layer is never blocked, which is
                # what keeps genuine six-deep stacks working -- every step of
                # `base32 -> base16 -> base64 -> morse` sniffs above 0.75.
                evidence = likelihoods.get(layer.info.name, 0.0)
                if evidence < floor:
                    continue
                self._descend(layer, text, ctx, depth, pool, report, evidence)

        # The moderate attacks (Vigenere, XOR, ...) come next: they are the most
        # common answer by a wide margin, and anything that unwraps *this* text
        # must be tried before anything that guesses at a second layer.
        if mode != "cheap":
            self._attack(text, ctx, pool, likelihoods, report, costs=(MODERATE,), sink=produced)
        if pool.certain or ctx.expired():
            return

        # Attack-then-attack: stacks of transpositions with a substitution
        # underneath, to five composed steps.  This subsumes the single-reading
        # probe it replaced -- depth 1 of the chain search *is* that probe --
        # and it is the pass that takes `rail_fence(caesar)` apart at one step
        # and `reverse(rail_fence(skip(reverse(rail_fence(rot13)))))` at five.
        # It runs before the expensive attacks because it costs a fraction of a
        # second: see `_chain_search` for why the combinatorics collapse.
        if depth < self.max_depth and not pool.certain and self._transposition_shaped(text, ctx):
            self._chain_search(text, ctx, pool, CHAIN_SHALLOW_STEPS)
        if pool.certain or ctx.expired():
            return

        # The expensive attacks: substitution, Playfair, columnar, Hill, M-94.
        # They run against a *reduced* context so that finishing them does not
        # leave the second recursion pass with nothing to spend.  Without the
        # reserve a text with several plausible transposition readings spends
        # every second on Hill and Playfair and never looks underneath.
        if mode == "full":
            reserve = ctx.remaining() * RECURSION_RESERVE if depth < self.max_depth else 0.0
            attack_ctx = ctx.child(budget=max(1.0, ctx.remaining() - reserve))
            self._attack(
                text, attack_ctx, pool, likelihoods, report,
                costs=(EXPENSIVE, BRUTAL), sink=produced,
            )
            if pool.certain or ctx.expired():
                return

        # Deep chain search: stacks of up to five composed transpositions with a
        # substitution underneath.  It waits until here because it is the one
        # pass that can spend a real share of the budget without any cipher
        # having asked for it -- Myszkowski and AMSCO are transpositions of
        # English too, they pass the gate, and their permutations are *not*
        # reachable by composing rail fences, so running this first would take
        # the budget from the attacks that were going to solve them.
        if (
            depth == 0
            and not pool.certain
            and (pool.best.confidence if pool.best else 0.0) < CERTAIN_CONFIDENCE
            and self._transposition_shaped(text, ctx)
        ):
            self._chain_search(text, ctx, pool, MAX_CHAIN_STEPS)
        if pool.certain or ctx.expired():
            return

        # Last resort: probe the transposition readings again, this time with
        # the periodic ciphers.  A dozen Vigenere solves is seconds rather than
        # milliseconds, so it happens only at the outermost node, only when
        # nothing else has held up, and only with time left to spend -- the
        # `skip(vigenere)` construction and its relatives.
        #
        # The bar here is *certainty*, not the solved threshold: a wrong answer
        # that scrapes past 0.62 is exactly the situation where the reading
        # underneath a transposition is worth another few seconds.
        if (
            depth == 0
            and not pool.certain
            and (pool.best.confidence if pool.best else 0.0) < CERTAIN_CONFIDENCE
            and ctx.remaining() > LAST_RESORT_SECONDS
        ):
            self._say("no reading held up; trying periodic ciphers under each transposition", 0.9)
            self._probe_readings(text, ctx, depth, pool, PROBE_PERIODIC)

        # Second pass: the structural results worth a node of their own --
        # `reverse` above all, which is keyless and so has exactly one reading.
        if depth < self.max_depth and not pool.certain:
            self._recurse_candidates(
                produced, ctx, depth, pool, report, cipher_depth,
                child_mode="bounded", limit=3,
            )

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
                        budget=max(1.0, ctx.remaining() * layer_share(depth) * 0.7),
                        depth=depth + 1,
                    )
                    self._explore(inner, child, depth + 1, pool, report)
                    break

    def _quick_attacks(
        self,
        text: str,
        ctx: CrackContext,
        pool: CandidatePool,
        report: CrackReport,
        sink: list[Candidate],
        likelihoods: dict[str, float] | None = None,
    ) -> None:
        """Run the keyless substitutions: no key to search, no false positives.

        Ordered by the identifier's opinion, exactly as the main attack phase
        is.  Order matters even among equivalent answers: ROT13 *is* a Caesar
        shift of 13, so whichever runs first claims the solve, and the report
        should say ROT13 when the identifier recognised ROT13.
        """
        from .ciphers import try_get

        letters = letters_only(text)
        ranked = sorted(
            PRE_PEEL_CIPHERS,
            key=lambda n: (
                -(likelihoods or {}).get(n, 0.0),
                # Equivalent readings tie on evidence by construction, so the
                # canonical name has to break the tie here as well: without
                # this the order falls back to however PRE_PEEL_CIPHERS
                # happens to be written, and a ROT13 gets reported as a
                # Caesar of 13.
                Candidate.EQUIVALENT_CIPHER_RANK.get(n, 1),
                n,
            ),
        )
        for name in ranked:
            if pool.certain or ctx.expired():
                return
            cipher = try_get(name)
            if cipher is None:
                continue
            self._run(cipher, text, letters, ctx, pool, report, CHEAP, 1.0 / len(PRE_PEEL_CIPHERS), sink)

    def _readings(self, text: str, limit: int = 24, wide: bool = True) -> list[tuple[str, Any, str]]:
        """Every plausible way this text could be a small transposition.

        Returns ``(cipher name, key, decrypted text)``.  The keys are
        *enumerated*, not taken from the attacks that already ran, and that
        distinction is the whole point: a transposition permutes letters, so
        every key produces identical letter statistics and a cipher's own
        ranking of its keys is meaningless when what is underneath is still
        enciphered.  The correct reading is routinely nowhere near the top of
        the list the attack returned.

        Only ciphers with a keyspace small enough to walk are included.
        ``wide`` sweeps every reading; the narrow set keeps the rail counts and
        strides that actually occur in puzzles, and exists because the
        last-resort pass pays a full Vigenere solve per reading and has seconds,
        not minutes, to work with -- fourteen readings it can finish beat
        nineteen it cannot.
        """
        from .ciphers import try_get

        readings: list[tuple[str, Any, str]] = []
        for name, keys in (
            ("reverse", [None]),
            ("rail_fence", [(rails, 0) for rails in range(2, 9 if wide else 7)]),
            ("skip", list(range(2, 13 if wide else 10))),
        ):
            cipher = try_get(name)
            if cipher is None:
                continue
            for key in keys:
                try:
                    plain = cipher.decrypt(text) if key is None else cipher.decrypt(text, key)
                except Exception:
                    continue
                if len(letters_only(plain)) >= 16:
                    readings.append((name, key, plain))
        return readings[:limit]

    def _probe_readings(
        self,
        text: str,
        ctx: CrackContext,
        depth: int,
        pool: CandidatePool,
        probes: tuple[str, ...],
    ) -> None:
        """Try a few small ciphers directly against each transposition reading.

        This is deliberately *not* a recursive exploration.  Opening a node per
        reading means re-running identification, the layer sniffers and the
        whole cheap attack set twenty times over, which costs seconds and
        crowds out the attacks that were going to work.  A probe runs the named
        ciphers against the reading and stops -- no identification, no peeling,
        no recursion -- so its cost is bounded by the probe list.
        """
        from .ciphers import try_get

        ciphers = [c for c in (try_get(name) for name in probes) if c is not None]
        seen: set[str] = set()
        readings = []
        for name, key, plain in self._readings(text, wide=False):
            fp = fingerprint(plain)
            if fp in seen:
                continue
            seen.add(fp)
            readings.append((name, key, plain))

        # Cipher-major, not reading-major: the probe list is ordered by how
        # often each cipher turns up, so sweeping every reading with Vigenere
        # before trying any of them with Porta means a deadline that lands
        # mid-probe still covered the likely answers.  Reading-major order
        # spends the whole budget on the first few readings.
        for cipher in ciphers:
            if ctx.expired() or pool.certain:
                return
            # Each cipher gets a share of what is left and spends it evenly
            # across the readings, so a sweep always *finishes*.  A fixed
            # per-probe cap does not work here: too generous and the clock runs
            # out halfway through the first cipher (the right reading is as
            # likely to be the last one as the first), too tight and a cipher
            # that needed a second never lands at all.
            sweep = ctx.remaining() * PROBE_CIPHER_SHARE
            per_reading = max(0.25, min(PROBE_SECONDS, sweep / max(1, len(readings))))
            for name, key, plain in readings:
                if ctx.expired() or pool.certain:
                    return
                if len(cipher.prepare(plain)) < max(cipher.info.min_length, 2):
                    continue
                sub = ctx.with_steps(
                    ctx.steps + (name,),
                    budget=min(per_reading, max(0.2, ctx.remaining())),
                    depth=depth + 1,
                )
                try:
                    for result in cipher.crack(plain, sub):
                        result.notes.setdefault("reading", f"{name} key {key}")
                        pool.add(result)
                        if result.certain:
                            return
                except Exception:  # a probe must never break the solve
                    if STRICT_ATTACKS:
                        raise

    # -- deep cipher chains -------------------------------------------------- #
    def _transposition_shaped(self, text: str, ctx: CrackContext) -> bool:
        """Could this text be a transposition of English under one substitution?

        A transposition does not change which letters are present, and a
        monoalphabetic substitution renames them consistently, so a stack of
        the two leaves a letter histogram that matches English under *some*
        rotation or reflection.  Measured over this corpus the separation is
        not subtle -- chi-squared per letter against English, best of the 26
        rotations and Atbash:

        ===============================  =============
        text                             chi / letter
        ===============================  =============
        English, and any transposition          0.116
        of it (rail fence, columnar,
        Myszkowski, AMSCO, six stacked
        ciphers)
        Vigenere                                1.711
        Hill                                    2.214
        Simple substitution                     3.658
        ===============================  =============

        So the gate is cheap, exact in practice, and keeps the chain search off
        the texts it could never explain -- which matters because the search is
        the only pass that can spend a serious share of the budget without a
        cipher having asked for it.
        """
        letters = letters_only(text).upper()
        if len(letters) < 24:
            return False
        counts = [0] * 26
        for ch in letters:
            counts[A26.index(ch)] += 1
        ref = ctx.model.monogram_reference()
        expected = [ref[A26[i]] * len(letters) for i in range(26)]

        def chi(mapped: list[int]) -> float:
            return sum(
                (mapped[i] - expected[i]) ** 2 / expected[i]
                for i in range(26)
                if expected[i] > 0
            )

        best = min(chi([counts[(i + shift) % 26] for i in range(26)]) for shift in range(26))
        best = min(best, chi([counts[25 - i] for i in range(26)]))
        return best / len(letters) <= CHAIN_GATE_CHI

    def _monoalphabetic_candidates(
        self, text: str, ctx: CrackContext, keep: int = 3
    ) -> list[tuple[str, Any, str]]:
        """The most likely monoalphabetic corrections for ``text``, applied.

        Returns ``(cipher name, key, corrected text)``, always including the
        identity.  The trick that makes this possible up front is that a
        transposition does not change *which* letters are present, only where
        they are: the letter distribution of the ciphertext is exactly the
        distribution of the plaintext after whatever substitution was applied,
        no matter how many transpositions were stacked on top.  So the shift
        can be read off the histogram before a single transposition is undone.
        """
        letters = letters_only(text).upper()
        out: list[tuple[str, Any, str]] = []
        if len(letters) < 24:
            return [("none", None, text)]
        counts = [0] * 26
        for ch in letters:
            counts[A26.index(ch)] += 1
        ref = ctx.model.monogram_reference()
        expected = [ref[A26[i]] * len(letters) for i in range(26)]

        def chi(mapped: list[int]) -> float:
            total = 0.0
            for i in range(26):
                exp = expected[i]
                if exp > 0:
                    diff = mapped[i] - exp
                    total += diff * diff / exp
            return total

        # Shift 0 is in the list on purpose: "no substitution at all" is a
        # hypothesis like any other (an all-transposition stack), and it should
        # win or lose on the same histogram evidence rather than by being tried
        # first out of habit.  Ordering matters here -- each candidate gets a
        # slice of the state allowance, so a wrong one tried first is states
        # the right one never gets.
        scored: list[tuple[float, str, Any]] = [
            (chi([counts[(i + shift) % 26] for i in range(26)]),
             "none" if shift == 0 else ("rot13" if shift == 13 else "caesar"), shift)
            for shift in range(26)
        ]
        scored.append((chi([counts[25 - i] for i in range(26)]), "atbash", None))
        scored.sort(key=lambda t: t[0])
        for _, name, key in scored[:keep]:
            if name == "none":
                out.append(("none", None, text))
                continue
            if name == "atbash":
                mapped = "".join(A26[25 - A26.index(c)] if c in A26 else c for c in text.upper())
            else:
                mapped = "".join(
                    A26[(A26.index(c) - int(key)) % 26] if c in A26 else c for c in text.upper()
                )
            out.append((name, key, mapped))
        return out

    def _chain_search(
        self,
        text: str,
        ctx: CrackContext,
        pool: CandidatePool,
        max_steps: int,
    ) -> None:
        """Search stacks of transpositions with one substitution underneath.

        This is the "six layers of ciphers" case, and it is tractable because
        of an algebraic fact worth stating plainly: **a transposition and a
        monoalphabetic substitution commute**.  A transposition moves letters
        without looking at them; a substitution rewrites letters without moving
        them.  So any stack of rail fences, skips, reversals, Caesars, Atbashes
        and ROT13s -- in any order, however deep -- equals *one* permutation
        followed by *one* substitution.

        Two consequences, and the search is built on both:

        1. The substitution can be solved **first**, from the ciphertext's
           letter histogram, because no transposition changes it
           (:meth:`_monoalphabetic_candidates`).  It is then applied to the
           whole text once, and what remains is a pure permutation problem.
        2. Each state therefore costs a single quadgram scoring rather than a
           re-analysis, so tens of thousands of compositions per second are
           affordable and the depth that matters is reachable:

           ==========  ==================  =========================
           chain depth  compositions       what it covers
           ==========  ==================  =========================
           1                        13     one transposition + a shift
           2                       182     two + a shift
           3                     2,380     three + a shift
           4                    30,927     four + a shift
           ==========  ==================  =========================

        Deduplication keeps those numbers honest -- different stacks often
        compose to the same permutation (two reversals are the identity) and
        every state is fingerprinted -- and the cap is set from the time left,
        so a bigger budget searches deeper instead of the search overrunning.

        What this deliberately does *not* do is chase six stacked
        polyalphabetics.  Nothing commutes there, every intermediate state is
        indistinguishable from noise, and no test exists to prune the tree; that
        limit is real and is documented rather than papered over.
        """
        from .ciphers import try_get

        transforms: list[tuple[str, Any, Any]] = []
        for name, keys in (
            ("reverse", [None]),
            ("rail_fence", [(rails, 0) for rails in range(2, 7)]),
            ("skip", list(range(2, 9))),
        ):
            cipher = try_get(name)
            if cipher is None:
                continue
            for key in keys:
                transforms.append((name, key, cipher))

        # States are cheap but not free; spend a slice of what is left rather
        # than a fixed number, so a 5-second run stays quick and a 5-minute one
        # searches a level deeper.
        allowance = min(
            CHAIN_STATE_CAP,
            int(max(0.0, ctx.remaining()) * CHAIN_SHARE * CHAIN_STATES_PER_SECOND),
        )
        if allowance < len(transforms):
            return

        candidates = self._monoalphabetic_candidates(text, ctx)
        # Split the allowance rather than letting the first candidate spend it
        # all: the histogram usually ranks the true substitution first, but
        # "usually" is not "always", and a wrong guess must not be able to
        # starve the right one.
        rest = max(1, len(candidates) - 1)
        for index, (sub_name, sub_key, base) in enumerate(candidates):
            if ctx.expired() or pool.certain or allowance <= 0:
                return
            fraction = CHAIN_FIRST_SHARE if index == 0 else (1 - CHAIN_FIRST_SHARE) / rest
            budget_states = min(allowance, max(len(transforms) * 2, int(allowance * fraction)))
            allowance -= budget_states
            seen: set[str] = {fingerprint(base)}
            frontier: list[tuple[str, tuple[tuple[str, Any], ...]]] = [(base, ())]
            # Breadth first, so the shallowest explanation wins: a two-step
            # chain is a better answer than a six-step chain reaching the same
            # plaintext, and likelier to be what the puzzle actually did.
            for _ in range(max_steps):
                if not frontier or ctx.expired() or pool.certain or budget_states <= 0:
                    break
                nxt: list[tuple[str, tuple[tuple[str, Any], ...]]] = []
                for body, chain in frontier:
                    for name, key, cipher in transforms:
                        if budget_states <= 0 or ctx.expired() or pool.certain:
                            break
                        try:
                            inner = cipher.decrypt(body) if key is None else cipher.decrypt(body, key)
                        except Exception:
                            continue
                        fp = fingerprint(inner)
                        if fp in seen:
                            continue
                        seen.add(fp)
                        budget_states -= 1
                        steps = chain + ((name, key),)
                        nxt.append((inner, steps))
                        # Two-stage scoring.  `score()` segments the text into
                        # dictionary words, which is the honest measure and far
                        # too slow to run on a quarter of a million states;
                        # n-gram fitness alone is a fifth of the cost and never
                        # rates real English below the gate (English averages
                        # -4.3 per character, random text -7.7).
                        if ctx.model.search_fitness(inner[:CHAIN_GATE_CHARS]) < CHAIN_FITNESS_GATE:
                            continue
                        if self.model.score(inner).confidence < SOLVED_CONFIDENCE:
                            continue
                        # Prefix the chain this node was already inside: the
                        # search runs under peeled encodings too, and a report
                        # that says `reverse -> rail_fence -> caesar` for a
                        # base64-wrapped puzzle has lost two real steps.
                        named = ctx.steps + tuple(step for step, _ in steps)
                        if sub_name == "none":
                            # An all-transposition stack: the last step is the
                            # one that gets the credit and the key.
                            self._say(f"chain found: {' -> '.join(named)}", 0.95, cipher=named[-1])
                            pool.add(ctx.with_steps(named[:-1]).candidate(
                                named[-1], inner, key, steps=named[:-1],
                                method="chain search (composed transpositions)",
                            ))
                        else:
                            self._say(
                                f"chain found: {' -> '.join(named)} -> {sub_name}",
                                0.95,
                                cipher=sub_name,
                            )
                            pool.add(ctx.with_steps(named).candidate(
                                sub_name, inner, sub_key, steps=named,
                                method=(
                                    "chain search: the substitution was read off the letter "
                                    "histogram, which transpositions leave untouched, then the "
                                    "permutation stack was composed"
                                ),
                            ))
                        if pool.certain:
                            return
                frontier = nxt

    def _recurse_candidates(
        self,
        produced: list[Candidate],
        ctx: CrackContext,
        depth: int,
        pool: CandidatePool,
        report: CrackReport,
        cipher_depth: int = 0,
        only: frozenset[str] | None = None,
        child_mode: str = "bounded",
        limit: int = 8,
    ) -> None:
        """Explore the output of structure-changing ciphers as new nodes.

        Only the best few candidates are followed, and only when they are not
        already readable -- a transposition that produced English has answered
        the question, and re-attacking it would just rediscover the same text
        under a no-op cipher.
        """
        # Ranking by confidence is exactly wrong here: the output of the
        # middle step of a stack is *meant* to look like nonsense, so the
        # candidate worth following is usually at the bottom of the pool.  Take
        # the best attempt from each recursive cipher at this node instead, and
        # order them by the cipher's own fitness rather than by how English
        # they read.
        if cipher_depth >= MAX_CIPHER_UNWRAPS:
            return
        cheap_pass = child_mode == "cheap"
        if cheap_pass:
            if self._cheap_cipher_nodes >= MAX_CHEAP_CIPHER_NODES:
                return
        elif self._cipher_nodes >= MAX_CIPHER_NODES:
            return

        by_cipher: dict[str, list[Candidate]] = {}
        for candidate in produced:
            if candidate.cipher not in (only or RECURSIVE_CIPHERS):
                continue
            # Following the same cipher twice in one chain is how you get
            # `reverse -> reverse` (the identity) reported as a two-step
            # solution.  Two stacked transpositions of the same kind are also
            # almost always expressible as one, so the second step buys freedom
            # rather than explanation.
            if candidate.cipher in ctx.steps:
                continue
            by_cipher.setdefault(candidate.cipher, []).append(candidate)

        shortlist: list[Candidate] = []
        for name, candidates in by_cipher.items():
            candidates.sort(key=lambda c: -c.fitness)
            keep = AMBIGUOUS_FOLLOW if name in AMBIGUOUS_RECURSIVE else 1
            if cheap_pass:
                keep = max(keep, 12)  # every reading; each is nearly free
            shortlist.extend(candidates[:keep])

        # Order: the keyless structural ciphers first.  Their output is exact
        # rather than a guess, they cost nothing to follow, and `reverse` in
        # particular is the most common wrapper in puzzle stacks -- ranking it
        # by how English its output reads would drop it, because its output is
        # *meant* to still be enciphered.
        def rank(candidate: Candidate) -> tuple[int, float]:
            exact = candidate.cipher in EXACT_RECURSIVE
            return (0 if exact else 1, -candidate.fitness)

        followed = 0
        for candidate in sorted(shortlist, key=rank):
            if followed >= limit or ctx.expired() or pool.certain:
                return
            body = candidate.plaintext
            letters = letters_only(body)
            if len(letters) < 16:
                continue
            if self.model.score(body).confidence >= SOLVED_CONFIDENCE:
                continue  # already readable: nothing left underneath
            # Revisit a text only when this pass may do more with it than
            # the pass that saw it first: the cheap pass deliberately leaves
            # Vigenere and friends untried.
            fp = fingerprint(body)
            rank = MODE_RANK[child_mode]
            if self._explored.get(fp, -1) >= rank:
                continue
            self._explored[fp] = rank
            followed += 1
            if cheap_pass:
                self._cheap_cipher_nodes += 1
            else:
                self._cipher_nodes += 1
            self._say(
                f"exploring the {candidate.cipher} result as a cipher in its own right",
                0.75,
                cipher=candidate.cipher,
            )
            chain = tuple(candidate.steps) + (candidate.cipher,)
            share = max(1.0, ctx.remaining() * layer_share(depth) * 0.4)
            if candidate.cipher in AMBIGUOUS_RECURSIVE:
                share = min(share, AMBIGUOUS_CHILD_SECONDS)
            child = ctx.with_steps(chain, budget=share, depth=depth + 1)
            self._explore(
                body, child, depth + 1, pool, report,
                mode=child_mode, cipher_depth=cipher_depth + 1,
            )

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
        # A cipher's own detector is useful but partisan: several of them
        # return near-certainty for any letters-only English-shaped text, and
        # letting those values compete at face value flattens the identifier's
        # ranking into a tie, which costs the attack the identifier actually
        # pointed at.  So a self-assessment is damped, and can never outrank
        # the best hypothesis the identifier arrived at from the text alone.
        ceiling = max(likelihoods.values(), default=1.0) * 0.99
        for cipher in self.ciphers:
            try:
                own = cipher.likelihood(text, ctx)
            except Exception:
                continue
            if not own:
                continue
            value = min(own * SELF_ASSESSMENT_WEIGHT, ceiling)
            if value > blended.get(cipher.info.name, 0.0):
                blended[cipher.info.name] = value
        # Ciphers that can produce the *same* plaintext share their evidence.
        # Nothing distinguishes a 13-shift read as ROT13 from one read as a
        # Caesar, so whichever of them scores higher must not decide which
        # name the user is given: the search stops at the first certain
        # answer, so the loser of that race never even runs.  Levelling the
        # group lets the tie break on Candidate.EQUIVALENT_CIPHER_RANK, which
        # prefers the specific name.
        for group in Candidate.EQUIVALENT_GROUPS:
            present = [name for name in group if name in blended]
            if len(present) > 1:
                shared = max(blended[name] for name in present)
                for name in present:
                    blended[name] = shared
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
        likelihood: float = 0.0,
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
        # Budget follows evidence here as it does in the attack phases.  A
        # layer the identifier is 92% sure about should not be handed the same
        # 60% of the clock as one it half believes: the leftover is for
        # readings that are probably wrong, and starving the likely branch is
        # how a keyed Polybius (peel, then a substitution search underneath)
        # ends up losing to a base64 reading of the same digits.
        share = min(0.92, layer_share(depth) + 0.3 * max(0.0, min(1.0, likelihood)))
        child = ctx.child(
            budget=max(1.0, ctx.remaining() * share),
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
        sink: list[Candidate] | None = None,
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
            # Time within a phase is shared out in proportion to how likely
            # each cipher is, not equally.  An equal split sounds fair and is
            # not: adding ten ciphers to the collection would silently take
            # time away from the substitution hill climb that was going to
            # solve the puzzle, and a keyed Polybius (which is a Polybius
            # peel followed by a substitution search) would stop coming out.
            # The floor keeps every cipher in the running, because a
            # misidentification must never cost the user their plaintext.
            weights = [max(LIKELIHOOD_FLOOR, likelihoods.get(c.info.name, 0.0)) for c in group]
            self._likelihood_floor = likelihoods
            for index, cipher in enumerate(group):
                if ctx.expired() or pool.certain:
                    return
                share = weights[index] / sum(weights[index:])
                self._run(cipher, text, letters, ctx, pool, report, cost, share, sink)

    def _run(
        self,
        cipher: Cipher,
        text: str,
        letters: str,
        ctx: CrackContext,
        pool: CandidatePool,
        report: CrackReport,
        cost: float,
        share: float,
        sink: list[Candidate] | None = None,
    ) -> None:
        prepared = cipher.prepare(text)
        alphabet = cipher.info.alphabet
        usable = prepared if alphabet is None else prepared
        if len(usable) < max(cipher.info.min_length, 2) and not ctx.exhaustive:
            return
        # An attack gets a bounded share of the time still available at *this*
        # node.  The previous two-second floor could turn a 0.5-second request
        # into several expensive sub-contexts; each child inherited the root
        # deadline, but process-backed attacks could still finish after the user
        # had asked us to stop.  A slice is a cap, never a promise of a minimum.
        remaining = ctx.remaining()
        if remaining <= 0:
            return
        if cost >= EXPENSIVE:
            slice_seconds = min(PHASE_SLICES[cost], remaining * max(0.0, min(1.0, share)))
        else:
            slice_seconds = min(PHASE_SLICES[cost], remaining)
        # Proportional sharing starves the last phase: by the time the BRUTAL
        # group is reached the remainder has been divided so many ways that
        # each attack is offered zero seconds, and a zero-second attack cannot
        # find anything however well the evidence points at it.  An M-94
        # ciphertext that the cipher's own search cracks in six seconds was
        # being missed for exactly this reason, with budget still unspent.
        # So: when the identifier likes a cipher, it gets a workable slice
        # rather than its arithmetic share of what is left.
        evidence = self._likelihood_floor.get(cipher.info.name, 0.0)
        if (
            cost >= EXPENSIVE                       # only the proportional phases starve
            and evidence >= WELL_EVIDENCED
            and slice_seconds < MIN_VIABLE_SLICE
        ):
            slice_seconds = min(MIN_VIABLE_SLICE, remaining)
        if slice_seconds <= 0:
            return
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
                if sink is not None:
                    sink.append(candidate)
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
            self._note_language(report)
        self._say(
            f"{'solved' if report.solved else 'best effort'} in {report.elapsed:.2f}s "
            f"({len(report.attacks)} attacks, confidence {report.confidence:.2f})",
            1.0,
        )
        return report

    def _note_language(self, report: CrackReport) -> None:
        """Flag a plaintext that reads better under another shipped model.

        The English model happily *solves* French or Italian text -- the
        languages share enough n-grams that a solve under the wrong model is
        still the right plaintext -- but it cannot respell the words or
        honestly say how confident it is.  Ranking the winning plaintext
        under every model costs one scoring pass and tells the user which
        ``--language`` would have been the right call.
        """
        best = report.best
        if best is None or len(letters_only(best.plaintext)) < 40:
            return
        ranked = detect_language(best.plaintext, limit=2)
        if not ranked:
            return
        language, confidence = ranked[0]
        if language == self.model.language:
            return
        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
        if confidence - runner_up < 0.015 or confidence < 0.55:
            return  # too close to call, or nothing reads like language at all
        best.notes["language"] = (
            f"plaintext reads as {language.capitalize()} "
            f"(confidence {confidence:.2f}); rerun with --language {language} "
            f"for honest scoring and word respacing"
        )
        report.language_detected = language

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
    max_depth: int = 6,
    hints: dict[str, Any] | None = None,
    progress: Callable[[str, float, dict], None] | None = None,
    model: LanguageModel | None = None,
    exhaustive: bool = False,
    language: str = "english",
) -> CrackReport:
    """Convenience wrapper around :class:`Solver`.

    ``language`` names one of the shipped plaintext models (see
    :data:`buttcrack.lang.LANGUAGES`) and is ignored when ``model`` is given.
    Use :func:`solve_auto` to detect the language instead.
    """
    return Solver(
        budget=budget,
        workers=workers,
        max_depth=max_depth,
        model=model,
        hints=hints,
        progress=progress,
        exhaustive=exhaustive,
        language=language,
    ).solve(ciphertext)


def solve_auto(
    ciphertext: str,
    *,
    budget: float = 30.0,
    workers: int = 1,
    max_depth: int = 6,
    hints: dict[str, Any] | None = None,
    progress: Callable[[str, float, dict], None] | None = None,
    exhaustive: bool = False,
) -> CrackReport:
    """Solve under every shipped language model, picking the best fit.

    Ciphertext does not carry a language signal, so detection has to ride on
    *solving*: each model gets a short probe of the budget, and whichever
    probe reads the most language gets the remainder.  Cheap ciphers (Caesar,
    substitution, ...) usually solve outright inside their probe, so the
    early exit fires and the whole thing costs one short solve; the expensive
    ciphers are probed by how much their best *partial* reading likes the
    text, which tracks the language well once 60-odd letters are decrypted.

    Probing is capped at half the budget so an ambiguous text still gets a
    full-strength solve, and English is probed first so the common case --
    English after all -- pays for exactly one probe.
    """
    started = time.time()
    order = ["english"] + [name for name in LANGUAGES if name != "english"]
    probe_budget = max(1.0, min(4.0, budget / 12.0))
    cap = budget * 0.5
    probes: dict[str, CrackReport] = {}
    say = progress or (lambda *_: None)
    for language in order:
        if time.time() - started >= cap and probes:
            break
        say(f"probing {language}", (time.time() - started) / max(budget, 0.001), {"language": language})
        probes[language] = solve(
            ciphertext,
            budget=probe_budget,
            workers=workers,
            max_depth=max_depth,
            hints=hints,
            progress=None,
            exhaustive=exhaustive,
            language=language,
        )
        if probes[language].solved:
            report = probes[language]
            # A solve under the wrong model still yields the right plaintext,
            # but its confidence and word spacing are dishonest.  If the
            # plaintext clearly reads as another shipped language, spend one
            # more probe there and prefer that solve when it lands.
            detected = report.language_detected
            if detected and detected != language and detected in LANGUAGES:
                say(f"re-probing {detected}", (time.time() - started) / max(budget, 0.001), {})
                foreign = solve(
                    ciphertext,
                    budget=probe_budget,
                    workers=workers,
                    max_depth=max_depth,
                    hints=hints,
                    progress=None,
                    exhaustive=exhaustive,
                    language=detected,
                )
                if foreign.solved:
                    foreign.budget = budget
                    return foreign
                report.language_detected = detected
            report.budget = budget  # the answer stands for the whole budget
            return report
    # No probe solved outright: hand the rest of the budget to whichever
    # language read the most text so far.  Rank by best confidence, then by
    # how much was found at all -- a probe that produced nothing scores below
    # one that produced a partial reading.
    def probe_rank(language: str) -> tuple[float, float]:
        report = probes[language]
        return (report.confidence, 1.0 if report.best else 0.0)

    best_language = max(probes, key=probe_rank)
    remaining = budget - (time.time() - started)
    say(f"probes favour {best_language}", (time.time() - started) / max(budget, 0.001), {})
    return solve(
        ciphertext,
        budget=max(remaining, probe_budget),
        workers=workers,
        max_depth=max_depth,
        hints=hints,
        progress=progress,
        exhaustive=exhaustive,
        language=best_language,
    )
