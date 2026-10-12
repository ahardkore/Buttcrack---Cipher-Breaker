"""Search infrastructure shared by the stochastic attacks.

Substitution, Playfair and Bifid all have keyspaces far too large to enumerate
(26!, 25!, ...) and are solved by hill climbing on quadgram fitness with random
restarts.  This module holds the machinery those three share:

* :func:`restart_search` -- run N independent climbs, keep the global best, stop
  early as soon as a climb produces plaintext the language model is *certain*
  about, and never overrun the deadline;
* :func:`parallel_restarts` -- spread restarts across processes, choosing
  whichever start method the platform actually has: ``fork`` where it exists,
  where the already-loaded language model is inherited copy-on-write instead of
  being re-read in every worker, and ``spawn`` everywhere else -- Windows
  included -- so that the expensive attacks use every core there too.
"""

from __future__ import annotations

import multiprocessing
import os
import random
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from .lang import CERTAIN_CONFIDENCE
from .text import A26


@dataclass
class SearchResult:
    """Outcome of one climb."""

    key: Any
    plaintext: str
    fitness: float
    confidence: float
    evaluations: int
    restarts: int


def _default_workers(requested: int | None) -> int:
    if requested and requested > 0:
        return requested
    try:
        cpus = len(os.sched_getaffinity(0))
    except AttributeError:  # pragma: no cover - non-Linux
        cpus = os.cpu_count() or 1
    return max(1, min(cpus, 4))


def start_method() -> str | None:
    """The cheapest way this platform can start a worker process.

    ``fork`` gets first refusal everywhere it exists, because a forked worker
    inherits the parent's loaded language model copy-on-write and starting one
    therefore costs nothing measurable.  Windows has no ``fork``, and neither do
    some containers and embedded interpreters; there ``spawn`` is the difference
    between using every core and using one.

    Spawn is not free -- each worker re-imports the package and re-reads the
    n-gram tables, about 0.25 s -- but that is paid once per worker, in
    parallel, against a budget that defaults to 30 s.  A four-core machine
    finishes a substitution climb roughly four times sooner.

    ``forkserver`` is skipped on purpose.  It exists to make ``fork`` safe in
    the presence of threads, and its workers fork from a clean server, so it
    would pay spawn's reload cost without spawn's portability.

    Returns ``None`` when this interpreter offers neither, which tells
    :func:`parallel_restarts` to stay in-process.
    """
    try:
        methods = multiprocessing.get_all_start_methods()
    except Exception:  # pragma: no cover - trimmed-down multiprocessing
        return None
    for name in ("fork", "spawn"):
        if name in methods:
            return name
    return None


def _serial(worker: Callable[[tuple], tuple], payloads: Sequence[tuple], deadline: float | None) -> list[tuple]:
    """Run every payload in this process, stopping at the deadline."""
    results: list[tuple] = []
    for payload in payloads:
        if deadline is not None and time.time() >= deadline:
            break
        result = worker(payload)
        if result:
            results.append(result)
    return results


#: What a spawned pool charges before any of its workers can compute.
#:
#: Measured rather than guessed, on the batch that exposed this: the same
#: two-payload substitution climb returned 0.30 s after submission through
#: ``fork`` and 1.06-1.14 s through ``spawn``.  The difference is a fresh
#: interpreter importing the package and re-reading the n-gram tables in every
#: worker, and it is a cost the *engine* chose to take on -- so the engine
#: absorbs it rather than charging it to the caller's search budget.  See
#: :func:`parallel_restarts`.
SPAWN_STARTUP = 1.0


