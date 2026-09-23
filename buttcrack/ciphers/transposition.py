"""Transposition ciphers: columnar, rail fence, skip (scytale) and route.

Transposition is the mirror image of substitution and needs its own detection
logic: it *preserves* the letter distribution exactly, so the index of
coincidence stays at English levels (~0.066) while the n-gram fitness collapses
(~-7.5).  "Good IC, terrible fitness" is the fingerprint, and it is why the
engine can tell transposition from polyalphabetic ciphers before spending any
search budget.

Columnar transposition is the interesting attack.  For a guessed width ``L`` the
ciphertext splits into ``L`` segments; the unknown is which grid column each
segment came from.  Rather than enumerating ``L!`` orders:

1. score every *ordered pair* of segments by the bigram statistics of the
   letters they would place side by side in a row (``seg_a[i]`` then
   ``seg_b[i]``);
2. build a path greedily from the strongest pair, extending whichever end gains
   most -- an O(L^2) approximation of the optimal ordering;
3. refine with swap hill climbing on *quadgram* fitness of the reconstruction,
   which is the metric that actually matters, from several random restarts.

Widths up to 6 are enumerated exactly instead, because 720 reconstructions cost
less than a hill climb and cannot miss.

Irregular (null) grids add one unknown -- which read positions held the longer
columns -- handled by enumerating those patterns, capped for large widths.
"""

from __future__ import annotations

import random
from itertools import combinations, permutations, product
from typing import Any, Iterator, Sequence

from ..results import Candidate
from ..text import A26, index_of_coincidence, letters_only
from .base import CHEAP, EXPENSIVE, MODERATE, Cipher, CipherInfo, CrackContext, Family

ENGLISH_IC = 0.0667
RANDOM_IC = 0.0385


def transposition_likelihood(text: str, ctx: CrackContext) -> float:
    """Shared fingerprint: English IC, destroyed n-grams."""
    stream = letters_only(text)
    if len(stream) < 20:
        return 0.0
    ic = index_of_coincidence(stream)
    ic_fit = max(0.0, min(1.0, (ic - RANDOM_IC) / (ENGLISH_IC - RANDOM_IC)))
    fit = ctx.model.ngram_score(stream)
    unreadable = max(0.0, min(1.0, (-5.0 - fit) / 2.0))
    return round(ic_fit * unreadable, 4)


def key_to_order(key: Any, width: int | None = None) -> list[int]:
    """Normalise a transposition key into a *read order*.

    The returned list satisfies ``order[r] == grid column read at position r``,
    which is the convention every function in this module uses.

    A keyword follows the classic rule -- columns are read in the order their
    key letters alphabetise, so ``ZEBRA`` reads column 4 first (A), then 2 (B),
    1 (E), 3 (R), 0 (Z).  An explicit list of ints is taken as the read order
    directly.

    >>> key_to_order("ZEBRA")
    [4, 2, 1, 3, 0]
    """
    if isinstance(key, dict):
        key = key.get("key", key.get("order"))
    if isinstance(key, str) and key.strip():
        text = key.strip()
        if all(c.isdigit() or c in " ,-" for c in text):
            return [int(t) for t in text.replace(",", " ").replace("-", " ").split()]
        letters = [c for c in text.upper() if c in A26]
        if not letters:
            raise ValueError(f"cannot read transposition key {key!r}")
        return sorted(range(len(letters)), key=lambda i: (letters[i], i))
    order = [int(k) for k in key]
    if width is not None and sorted(order) != list(range(width)):
        raise ValueError(f"key {key} is not a permutation of 0..{width - 1}")
    return order


