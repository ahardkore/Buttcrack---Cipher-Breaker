"""No-cost local cryptanalysis assistant.

This is deliberately an explainable planner, not a pretend general-purpose AI.
It inspects ciphertext statistics, recognizes an exact verified corpus match when
one exists, and recommends bounded attacks that the local engine can actually
run. It has no network calls, API key, or paid model.

The recovered Paradigm Kryptos PK1–PK10 suite adds a useful lesson without
turning every ciphertext into a Kryptos claim: keyed alphabets and ordered
pipelines must be modelled explicitly, and a candidate is only established by
an exact round trip.  The assistant therefore treats the corpus as *verified*
only on byte-for-byte normalized equality; elsewhere it offers those methods as
transparent hypotheses.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from typing import Any

from .paradigm import catalog, match, normalize


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


def _paradigm_recommendations(text: str, ioc: float) -> list[AttackRecommendation]:
    """Transfer PK lessons without mistaking a resemblance for an attribution."""
    n = len(text)
    out: list[AttackRecommendation] = []
    # The PK suite showed that a classical periodic signal may live in a keyed
    # coordinate system.  This is useful whenever statistical screening points
    # toward a periodic cipher, not just at PK's ten published lengths.
    if n >= 40 and ioc < 0.060:
        out.append(
            AttackRecommendation(
                "keyed-alphabet Quagmire III screen",
                "PK1–PK10 demonstrated that periodic arithmetic can use a keyed alphabet; ordinary A=0 Vigenere analysis may miss that coordinate system.",
                "compare ordinary periodic models with Quagmire III over the KRYPTOS alphabet; retain the alphabet and recovered key with every candidate",
                "exploratory",
            )
        )
    if n >= 100:
        out.append(
            AttackRecommendation(
                "ordered pipeline worksheet",
                "The recovered PK suite combines substitution, complete columnar transposition, Hill, and spiral steps; scoring an unordered bag of ciphers loses the construction evidence.",
                "record every reversible layer, grid convention, direction, and intermediate text; accept a result only after exact re-encryption reproduces the input",
                "exploratory",
            )
        )
    published_lengths = {record["ciphertext_length"] for record in catalog()}
    if n in published_lengths:
        out.append(
            AttackRecommendation(
                "canonical-corpus comparison",
                f"{n} letters shares a length with a recovered PK1–PK10 record, but length alone identifies nothing.",
                "compare the normalized ciphertext exactly against the local verified catalog; if it differs, continue normal analysis rather than inheriting a PK mechanism",
                "low",
            )
        )
    return out


def recommend(ciphertext: str) -> list[AttackRecommendation]:
    """Return transparent, ranked next steps for a ciphertext.

    Recommendations are hypotheses, except an explicit ``verified`` exact match
    to the local PK1–PK10 catalog.  They never infer a cipher merely from a
    shared length, alphabet, or narrative theme.
    """
    text = normalize(ciphertext)
    n = len(text)
    ioc = _ioc(text)
    entropy = _entropy(text)
    exact = match(ciphertext)
    out: list[AttackRecommendation] = []
    if exact is not None:
        out.append(
            AttackRecommendation(
                f"verified Paradigm Kryptos {exact.challenge_id} corpus match",
                "The normalized ciphertext is byte-for-byte identical to a recovered PK1–PK10 record; its stored plaintext SHA-256 and construction verification are available locally.",
                f"return {exact.title}; mechanism: {exact.mechanism}; preserve the supplied verification record and re-run the construction independently when publishing",
                "verified",
            )
        )
        return out
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
                "estimate periods, then compare Vigenere-family, Quagmire III, and autokey models",
                "tentative",
            )
        )
    out.extend(_paradigm_recommendations(text, ioc))
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


def analysis(ciphertext: str) -> dict[str, Any]:
    """Machine-readable local-agent output for the API and desktop UI."""
    text = normalize(ciphertext)
    exact = match(ciphertext)
    return {
        "status": "verified_exact_match" if exact else "recommendations_only",
        "network": False,
        "model": "explainable-local-planner",
        "statistics": {"letters": len(text), "ioc": round(_ioc(text), 5), "entropy": round(_entropy(text), 4)},
        "exact_match": exact.as_dict(include_text=False) if exact else None,
        "recommendations": [asdict(item) for item in recommend(ciphertext)],
    }


def explain(ciphertext: str) -> str:
    text = normalize(ciphertext)
    exact = match(ciphertext)
    lines = [
        "LOCAL CRYPTANALYSIS ASSISTANT",
        "No network model or paid API was used.",
        f"letters={len(text)} ioc={_ioc(text):.4f} entropy={_entropy(text):.3f}",
        "",
    ]
    if exact is not None:
        lines += [
            f"VERIFIED EXACT MATCH: {exact.challenge_id} — {exact.title}",
            f"mechanism: {exact.mechanism}",
            f"verification: {exact.verification}",
            "This verdict follows exact corpus equality and a stored plaintext SHA-256, not language scoring.",
            "",
        ]
    for i, item in enumerate(recommend(ciphertext), 1):
        lines += [f"{i}. {item.name} [{item.confidence}]", f"   why: {item.reason}", f"   scope: {item.scope}"]
    if exact is None:
        lines.append("Status: recommendations only; verify every candidate by exact round trip.")
    else:
        lines.append("Status: verified canonical corpus match; independently reproduce the construction before relying on it outside this catalog.")
    return "\n".join(lines)