def parallel_restarts(
    worker: Callable[[tuple], tuple],
    payloads: Sequence[tuple],
    workers: int,
    deadline: float | None = None,
) -> list[tuple]:
    """Map ``worker`` over ``payloads``, in parallel when it is worth it.

    Results are collected as they complete, so an expiring time slice keeps the
    climbs that *did* finish instead of discarding the batch -- and instead of
    starting again serially, which cannot beat the clock and doubles the work.

    The deadline stops new work from being *started*; it does not cancel work
    already running.  A batch submitted inside the budget therefore keeps
    listening for :data:`SPAWN_STARTUP` seconds past it, because the alternative
    is worse than a fraction of a second: a batch issued just before the bell
    was the whole point of spending that part of the budget, and dropping it
    discards the only result available.  Windows is where this bites -- every
    spawned worker boots an interpreter and re-reads the n-gram tables before it
    can compute at all, so its batch returns just after the bell while the
    identical batch under ``fork`` returns just before it.

    A pool started *after* the deadline gets no such latitude: that budget is
    spent, and the caller's cap is what keeps a search responsive.  Because the
    clock is re-read on every call, at most one batch per search gets the extra
    window -- a cascade whose stages keep issuing pools will find the deadline
    already behind it and be cut off immediately, as it should be.

    Falls back to a serial loop when no pool can be created at all: a solver
    with no usable start method (a restricted container, a web request thread)
    must still produce an answer.
    """
    if workers <= 1 or len(payloads) <= 1:
        return _serial(worker, payloads, deadline)

    submitted = time.time()
    method = start_method()
    if deadline is not None and method == "spawn" and deadline - submitted <= SPAWN_STARTUP:
        # A spawned pool cannot compute inside a slice this short: booting the
        # interpreters alone costs more than the slice has left, so the workers
        # would finish after the bell and -- before this -- their answers were
        # thrown away, turning a solvable puzzle into an unsolved one.  Doing
        # the work here is not merely cheaper than starting a pool that cannot
        # pay for itself; it is faster than a pool that *can*, because there is
        # no boot to pay for.  Measured, on the batch that exposed this: two
        # substitution climbs cost 0.21 s each in this process and 1.06-1.14 s
        # through ``spawn``.
        return _serial(worker, payloads, deadline)

    #: ``None`` means "no deadline"; a time in the past means "no waiting".
    collect_until = deadline
    if deadline is not None and submitted < deadline and method == "spawn":
        collect_until = deadline + SPAWN_STARTUP
    results: list[tuple] = []
    if method is not None:
        try:
            ctx = multiprocessing.get_context(method)
            with ctx.Pool(processes=min(workers, len(payloads))) as pool:
                pending = [pool.apply_async(worker, (payload,)) for payload in payloads]
                while pending:
                    # Drain first, then decide whether to keep waiting: checking
                    # the clock before looking at the handles threw away climbs
                    # that had already finished, which is the bug this exists to
                    # prevent.
                    running = []
                    for handle in pending:
                        if not handle.ready():
                            running.append(handle)
                            continue
                        try:
                            result = handle.get()
                        except Exception:  # a worker died; keep what the others found
                            continue
                        if result:
                            results.append(result)
                    pending = running
                    if not pending:
                        break
                    if collect_until is not None and time.time() >= collect_until:
                        break
                    time.sleep(0.005)
        except Exception:
            results = []
    if results:
        return results
    # A process pool can fail before producing a result, in which case serial is
    # a useful compatibility fallback.  It is not useful after the deadline:
    # starting a fresh stochastic climb there both violates the caller's budget
    # and guarantees that the answer arrives too late to use.
    if deadline is not None and time.time() >= deadline:
        return results
    return _serial(worker, payloads, deadline)


def frequency_seed(ciphertext: str) -> list[str]:
    """Seed key: map the most common ciphertext letter to E, and so on.

    A frequency-ordered start is the single best heuristic for substitution: on
    long texts the very first climb from this seed usually lands near the truth,
    which is why restart 0 uses it and later restarts are random.
    """
    from collections import Counter

    counts = Counter(c for c in ciphertext if c in A26)
    english_order = "ETAOINSHRDLCUMWFGYPBVKJXQZ"
    by_freq = [c for c, _ in counts.most_common()]
    by_freq += [c for c in A26 if c not in counts]
    key = list(A26)
    for cipher_letter, plain_letter in zip(by_freq, english_order):
        key[A26.index(cipher_letter)] = plain_letter
    return key


