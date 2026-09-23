"""Search infrastructure shared by the stochastic attacks.

Substitution, Playfair and Bifid all have keyspaces far too large to enumerate
(26!, 25!, ...) and are solved by hill climbing on quadgram fitness with random
restarts.  This module holds the machinery those three share:

* :func:`restart_search` -- run N independent climbs, keep the global best, stop
  early as soon as a climb produces plaintext the language model is *certain*
  about, and never overrun the deadline;
* :func:`parallel_restarts` -- spread restarts across processes with ``fork`` so
  the already-loaded language model is inherited copy-on-write instead of being
  re-read from disk in every worker.
"""

from __future__ import annotations

import multiprocessing
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from .lang import CERTAIN_CONFIDENCE, get_model
from .results import Candidate
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

    Falls back to a serial loop when no pool can be created at all: a solver that
    cannot fork (restricted containers, spawn-only platforms, a web request
    thread) must still produce an answer.
    """
    if workers <= 1 or len(payloads) <= 1:
        return [worker(p) for p in payloads]
    results: list[tuple] = []
    try:
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(processes=min(workers, len(payloads))) as pool:
            pending = [pool.apply_async(worker, (payload,)) for payload in payloads]
            while pending:
                if deadline is not None and time.time() >= deadline:
                    break
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
                if pending:
                    time.sleep(0.005)
    except Exception:
        results = []
    if results:
        return results
    for payload in payloads:
        if deadline is not None and time.time() >= deadline and results:
            break
        result = worker(payload)
        if result:
            results.append(result)
    return results


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
