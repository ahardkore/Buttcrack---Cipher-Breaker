"""Bounded, transparent diagnostics for a ciphertext/candidate comparison.

No scoring promotion, cipher identification or key recovery is performed here.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .lang import get_model, resolve_language
from .text import A26

MAX_RAW_CHARS = 16000
MAX_LETTERS = 8000
MAX_REPEAT_POSITIONS = 20
MAX_PATTERNS = 30


def ascii_letters(text: str) -> str:
    # Do not expand Unicode uppercase mappings (ß -> SS), which shifts positions.
    return "".join(char.upper() for char in text if char in A26 or char in A26.lower())


def bounded_int(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def symbol_entropy(counts: Counter) -> float | None:
    total = sum(counts.values())
    if not total:
        return None
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def sample(text: str, externally_truncated: bool = False) -> tuple[str, dict]:
    prefix = text[:MAX_RAW_CHARS]
    all_letters = ascii_letters(prefix)
    letters = all_letters[:MAX_LETTERS]
    counts = Counter(letters)
    n = len(letters)
    return letters, {
        "sample_chars": len(prefix), "letters": n, "distinct_letters": len(counts),
        "omitted_non_ascii_letters_or_layout": len(prefix) - len(all_letters),
        "raw_prefix_truncated": externally_truncated or len(text) > MAX_RAW_CHARS,
        "letter_sample_truncated": len(all_letters) > MAX_LETTERS,
        "ic": sum(count * (count - 1) for count in counts.values()) / (n * (n - 1)) if n >= 2 else None,
        "letter_entropy": symbol_entropy(counts),
        "symbol_entropy": symbol_entropy(Counter(prefix)),
        "frequencies": [{"letter": letter, "count": counts[letter], "proportion": counts[letter] / n if n else 0.0} for letter in A26],
    }


def repeated_patterns(letters: str, max_period: int) -> tuple[list[dict], Counter]:
    """Bounded Kasiski view: 3–5-grams, at most 20 stored positions each.

    Only adjacent stored repeat distances are counted, once per pattern/period.
    This avoids the quadratic all-pairs explosion on repetitive inputs.
    """
    patterns = []
    votes: Counter = Counter()
    for size in (3, 4, 5):
        seen: dict[str, list[int]] = {}
        totals: Counter = Counter()
        for index in range(len(letters) - size + 1):
            gram = letters[index:index + size]
            totals[gram] += 1
            positions = seen.setdefault(gram, [])
            if len(positions) < MAX_REPEAT_POSITIONS:
                positions.append(index)
        for gram, positions in seen.items():
            if len(positions) < 2:
                continue
            distances = [right - left for left, right in zip(positions, positions[1:])]
            factors = [p for p in range(2, max_period + 1) if any(distance % p == 0 for distance in distances)]
            votes.update(factors)
            patterns.append({
                "pattern": gram, "length": size, "occurrences": totals[gram],
                "positions": positions, "adjacent_distances": distances, "supporting_periods": factors,
                "positions_truncated": totals[gram] > len(positions),
            })
    patterns.sort(key=lambda item: (-item["length"], -item["occurrences"], item["positions"][0]))
    return patterns[:MAX_PATTERNS], votes


def periods(letters: str, max_period: int, reference_ic: float, votes: Counter) -> tuple[list[dict], list[dict]]:
    diagnostics = []
    n = len(letters)
    for period in range(1, min(max_period, n // 2) + 1):
        numerator = denominator = 0
        valid_ics = []
        sizes = []
        for offset in range(period):
            column = letters[offset::period]
            counts = Counter(column)
            size = len(column)
            sizes.append(size)
            if size >= 2:
                pairs = size * (size - 1)
                same = sum(count * (count - 1) for count in counts.values())
                numerator += same
                denominator += pairs
                # Zero IC is a real measurement, not a missing column.
                valid_ics.append(same / pairs)
        weighted_ic = numerator / denominator if denominator else None
        lag_matches = sum(left == right for left, right in zip(letters, letters[period:]))
        diagnostics.append({
            "period": period, "weighted_column_ic": weighted_ic,
            "mean_column_ic": sum(valid_ics) / len(valid_ics) if valid_ics else None,
            "min_column_letters": min(sizes), "mean_column_letters": n / period,
            "kasiski_votes": votes[period], "lag_matches": lag_matches,
            "lag_comparisons": n - period, "lag_match_rate": lag_matches / (n - period),
            "insufficient_sample": min(sizes) < 6 or n < 60,
        })
    max_votes = max((row["kasiski_votes"] for row in diagnostics), default=0) or 1
    for row in diagnostics:
        ic_support = min(1.0, max(0.0, (row["weighted_column_ic"] - 1 / 26) / max(reference_ic - 1 / 26, .001)))
        adequacy = min(1.0, row["min_column_letters"] / 12)
        row["support_score"] = adequacy * (.8 * ic_support + .2 * row["kasiski_votes"] / max_votes)
    ranked = sorted(diagnostics, key=lambda row: (-row["support_score"], row["period"]))
    estimates = []
    # Keep harmonics visible but name their shorter near-equal explanations.
    for row in ranked[:10]:
        shorter = [other["period"] for other in diagnostics if other["period"] < row["period"] and row["period"] % other["period"] == 0 and other["support_score"] >= row["support_score"] * .93]
        estimates.append({**row, "related_shorter_periods": shorter})
    return diagnostics, estimates


def alignment(ciphertext: str, plaintext: str, options: dict) -> dict:
    cipher = options.get("cipher", "none")
    if not isinstance(cipher, str) or len(cipher) > 128:
        raise ValueError("cipher must be a name of at most 128 characters")
    mode = options.get("alignment_model", "auto")
    allowed = ("auto", "none", "vigenere", "beaufort", "variant_beaufort", "gronsfeld", "caesar")
    if not isinstance(mode, str) or mode not in allowed:
        raise ValueError("Unsupported alignment_model")
    steps = options.get("steps", [])
    if not isinstance(steps, list) or len(steps) > 8 or any(not isinstance(step, str) for step in steps):
        raise ValueError("steps must be a list of at most eight cipher/layer names")
    explicit = mode != "auto"
    if mode == "auto":
        mode = cipher if not steps and cipher in allowed[2:] else "none"
    key = options.get("key", "")
    if not isinstance(key, str) or len(key) > 128:
        raise ValueError("key must be text, at most 128 characters")
    phase = bounded_int(options.get("key_offset", 0), "key_offset", 0, 127)
    start = bounded_int(options.get("alignment_start", 0), "alignment_start", 0, MAX_LETTERS)
    count = bounded_int(options.get("alignment_count", 80), "alignment_count", 1, 160)
    key_letters = ""
    if key and mode == "gronsfeld":
        if any(char not in "0123456789" for char in key):
            raise ValueError("Gronsfeld alignment requires a digit key")
        key_letters = "".join(A26[int(char)] for char in key)
    elif key and mode == "caesar":
        if not key.isascii() or not key.isdigit() or not 0 <= int(key) <= 25:
            raise ValueError("Caesar alignment requires a shift from 0 to 25")
        key_letters = A26[int(key)]
    elif key and mode != "none":
        if any(char not in A26 + A26.lower() for char in key):
            raise ValueError("This alignment model requires an A–Z key")
        key_letters = key.upper()
    rows = []
    for index in range(start, min(start + count, max(len(ciphertext), len(plaintext)))):
        c = ciphertext[index] if index < len(ciphertext) else ""
        p = plaintext[index] if index < len(plaintext) else ""
        k = key_letters[(index + phase) % len(key_letters)] if key_letters else ""
        predicted, matches = "", None
        if c and p and k:
            plain_index, key_index = A26.index(p), A26.index(k)
            if mode in ("vigenere", "gronsfeld", "caesar"):
                predicted = A26[(plain_index + key_index) % 26]
            elif mode == "variant_beaufort":
                predicted = A26[(plain_index - key_index) % 26]
            elif mode == "beaufort":
                predicted = A26[(key_index - plain_index) % 26]
            matches = c == predicted
        rows.append({"position": index, "ciphertext": c, "plaintext": p, "key": k, "predicted_ciphertext": predicted, "matches": matches})
    checked = sum(row["matches"] is not None for row in rows)
    return {
        "model": mode, "explicit_hypothesis": explicit and mode != "none", "rows": rows,
        "key_period": len(key_letters) or None, "key_offset": phase,
        "positions_checked": checked, "mismatches": sum(row["matches"] is False for row in rows),
        "lengths_match": len(ciphertext) == len(plaintext),
        "detail": "Displayed A–Z letter positions, with layout removed. " + (
            "No key equations are checked for unsupported, transposition, autokey, keyed-alphabet or layered constructions. Choose an explicit model only to test a separate hypothesis."
            if mode == "none" else "Equations test the chosen repeated-key convention only. Agreement is not independent verification or proof of intended plaintext; a manual model may not match the actual cipher/pipeline."
        ),
    }


def analyze(options: dict) -> dict:
    if not isinstance(options, dict):
        raise ValueError("Analysis input must be a JSON object")
    texts = []
    for name in ("ciphertext", "plaintext"):
        value = options.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text")
        truncated = options.get(name + "_truncated", False)
        if not isinstance(truncated, bool):
            raise ValueError(f"{name}_truncated must be a boolean")
        texts.append(sample(value, truncated))
    max_period = bounded_int(options.get("max_period", 24), "max_period", 2, 40)
    language = resolve_language(options.get("language", "english"))
    if language in ("auto", "detect"):
        language = "english"
    reference = get_model(language).monogram_reference()
    reference_ic = sum(proportion ** 2 for proportion in reference.values())
    outputs = []
    for letters, metrics in texts:
        repeats, votes = repeated_patterns(letters, max_period)
        diagnostics, estimates = periods(letters, max_period, reference_ic, votes)
        outputs.append({
            **metrics, "repeated_patterns": repeats, "periods": diagnostics, "key_length_estimates": estimates,
            "warnings": [warning for condition, warning in (
                (len(letters) < 60, "Short sample: period and key-length estimates are particularly unreliable."),
                (len(set(letters)) < 10, "Low letter diversity can create misleading IC, repeats and period peaks."),
                (metrics["raw_prefix_truncated"] or metrics["letter_sample_truncated"], "Diagnostics use a bounded prefix, not the full source text."),
            ) if condition],
        })
    return {
        "ciphertext": outputs[0], "plaintext": outputs[1], "alignment": alignment(texts[0][0], texts[1][0], options),
        "reference": {"language": language, "expected_ic": reference_ic, "uniform_random_ic": 1 / 26},
        "limits": {"raw_chars": MAX_RAW_CHARS, "letters": MAX_LETTERS, "repeat_positions": MAX_REPEAT_POSITIONS, "patterns": MAX_PATTERNS},
        "normalization": "ASCII A–Z only; case folded, spaces/digits/punctuation/non-ASCII letters removed. Positions and key offsets count letters after normalization.",
        "method": "Key-length support = min(1, shortest column / 12) × (0.8 × clipped column-IC lift above 1/26 toward the selected language reference + 0.2 × relative Kasiski votes). This is a heuristic, not a probability. Kasiski uses 3–5-grams and adjacent distances among the first 20 stored positions; overlapping patterns are not independent evidence. Lag rate measures equal letters separated by that lag. Shorter divisors and multiples can share peaks; repeats can also occur by chance.",
        "caveat": "Frequency, IC, entropy, repeats and period peaks do not prove a cipher, key or plaintext. A transposition preserves letter frequencies/IC/letter entropy. These A–Z tools may be inappropriate for byte ciphers, encodings and non-Latin alphabets. Repeated-key Vigenère estimates assume the correct input layer and language; autokey and keyed alphabets need other models.",
    }