def swap(key: list[str], i: int, j: int) -> list[str]:
    out = list(key)
    out[i], out[j] = out[j], out[i]
    return out


def climb(
    ciphertext: str,
    fitness: Callable[[str], float],
    *,
    rng: random.Random,
    start: list[str] | None = None,
    alphabet: str = A26,
    max_evals: int = 4000,
    deadline: float | None = None,
    apply_key: Callable[[str, list[str]], str] | None = None,
) -> tuple[list[str], float, int]:
    """First-improvement hill climbing over pairwise swaps of the key.

    Returns ``(key, fitness, evaluations)``.  The pair order is reshuffled after
    every accepted move, which reaches local optima in far fewer evaluations
    than steepest-ascent scanning all 325 pairs each pass.
    """
    n = len(alphabet)
    apply_key = apply_key or (lambda text, key: text.translate(str.maketrans(alphabet, "".join(key))))
    key = list(start) if start else [alphabet[i] for i in range(n)]
    if start is None:
        rng.shuffle(key)
    current = fitness(apply_key(ciphertext, key))
    evals = 1
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    while evals < max_evals:
        if deadline is not None and evals % 256 == 0 and time.time() >= deadline:
            break
        rng.shuffle(pairs)
        improved = False
        for i, j in pairs:
            candidate = swap(key, i, j)
            value = fitness(apply_key(ciphertext, candidate))
            evals += 1
            if value > current + 1e-12:
                key, current, improved = candidate, value, True
                break
            if evals >= max_evals:
                break
        if not improved:
            break
    return key, current, evals


def restart_search(
    ciphertext: str,
    *,
    fitness: Callable[[str], float],
    confidence: Callable[[str], float],
    apply_key: Callable[[str, list[str]], str],
    restarts: int,
    rng: random.Random,
    deadline: float | None = None,
    max_evals: int = 4000,
    alphabet: str = A26,
    seeds: Iterable[list[str]] = (),
) -> tuple[list[str], str, float, float, int, int]:
    """Run climbs until the budget, the deadline or certainty runs out.

    Returns ``(best_key, best_plaintext, best_fitness, best_confidence,
    total_evaluations, restarts_used)``.
    """
    best_key: list[str] | None = None
    best_plain = ""
    best_fit = float("-inf")
    best_conf = 0.0
    evals = 0
    used = 0
    seed_list = list(seeds)
    for r in range(restarts):
        # Always take at least one shot, deadline or not.  Restart 0 is the
        # frequency-seeded (or otherwise best-guess) climb and is far the most
        # likely to land; returning nothing because a time slice expired while
        # an earlier attack overran is the worst possible outcome.  It is bounded
        # by ``max_evals``, so the overrun is a fraction of a second.
        if r and deadline is not None and time.time() >= deadline:
            break
        start = seed_list[r] if r < len(seed_list) else None
        key, fit, n_evals = climb(
            ciphertext,
            fitness,
            rng=rng,
            start=start,
            alphabet=alphabet,
            max_evals=max_evals,
            deadline=None if r == 0 else deadline,
            apply_key=apply_key,
        )
        evals += n_evals
        used = r + 1
        if fit > best_fit:
            best_key, best_fit = key, fit
            best_plain = apply_key(ciphertext, key)
            best_conf = confidence(best_plain)
            if best_conf >= CERTAIN_CONFIDENCE:
                break
    if best_key is None:
        best_key = list(alphabet)
        best_plain = apply_key(ciphertext, best_key)
    return best_key, best_plain, best_fit, best_conf, evals, used


def restarts_for(length: int, *, base: int = 12, minimum: int = 4, maximum: int = 64) -> int:
    """Shorter texts have flatter fitness landscapes and need more restarts.

    Measured behaviour on this model: 600+ letters converges in a handful of
    restarts, 200 letters needs a few dozen, and below ~120 letters the correct
    key is often not the global optimum at all (see README "limits").
    """
    if length >= 600:
        return max(minimum, base // 2)
    if length >= 300:
        return base
    if length >= 150:
        return min(maximum, base * 3)
    return maximum
