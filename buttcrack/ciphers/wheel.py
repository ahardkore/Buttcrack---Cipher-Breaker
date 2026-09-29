"""The M-94 wheel cipher: 25 mixed alphabets on a spindle.

The M-94 (US Army 1922-1943, Navy CSP-488) is Parker Hitt's strip-cipher idea
as Major Joseph Mauborgne built it: 25 disks, each carrying a different
scrambled alphabet around its rim, threaded on a spindle in a secret order.
The sender rotates the disks to spell the plaintext along one row and reads
the ciphertext off a different row; the receiver sets the same disk order,
aligns the ciphertext, and reads the plaintext row back.  Each plaintext
position is enciphered through *its own disk's* mixed alphabet, so the cipher
is polyalphabetic with a period of exactly 25 -- but unlike a Vigenere, each
column of the period is a full mixed alphabet rather than a shift.

The disk alphabets are public (they were engraved on every device Mauborgne's
manufacturers turned out); the secret is the *order* of the 25 disks on the
spindle -- ``log2(25!)`` ~ 83 bits -- plus which row the sender read from.
Both are recovered here by hill climbing over pairwise disk swaps, scoring
each candidate order by its best read-out row (see :func:`_search_reading`
for how that stays cheap).  The attack lands from roughly 200 letters of
ciphertext on the shipped English model, which matches the classical result:
Friedman's team read M-94 traffic once enough message material accumulated,
and short single messages stayed safe.

The disk set in ``data/m94_disks.txt`` is the standard 25-disk Mauborgne set;
each disk is identified by the letter that follows its ``A`` (disks ``B``
through ``Z``), which is also how key orders are written down.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..lang import CERTAIN_CONFIDENCE, get_model
from ..results import Candidate
from ..search import parallel_restarts
from ..text import ic_of_columns, index_of_coincidence, letters_only
from .base import BRUTAL, Cipher, CipherInfo, CrackContext, Family

#: The 25 disk alphabets, in file order: disk ``i`` is identified by the
#: letter that follows its ``A``, which for the standard set runs ``B, C ... Z``.
#: Loaded once per process; fork-based workers inherit the parsed tables
#: copy-on-write.
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "m94_disks.txt"
DISK_IDS = "BCDEFGHIJKLMNOPQRSTUVWXYZ"

_DISKS: list[str] | None = None


def disks() -> list[str]:
    """The 25 standard M-94 disk alphabets, each a permutation of A-Z."""
    global _DISKS
    if _DISKS is None:
        alphabets = []
        for line in DATA_PATH.read_text(encoding="ascii").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if len(line) != 26 or len(set(line)) != 26:
                raise ValueError(f"bad M-94 disk alphabet in {DATA_PATH}: {line!r}")
            alphabets.append(line)
        if len(alphabets) != 25:
            raise ValueError(f"expected 25 M-94 disks in {DATA_PATH}, found {len(alphabets)}")
        _DISKS = alphabets
    return _DISKS


def _decode_rows() -> list[list[str]]:
    """``rows[disk][read_row]`` -- a 26-entry cipher->plain mapping as a string.

    Building all 25 x 26 rows costs well under a millisecond once per process;
    every decryption afterwards is pure indexing.
    """
    if not hasattr(_decode_rows, "cache"):
        rows = []
        for alphabet in disks():
            per_row = []
            for read_row in range(26):
                table = [""] * 26
                for position, letter in enumerate(alphabet):
                    table[ord(letter) - 65] = alphabet[(position - read_row) % 26]
                per_row.append("".join(table))
            rows.append(per_row)
        _decode_rows.cache = rows
    return _decode_rows.cache


def _disk_index(disk_id: str) -> int:
    index = DISK_IDS.find(disk_id)
    if index < 0:
        raise ValueError(f"M-94 disk ids are the letters {DISK_IDS}, got {disk_id!r}")
    return index


def parse_key(key: Any) -> tuple[str, int]:
    """Normalise an M-94 key to ``(order, read_row)``.

    The order is 25 disk letters (``B``-``Z``, each used once) in spindle
    order; a list of disk *numbers* 1-25 is accepted as the equivalent
    ``1 5 3 ...`` notation.  ``read_row`` says which row the sender read the
    ciphertext from (0-25); it defaults to 1 for encryption when not given,
    and is recovered from the text by the solver.
    """
    row = 1
    if isinstance(key, dict):
        row = int(key.get("row", 1))
        key = key.get("order", key.get("key"))
    if isinstance(key, (list, tuple)):
        parts = [str(v) for v in key]
        if all(p.strip().isdigit() for p in parts if p.strip()):
            numbers = [int(p) for p in parts if p.strip()]
            if sorted(numbers) != list(range(1, 26)):
                raise ValueError("a numbered M-94 key is a permutation of 1..25")
            order = "".join(DISK_IDS[n - 1] for n in numbers)
        else:
            order = "".join(str(v) for v in parts)
    else:
        text = str(key).strip()
        parts = text.replace(",", " ").split()
        if len(parts) >= 2 and all(p.isdigit() and 1 <= int(p) <= 25 for p in parts):
            numbers = [int(p) for p in parts]
            if sorted(numbers) != list(range(1, 26)):
                raise ValueError("a numbered M-94 key is a permutation of 1..25")
            order = "".join(DISK_IDS[n - 1] for n in numbers)
        else:
            order = text.replace(",", "").replace(" ", "").upper()
    if len(order) != 25 or len(set(order)) != 25 or any(ch not in DISK_IDS for ch in order):
        raise ValueError(
            f"an M-94 order is 25 distinct disk letters from {DISK_IDS} (or numbers 1-25), got {key!r}"
        )
    if not 0 <= row < 26:
        raise ValueError(f"read row must be 0-25, got {row}")
    return order, row


def _apply(stream: str, order: str, read_row: int) -> str:
    """Decrypt ``stream`` given a disk order and the row it was read from."""
    rows = _decode_rows()
    out = []
    for i, ch in enumerate(stream):
        out.append(rows[_disk_index(order[i % 25])][read_row][ord(ch) - 65])
    return "".join(out)


def best_reading(stream: str, order: str, model, cap: int = 400) -> tuple[float, int, str]:
    """``(fitness, read_row, plaintext)`` for the best of the 26 read rows.

    The row is part of the key but constant across the whole message, so
    trying all 26 costs one cheap pass each and adds real evidence: only the
    true order has *some* row that reads as language throughout.  Used for
    final candidates, where exactness matters more than speed.
    """
    rows = _decode_rows()
    best = (-99.0, 0, "")
    for row in range(26):
        text = stream[:cap]
        plain = "".join(
            rows[_disk_index(order[i % 25])][row][ord(ch) - 65] for i, ch in enumerate(text)
        )
        value = model.search_fitness(plain)
        if value > best[0]:
            best = (value, row, plain)
    return best


def _search_reading(stream: str, order: list[int], model, keep: int = 3, prefix: int = 60) -> float:
    """Fitness of the best read row, prefiltered -- the climb's inner score.

    Scoring a candidate order exactly means decrypting and scoring all 26
    read rows (~2.2 ms measured); the climb needs thousands of those.  But the
    true row already stands out on a 60-letter prefix, so: score all rows on
    the prefix, then fully score only the best ``keep``.  Measured 0.7 ms per
    evaluation with the same answer on every order that matters (wrong orders
    pick a different wrong row -- irrelevant, they are all noise) and the
    exact best row on the true one.
    """
    rows = _decode_rows()
    head = stream[:prefix]
    ranked = []
    for row in range(26):
        plain = "".join(
            rows[order[i % 25]][row][ord(ch) - 65] for i, ch in enumerate(head)
        )
        ranked.append((model.search_fitness(plain), row))
    ranked.sort(reverse=True)
    best = -99.0
    for _, row in ranked[:keep]:
        plain = "".join(
            rows[order[i % 25]][row][ord(ch) - 65] for i, ch in enumerate(stream)
        )
        value = model.search_fitness(plain)
        if value > best:
            best = value
    return best


def _m94_climb(
    stream: str,
    model,
    rng: random.Random,
    *,
    max_evals: int = 2000,
    deadline: float | None = None,
    start: list[int] | None = None,
) -> tuple[list[int], float, int]:
    """First-improvement hill climb over pairwise wheel swaps.

    Returns ``(order, best_fitness, evaluations)``.  ``order`` indexes the
    shipped disk set; the read row is chosen implicitly by the fitness
    evaluation, so it tracks the order search for free.
    """
    order = list(start) if start is not None else list(range(25))
    if start is None:
        rng.shuffle(order)
    best = _search_reading(stream, order, model)
    evals = 1
    pairs = [(i, j) for i in range(25) for j in range(i + 1, 25)]
    while evals < max_evals:
        if deadline is not None and evals % 256 == 0 and time.time() >= deadline:
            break
        rng.shuffle(pairs)
        improved = False
        for a, b in pairs:
            order[a], order[b] = order[b], order[a]
            evals += 1
            value = _search_reading(stream, order, model)
            if value > best + 1e-9:
                best = value
                improved = True
                break
            order[a], order[b] = order[b], order[a]  # revert
            if evals >= max_evals:
                break
        if not improved:
            break
    return order, best, evals


def _m94_worker(payload: tuple) -> tuple:
    """One set of climbs in one process; returns the best ``(order, row, ...)``."""
    stream, restarts, seed, language, max_evals, deadline = payload
    model = get_model(language)
    rng = random.Random(seed)
    best: tuple | None = None
    used = 0
    evals_total = 0
    for r in range(restarts):
        # Restart 0 always runs, even past the deadline: it is bounded by
        # max_evals, and returning nothing because a shared slice expired is
        # the worst outcome for a search this expensive.
        if r and deadline is not None and time.time() >= deadline:
            break
        order, fit, evals = _m94_climb(
            stream, model, rng, max_evals=max_evals, deadline=None if r == 0 else deadline
        )
        used = r + 1
        evals_total += evals
        order_str = "".join(DISK_IDS[i] for i in order)
        # The read row is picked on the scored window (400 letters is far more
        # than the row choice ever needs), but the plaintext handed back must
        # be the *whole* message: the cap is a search cost, not a truncation.
        fitness, row, _ = best_reading(stream, order_str, model)
        plain = _apply(stream, order_str, row)
        conf = model.score(plain).confidence
        if best is None or conf > best[2]:
            best = (order_str, row, conf, fitness, plain)
        if conf >= CERTAIN_CONFIDENCE:
            break
    if best is None:
        return ()
    order_str, row, conf, fitness, plain = best
    return (order_str, row, conf, fitness, evals_total, used, plain)


class M94(Cipher):
    """M-94 / CSP-488 wheel cipher with the standard Mauborgne disk set."""

    info = CipherInfo(
        name="m94",
        title="M-94 wheel cipher",
        family=Family.WHEEL,
        key_type="wheel order (25 letters B-Z) + read row",
        keyspace=None,  # 25! ~= 1.5e25 orders times 26 read rows
        deterministic=False,
        min_length=100,
        cost=BRUTAL,
        # Underscore forms: ``get()`` normalises dashes to underscores.
        aliases=("m_94", "csp488", "csp_488", "wheel"),
        description=(
            "US Army M-94 (1922-1943): 25 mixed-alphabet wheels on a spindle, one "
            "letter per wheel. The key is the wheel order -- the alphabets themselves "
            "are the standard published set. Solved by hill climbing over wheel swaps "
            "with the read-out row recovered from the text; wants 200+ letters and a "
            "generous budget, and the honest-evidence rule caps solutions under 150 "
            "letters (25 wheels want ~6 letters each)."
        ),
        example_key={"order": "YRNCIXDULPTWFZHVMQBOKJEGS", "row": 9},
    )

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        order, read_row = parse_key(key)
        alphabets = disks()
        stream = self.prepare(plaintext)
        out = []
        for i, ch in enumerate(stream):
            alphabet = alphabets[_disk_index(order[i % 25])]
            out.append(alphabet[(alphabet.index(ch) + read_row) % 26])
        return "".join(out)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        order, read_row = parse_key(key)
        return _apply(self.prepare(ciphertext), order, read_row)

    def keys(self) -> Iterator[Any]:
        raise NotImplementedError("25! wheel orders are searched, not enumerated")

    # -- cryptanalysis ------------------------------------------------------ #
    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """Wheel ciphers look like a period-25 cipher with mixed-alphabet columns.

        Every 25th letter goes through the same disk, so for messages of two
        blocks or more the columns of a correct period-25 split are
        monoalphabetic (column IC ~ the plaintext language's) while the
        whole-text IC stays flat -- exactly the signature that separates an
        M-94 from a shifted or substituted text.  A Vigenere with a 25-letter
        key looks the same at this distance, which is fine: likelihoods only
        order attacks.
        """
        stream = letters_only(text)
        if len(stream) < 3 * 25:
            return 0.0
        if index_of_coincidence(stream) > 0.06:
            return 0.0  # monoalphabetic: no disk structure to find
        return max(0.0, min(0.9, (ic_of_columns(stream, 25) - 0.05) / 0.025))

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < max(self.info.min_length, 25) and not ctx.exhaustive:
            return
        hinted = ctx.hints.get("key")
        if hinted is not None:
            order, row = parse_key(hinted)
            if isinstance(hinted, dict) and "row" in hinted:
                plain = _apply(stream, order, row)
            else:
                # A bare order says nothing about which row the sender read
                # from; that is not part of the order, so recover it from the
                # text instead of guessing -- trying 26 rows is one cheap pass.
                row = best_reading(stream, order, ctx.model, cap=len(stream))[1]
                plain = _apply(stream, order, row)
            yield self.candidate(
                stream, plain, {"order": order, "row": row}, ctx,
                method="hinted key", columns=25,
            )
            return

        # Longer messages converge in fewer restarts (measured on the shipped
        # English model: 300+ letters usually lands within a dozen restarts,
        # 150-250 wants a couple of dozen, below that the true order is often
        # not even the fitness optimum).
        n = len(stream)
        if n >= 300:
            restarts = 12
        elif n >= 200:
            restarts = 20
        else:
            restarts = 28
        max_evals = 2500 if n >= 200 else 1500

        ctx.report(
            f"m94: hill climbing over 25! wheel orders "
            f"({ctx.workers} worker{'s' if ctx.workers > 1 else ''}, {len(stream)} letters)"
        )
        per_worker = max(1, restarts // max(1, ctx.workers))
        payloads = [
            (stream, per_worker, seed, ctx.model.language, max_evals, ctx.deadline)
            for seed in range(max(1, ctx.workers))
        ]
        started = time.time()
        results = parallel_restarts(_m94_worker, payloads, ctx.workers, ctx.deadline)
        results = [r for r in results if r]
        if not results:
            return
        # Best fitness first; a climb that ran out of budget still reports
        # what it found, and the candidate's own confidence says how much to
        # believe it.
        results.sort(key=lambda r: -r[3])
        seen: set[str] = set()
        emitted = 0
        for order, row, conf, _fitness, evals, used, plain in results:
            if order in seen:
                continue
            seen.add(order)
            notes = {
                "method": "hill climb over wheel swaps, best read row per order",
                "restarts": used,
                "evaluations": evals,
                "seconds": round(time.time() - started, 1),
            }
            if conf < 0.62:
                notes["caveat"] = (
                    "m94: the best wheel order found does not read as language; "
                    "try --budget 120, more ciphertext (200+ letters), or --hint key=<order>"
                )
            yield self.candidate(
                stream, plain, {"order": order, "row": row}, ctx,
                columns=25, **notes,
            )
            emitted += 1
            if emitted >= 3:
                return
