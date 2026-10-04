"""No-cost local cryptanalysis assistant.

This is deliberately an explainable planner, not a pretend general-purpose AI.
It inspects ciphertext statistics and recommends bounded attacks that the local
engine can actually run. It has no network calls, API key, or paid model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class AttackRecommendation:
    name: str
    reason: str
    scope: str
    confidence: str


def _ioc(text: str) -> float:
    letters = [c for c in text.upper() if c.isalpha()]
    n = len(letters)
    if n < 2:
        return 0.0
    counts = Counter(letters)
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))


def _entropy(text: str) -> float:
    letters = [c for c in text.upper() if c.isalpha()]
    n = len(letters)
    if not n:
        return 0.0
    counts = Counter(letters)
    return -sum((v / n) * log2(v / n) for v in counts.values())


def recommend(ciphertext: str) -> list[AttackRecommendation]:
    """Return transparent, ranked next steps for a ciphertext.

    Recommendations are hypotheses. They never claim that a cipher was
    identified or solved.
    """
    text = "".join(c for c in ciphertext.upper() if c.isalpha())
    n = len(text)
    ioc = _ioc(text)
    entropy = _entropy(text)
    out: list[AttackRecommendation] = []
    if n < 20:
        out.append(
            AttackRecommendation(
                "manual crib and substitution review",
                "The sample is short; statistical identification is underdetermined.",
                "show repeated symbols, likely boundaries, and hand worksheet",
                "low",
            )
        )
    if ioc >= 0.060:
        out.append(
            AttackRecommendation(
                "monoalphabetic/substitution ranking",
                f"IoC is {ioc:.4f}, compatible with a less-flattened substitution signal.",
                "rank Caesar, affine, keyword substitution, and bounded dictionary keys",
                "tentative",
            )
        )
    else:
        out.append(
            AttackRecommendation(
                "periodic and polyalphabetic screening",
                f"IoC is {ioc:.4f}; flattened monograms make a repeating-key model worth testing.",
                "estimate periods, then compare Vigenere-family and autokey models",
                "tentative",
            )
        )
    if n >= 50:
        out.append(
            AttackRecommendation(
                "transposition comparison",
                "The text is long enough to compare letter-preserving rearrangements.",
                "test bounded columnar widths and preserve exact permutation parameters",
                "exploratory",
            )
        )
    if entropy >= 4.4:
        out.append(
            AttackRecommendation(
                "encoding and symbol audit",
                f"Entropy is {entropy:.3f}; inspect normalization, symbols, and possible layers.",
                "check alphabet, separators, padding, and encoding before language scoring",
                "exploratory",
            )
        )
    return out


def explain(ciphertext: str) -> str:
    text = "".join(c for c in ciphertext.upper() if c.isalpha())
    lines = [
        "LOCAL CRYPTANALYSIS ASSISTANT",
        "No network model or paid API was used.",
        f"letters={len(text)} ioc={_ioc(text):.4f} entropy={_entropy(text):.3f}",
        "",
    ]
    for i, item in enumerate(recommend(text), 1):
        lines += [f"{i}. {item.name} [{item.confidence}]", f"   why: {item.reason}", f"   scope: {item.scope}"]
    lines.append("Status: recommendations only; verify every candidate by exact round trip.")
    return "\n".join(lines)