class ColumnarTransposition(Cipher):
    """Columnar transposition, regular and irregular (null) grids."""

    info = CipherInfo(
        name="columnar",
        title="Columnar transposition",
        family=Family.TRANSPOSITION,
        key_type="keyword or permutation",
        min_length=12,
        cost=EXPENSIVE,
        aliases=("columnar_transposition", "column_transposition"),
        description="Plaintext written into a grid by rows, read out by columns in key order.",
        example_key="ZEBRA",
    )

    max_width = 14
    #: Cap on null patterns examined per width (random subsample beyond this).
    max_patterns = 1000
    #: Patterns promoted from the cheap first stage to the exact solver.
    pattern_leaders = 5
    #: Widths with at most this many orderings are enumerated exhaustively.
    exhaustive_limit = 720
    #: Widths up to this get the exact Held-Karp seed (~93 ms at 14).
    exact_dp_width = 14

    # -- transforms --------------------------------------------------------- #
    def encrypt(self, plaintext: str, key: Any = "ZEBRA") -> str:
        stream = self.prepare(plaintext)
        order = key_to_order(key)
        width = len(order)
        rows = [stream[i : i + width] for i in range(0, len(stream), width)]
        # Read the columns in key order; a short final row simply contributes
        # nothing to the columns past its end.
        return "".join("".join(r[col] for r in rows if col < len(r)) for col in order)

    def decrypt(self, ciphertext: str, key: Any = "ZEBRA") -> str:
        stream = self.prepare(ciphertext)
        order = key_to_order(key)
        return self.rebuild(stream, order)

    @staticmethod
    def rebuild(stream: str, order: Sequence[int]) -> str:
        """Rebuild the grid from a read order and return it read row by row."""
        width = len(order)
        if width == 0:
            return stream
        n = len(stream)
        full, rem = divmod(n, width)
        # Grid columns 0..rem-1 are one letter longer (the ragged final row).
        grid_lengths = [full + 1 if col < rem else full for col in range(width)]
        columns: list[str] = [""] * width
        pos = 0
        for col in order:
            length = grid_lengths[col]
            columns[col] = stream[pos : pos + length]
            pos += length
        height = full + (1 if rem else 0)
        return "".join(
            "".join(columns[col][row] for col in range(width) if row < len(columns[col]))
            for row in range(height)
        )

    # -- attack helpers ----------------------------------------------------- #
    def _pair_scores(
        self, segments: Sequence[str], ctx: CrackContext, max_rows: int | None = None
    ) -> list[list[float]]:
        """Bigram score of placing segment ``a`` immediately left of segment ``b``.

        ``max_rows`` truncates the columns.  Bigram evidence saturates after a
        couple of dozen rows, so the cheap first stage of the search ranks null
        patterns on truncated columns and saves ~half the time.
        """
        table = ctx.model._tables.get(2) or {}
        floor = ctx.model._floors.get(2, -6.0)
        size = len(segments)
        cols = [seg[:max_rows] if max_rows else seg for seg in segments]
        scores = [[0.0] * size for _ in range(size)]
        for a in range(size):
            ca = cols[a]
            for b in range(size):
                if a == b:
                    continue
                scores[a][b] = sum(table.get(x + y, floor) for x, y in zip(ca, cols[b]))
        return scores

    @staticmethod
    def _exact_path(scores: list[list[float]], groups: list[list[int]]) -> list[int]:
        """Exact maximum-weight Hamiltonian path (Held-Karp), respecting groups.

        The objective is the sum of adjacent-column bigram scores, which is the
        log-likelihood of the horizontal letter pairs under a bigram model -- so
        the optimal path really is the most likely column order.  Greedy
        extension gets this wrong on wide grids (it commits early and cannot
        undo), which is exactly the case where a 13-column transposition is being
        attacked; the DP is O(2^L * L^2) and still costs under 100 ms at L=14.

        ``groups[i]`` lists the nodes eligible for the i-th block of positions,
        which is how irregular grids pin the long columns to the left.
        """
        size = sum(len(g) for g in groups)
        nodes = [v for g in groups for v in g]
        if size <= 2:
            return list(nodes)
        index = {v: i for i, v in enumerate(nodes)}
        weight = [[0.0] * size for _ in range(size)]
        for a in nodes:
            for b in nodes:
                if a != b:
                    weight[index[a]][index[b]] = scores[a][b]
        slot_group = [gi for gi, group in enumerate(groups) for _ in group]
        groups_i = [[index[v] for v in group] for group in groups]
        neg = float("-inf")
        dp = [neg] * ((1 << size) * size)
        parent = [-1] * ((1 << size) * size)
        for v in groups_i[0]:
            dp[(1 << v) * size + v] = 0.0
        popcount = [bin(m).count("1") for m in range(1 << size)]
        for mask in range(1 << size):
            position = popcount[mask]
            if position >= size:
                continue
            base = mask * size
            live = [
                (dp[base + last], last)
                for last in range(size)
                if (mask >> last) & 1 and dp[base + last] > neg
            ]
            if not live:
                continue
            for v in groups_i[slot_group[position]]:
                if (mask >> v) & 1:
                    continue
                target = (mask | (1 << v)) * size + v
                best, best_from = neg, -1
                for value, last in live:
                    cand = value + weight[last][v]
                    if cand > best:
                        best, best_from = cand, last
                if best > dp[target]:
                    dp[target] = best
                    parent[target] = best_from
        full = (1 << size) - 1
        end = max(range(size), key=lambda last: dp[full * size + last])
        path: list[int] = []
        mask, last = full, end
        while last != -1:
            path.append(nodes[last])
            previous = parent[mask * size + last]
            mask ^= 1 << last
            last = previous
        path.reverse()
        return path

    @staticmethod
    def _greedy_path(scores: list[list[float]], nodes: Sequence[int]) -> list[int]:
        """Greedy Hamiltonian path over ``nodes``: seed with the best pair, grow."""
        if len(nodes) <= 2:
            return list(nodes)
        # Seed with the single strongest *ordered* pair (a left of b).
        value, first, second = max(
            ((scores[a][b], a, b) for a in nodes for b in nodes if a != b),
            default=(0.0, nodes[0], nodes[-1]),
        )
        left, right = [first], [second]
        used = {left[0], right[0]}
        while len(used) < len(nodes):
            options = []
            for c in nodes:
                if c in used:
                    continue
                options.append((scores[right[-1]][c], "right", c))
                options.append((scores[c][left[0]], "left", c))
            if not options:
                break
            _, side, col = max(options)
            if side == "right":
                right.append(col)
            else:
                left.insert(0, col)
            used.add(col)
        return left + right

    def _refine(
        self,
        stream: str,
        path: list[int],
        groups: list[list[int]],
        ctx: CrackContext,
    ) -> tuple[list[int], float]:
        """Swap hill climbing on quadgram fitness, respecting group slots.

        ``path[i]`` is the segment index sitting at grid column ``i``; the first
        ``len(groups[0])`` positions may only hold segments from ``groups[0]``.
        """
        best = list(path)
        best_fit = ctx.model.search_fitness(self.rebuild(stream, invert_path(best)))
        slot_group = [gi for gi, group in enumerate(groups) for _ in group]
        guard = 0
        while guard < 20 and not ctx.expired():
            guard += 1
            improved = False
            for i, j in combinations(range(len(best)), 2):
                if slot_group[i] != slot_group[j]:
                    continue  # swapping across the null boundary is illegal
                cand = list(best)
                cand[i], cand[j] = cand[j], cand[i]
                fit = ctx.model.search_fitness(self.rebuild(stream, invert_path(cand)))
                if fit > best_fit + 1e-9:
                    best, best_fit, improved = cand, fit, True
            if not improved:
                break
        return best, best_fit

    # -- cryptanalysis ------------------------------------------------------ #
    def _slice(self, stream: str, width: int, pattern: tuple[int, ...]) -> tuple[list[str], list[list[int]]]:
        """Cut the ciphertext into segments and work out which may sit where.

        ``pattern`` names the read positions that held a long column.  Returns
        ``(segments, groups)`` where ``groups[0]`` are the segments eligible for
        the left-hand (long) grid columns and ``groups[1]`` the rest.
        """
        full, rem = divmod(len(stream), width)
        lengths = [full + 1 if r in pattern else full for r in range(width)]
        segments: list[str] = []
        pos = 0
        for length in lengths:
            segments.append(stream[pos : pos + length])
            pos += length
        long_read = [r for r in range(width) if r in pattern]
        short_read = [r for r in range(width) if r not in pattern]
        groups = [long_read, short_read] if rem else [list(range(width))]
        return segments, groups

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        n = len(stream)
        if n < self.info.min_length:
            return
        hint = ctx.hints.get("key") or ctx.hints.get("width")
        if hint is not None:
            widths = [len(key_to_order(hint))] if isinstance(hint, str) else [int(hint)]
        else:
            widths = list(range(2, min(self.max_width, max(2, n // 5)) + 1))
        rng = random.Random(ctx.hints.get("seed", 4242))
        results: list[Candidate] = []
        best_confidence = 0.0
        for width in widths:
            # A width that already produced certain plaintext ends the search:
            # wider grids only add cost and rotation-equivalent near-duplicates.
            if best_confidence >= 0.86 or ctx.expired():
                break
            full, rem = divmod(n, width)
            if full < 3:
                continue  # too few rows for the bigram statistics to mean anything
            patterns: list[tuple[int, ...]] = (
                [()] if rem == 0 else list(combinations(range(width), rem))
            )
            if len(patterns) > self.max_patterns:
                rng.shuffle(patterns)
                patterns = sorted(patterns[: self.max_patterns])

            n_paths = 1
            for group_size in (rem, width - rem) if rem else (width,):
                for i in range(1, group_size + 1):
                    n_paths *= i

            # Stage 1 -- rank null patterns cheaply.  A ragged grid adds one
            # unknown (which read positions held the longer columns) and there
            # are C(width, rem) of them, which for width 12 and rem 8 is 495:
            # far too many to hill climb each.  So each pattern gets a greedy
            # bigram path and one quadgram evaluation, and only the leaders go
            # on to the exact solver.
            prelim: list[tuple[float, tuple[int, ...]]] = []
            for pattern in patterns:
                if ctx.expired():
                    break
                segments, groups = self._slice(stream, width, pattern)
                scores = self._pair_scores(segments, ctx, max_rows=24)
                seed = sum((self._greedy_path(scores, g) for g in groups), [])
                prelim.append(
                    (ctx.model.search_fitness(self.rebuild(stream, invert_path(seed))), pattern)
                )
            prelim.sort(key=lambda t: -t[0])
            leaders = patterns if len(patterns) == 1 else [p for _, p in prelim[: self.pattern_leaders]]

            for pattern in leaders:
                if ctx.expired():
                    break
                segments, groups = self._slice(stream, width, pattern)
                if n_paths <= self.exhaustive_limit:
                    best_path, _ = self._exhaustive(stream, groups, ctx)
                else:
                    scores = self._pair_scores(segments, ctx)
                    seeds = (
                        [self._exact_path(scores, groups)]
                        if width <= self.exact_dp_width and ctx.remaining() > 0.3
                        else [sum((self._greedy_path(scores, g) for g in groups), [])]
                    )
                    for _ in range(2):
                        seeds.append(sum((rng.sample(g, len(g)) for g in groups), []))
                    best_path, best_fit = None, float("-inf")
                    for seed in seeds:
                        if ctx.expired():
                            break
                        path, fit = self._refine(stream, list(seed), groups, ctx)
                        if fit > best_fit:
                            best_path, best_fit = path, fit
                if best_path is None:
                    continue
                plain = self.rebuild(stream, invert_path(best_path))
                confidence = ctx.model.score(plain).confidence
                best_confidence = max(best_confidence, confidence)
                results.append(
                    ctx.candidate(
                        self.name,
                        plain,
                        {"width": width, "order": invert_path(best_path)},
                        steps=ctx.steps,
                        width=width,
                        nulls=rem,
                        null_pattern=list(pattern),
                        method=(
                            "exhaustive permutation search"
                            if n_paths <= self.exhaustive_limit
                            else "Held-Karp bigram DP + quadgram swap refinement"
                        ),
                    )
                )
        results.sort(key=Candidate.sort_key)
        yield from results

    def _exhaustive(
        self, stream: str, groups: list[list[int]], ctx: CrackContext
    ) -> tuple[list[int] | None, float]:
        """Try every ordering within each group and keep the best quadgram score."""
        best_path, best_fit = None, float("-inf")
        combos = [list(permutations(g)) for g in groups]
        for parts in product(*combos):
            if ctx.expired():
                return best_path, best_fit
            path = [c for part in parts for c in part]
            fit = ctx.model.search_fitness(self.rebuild(stream, invert_path(path)))
            if fit > best_fit:
                best_path, best_fit = path, fit
        return best_path, best_fit

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        return transposition_likelihood(text, ctx)


def invert_path(path: Sequence[int]) -> list[int]:
    """Convert ``grid column -> read position`` into ``read position -> grid column``."""
    order = [0] * len(path)
    for grid_col, read_pos in enumerate(path):
        order[read_pos] = grid_col
    return order


class RailFence(Cipher):
    """Rail fence (zigzag) transposition."""

    info = CipherInfo(
        name="rail_fence",
        title="Rail fence",
        family=Family.TRANSPOSITION,
        key_type="rails + offset",
        min_length=8,
        cost=CHEAP,
        aliases=("zigzag", "railfence"),
        description="Plaintext written along a zigzag of N rails, then read off rail by rail.",
        example_key=3,
    )
    max_rails = 20

    @staticmethod
    def rails_pattern(length: int, rails: int, offset: int = 0) -> list[int]:
        """The rail index visited at each plaintext position."""
        if rails < 2:
            return list(range(length))
        cycle = 2 * rails - 2
        out = []
        for i in range(length):
            t = (i + offset) % cycle
            out.append(t if t < rails else cycle - t)
        return out

    def _key(self, key: Any) -> tuple[int, int]:
        if isinstance(key, dict):
            return int(key.get("rails", 3)), int(key.get("offset", 0))
        if isinstance(key, (tuple, list)):
            return int(key[0]), int(key[1]) if len(key) > 1 else 0
        return int(key), 0

    def encrypt(self, plaintext: str, key: Any = 3) -> str:
        rails, offset = self._key(key)
        stream = self.prepare(plaintext)
        fence: list[list[str]] = [[] for _ in range(rails)]
        for i, rail in enumerate(self.rails_pattern(len(stream), rails, offset)):
            fence[rail].append(stream[i])
        return "".join("".join(row) for row in fence)

    def decrypt(self, ciphertext: str, key: Any = 3) -> str:
        rails, offset = self._key(key)
        stream = self.prepare(ciphertext)
        pattern = self.rails_pattern(len(stream), rails, offset)
        counts = [0] * rails
        for rail in pattern:
            counts[rail] += 1
        cursor, pos = [], 0
        for rail in range(rails):
            cursor.append(pos)
            pos += counts[rail]
        out = [""] * len(stream)
        for i, rail in enumerate(pattern):
            out[i] = stream[cursor[rail]]
            cursor[rail] += 1
        return "".join(out)

    def keys(self) -> Iterator[tuple[int, int]]:
        for rails in range(2, self.max_rails + 1):
            for offset in range(2 * rails - 2):
                yield (rails, offset)

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        return -ctx.model.search_fitness(letters_only(plaintext))

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        return transposition_likelihood(text, ctx)


class SkipTransposition(Cipher):
    """Skip / scytale transposition: read every ``k``-th letter, then wrap.

    Equivalent to winding the message around a rod of fixed circumference, and
    the simplest transposition of all -- which is why it turns up as an outer
    layer so often.
    """

    info = CipherInfo(
        name="skip",
        title="Skip / scytale",
        family=Family.TRANSPOSITION,
        key_type="stride",
        min_length=6,
        cost=CHEAP,
        aliases=("scytale", "stride", "caesar_box"),
        description="ct = pt[::k] + pt[1::k] + ... + pt[k-1::k]",
        example_key=5,
    )

    def encrypt(self, plaintext: str, key: Any = 5) -> str:
        stream = self.prepare(plaintext)
        k = max(1, int(key))
        return "".join(stream[i::k] for i in range(k))

    def decrypt(self, ciphertext: str, key: Any = 5) -> str:
        stream = self.prepare(ciphertext)
        k = max(1, int(key))
        out = [""] * len(stream)
        pos = 0
        for i in range(min(k, len(stream))):
            for j in range(i, len(stream), k):
                out[j] = stream[pos]
                pos += 1
        return "".join(out)

    def keys(self) -> Iterator[int]:
        yield from range(2, 41)

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        return -ctx.model.search_fitness(letters_only(plaintext))

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        return transposition_likelihood(text, ctx) * 0.6


class RouteTransposition(Cipher):
    """Route transposition over a rectangular grid, using standard read paths.

    Covers the routes that show up in puzzle books and CTFs: by columns, by
    rows, spirals (in/out, clockwise/counter-clockwise), boustrophedon snaking
    and diagonals.  The keyspace is small and enumerable, so ``crack`` is
    exhaustive.
    """

    info = CipherInfo(
        name="route",
        title="Route transposition",
        family=Family.TRANSPOSITION,
        key_type="(columns, route)",
        min_length=8,
        cost=MODERATE,
        aliases=("route_cipher",),
        description="Plaintext filled into a grid, read out along a fixed route.",
        example_key={"cols": 5, "route": "spiral_out_cw"},
    )

    ROUTES = (
        "columns",
        "rows",
        "columns_reverse",
        "rows_reverse",
        "snake_rows",
        "snake_columns",
        "spiral_out_cw",
        "spiral_in_cw",
        "spiral_out_ccw",
        "diagonals",
    )

    def _key(self, key: Any) -> tuple[int, str]:
        key = key or {"cols": 5, "route": "spiral_out_cw"}
        if isinstance(key, dict):
            return int(key.get("cols", 5)), str(key.get("route", "columns"))
        return int(key[0]), str(key[1])

    @staticmethod
    def _grid(stream: str, cols: int) -> list[list[str]]:
        """Row-wise grid, padded with blanks to a full ``cols`` rectangle.

        Padding to ``cols`` rather than to the widest row matters when the whole
        message is shorter than one row: the read path is generated for a
        rows x cols rectangle and would otherwise index past the end.
        """
        rows = [list(stream[i : i + cols]) for i in range(0, len(stream), cols)]
        return [r + [""] * (cols - len(r)) for r in rows]

    def _path(self, rows: int, cols: int, route: str) -> list[tuple[int, int]]:
        cells = [(r, c) for r in range(rows) for c in range(cols)]
        if route == "columns":
            return sorted(cells, key=lambda rc: (rc[1], rc[0]))
        if route == "columns_reverse":
            return sorted(cells, key=lambda rc: (rc[1], rc[0]), reverse=True)
        if route == "rows":
            return cells
        if route == "rows_reverse":
            return cells[::-1]
        if route == "snake_rows":
            out = []
            for r in range(rows):
                row = [(r, c) for c in range(cols)]
                out.extend(row if r % 2 == 0 else row[::-1])
            return out
        if route == "snake_columns":
            out = []
            for c in range(cols):
                col = [(r, c) for r in range(rows)]
                out.extend(col if c % 2 == 0 else col[::-1])
            return out
        if route == "diagonals":
            return sorted(cells, key=lambda rc: (rc[0] + rc[1], rc[0]))
        if route.startswith("spiral"):
            return self._spiral(rows, cols, route)
        return cells

    @staticmethod
    def _spiral(rows: int, cols: int, route: str) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        top, bottom, left, right = 0, rows - 1, 0, cols - 1
        clockwise = route in ("spiral_out_cw", "spiral_in_cw")
        while top <= bottom and left <= right:
            # The closing two legs of a ring only exist when the ring has both
            # height and width: on a single remaining row (or column) they walk
            # cells the first two legs already covered, which silently duplicates
            # letters and loses others.
            if clockwise:
                cells += [(top, c) for c in range(left, right + 1)]
                cells += [(r, right) for r in range(top + 1, bottom + 1)]
                if top < bottom and left < right:
                    cells += [(bottom, c) for c in range(right - 1, left - 1, -1)]
                    cells += [(r, left) for r in range(bottom - 1, top, -1)]
            else:
                cells += [(r, left) for r in range(top, bottom + 1)]
                cells += [(bottom, c) for c in range(left + 1, right + 1)]
                if top < bottom and left < right:
                    cells += [(r, right) for r in range(bottom - 1, top - 1, -1)]
                    cells += [(top, c) for c in range(right - 1, left, -1)]
            top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
        # "spiral_in" walks the same ring order backwards: from the centre out,
        # rather than from the outside in.
        if route.startswith("spiral_in"):
            cells.reverse()
        return cells

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        cols, route = self._key(key)
        stream = self.prepare(plaintext)
        grid = self._grid(stream, cols)
        return "".join(grid[r][c] for r, c in self._path(len(grid), cols, route) if grid[r][c])

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        cols, route = self._key(key)
        stream = self.prepare(ciphertext)
        n = len(stream)
        rows = (n + cols - 1) // cols if n else 0
        grid = [[""] * cols for _ in range(rows)]
        # Encryption writes the grid row by row and *skips* the cells the ragged
        # last row does not have.  Decryption has to skip exactly the same cells:
        # filling them would shift every later letter one place off, which is
        # invisible on a full rectangle and wrong on almost every real message.
        filled_last_row = n - (rows - 1) * cols if rows else 0
        it = iter(stream)
        for r, c in self._path(rows, cols, route):
            if rows and r == rows - 1 and c >= filled_last_row:
                continue
            try:
                grid[r][c] = next(it)
            except StopIteration:
                break
        return "".join("".join(row) for row in grid)

    def keys(self) -> Iterator[dict]:
        for cols in range(2, 13):
            for route in self.ROUTES:
                yield {"cols": cols, "route": route}

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        return -ctx.model.search_fitness(letters_only(plaintext))

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        return transposition_likelihood(text, ctx) * 0.8
