"""Explain candidate rankings without turning language scores into proof."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .results import Candidate, CrackReport

# A presentation heuristic, not a confidence interval or a calibrated probability.
CLOSE_SCORE_GAP = 0.03
PARAMETERS = (
    "key_length", "period", "periods", "columns", "width", "rows", "rails", "skip",
    "alphabet", "key_hex", "input_encoding", "column_ic", "period_quality",
    "restarts", "crib_offset", "padding", "normalization",
)


def json_key(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, dict):
        return {str(key): json_key(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_key(item) for item in value]
    return value


def verification(candidate: Candidate, ciphertext: str | None = None) -> dict:
    """A live direct-cipher check, or a checked canonical corpus association.

    Never trust a note saying 'verified'. Layer names alone do not preserve all
    outer keys, so do not claim a full-chain round trip for layered candidates.
    """
    from .ciphers import try_get
    from .text import A26, letters_only

    result = {
        "status": "not_checked", "label": "Not verified", "round_trip": "not_checked",
        "independent_verification": False, "intended_plaintext_proven": False,
        "detail": "Language statistics and dictionary hits do not verify the intended plaintext.",
    }
    if ciphertext is None:
        return result
    if candidate.cipher.startswith("paradigm_kryptos_"):
        from .paradigm import match

        record = match(ciphertext)
        if (record is not None and candidate.cipher == record.cipher_name
                and candidate.plaintext == record.plaintext and candidate.key == record.key):
            result.update({
                "status": "corpus_match", "label": "Verified canonical corpus match",
                "round_trip": "documented_in_corpus", "record": record.challenge_id,
                "plaintext_sha256": record.plaintext_sha256,
                "detail": f"Exact normalized ciphertext, plaintext and construction match {record.challenge_id}. {record.verification} This is archive recognition, not a new statistical solve or an independent recheck performed in this run.",
            })
        return result
    if candidate.steps:
        result["detail"] = "Full-chain re-encryption not checked: the report does not retain every outer-layer key. Statistical plausibility is not verification."
        return result
    cipher = try_get(candidate.cipher)
    if cipher is None or candidate.cipher == "none":
        result["detail"] = "No cipher round trip checked for this reading. A plaintext-like input does not establish an encryption method."
        return result
    try:
        produced = cipher.encrypt(candidate.plaintext, candidate.key)
    except Exception:
        result["detail"] = "This recovered parameter representation cannot be re-encrypted by the registered implementation. No verification claim is made."
        return result
    if not isinstance(produced, str):
        return result
    normalization = "exact characters"
    matches = produced == ciphertext
    # Only classical A–Z families get this explicitly disclosed normalization.
    # Never discard digits/punctuation from byte ciphers, codes or encodings.
    if not matches and cipher.info.alphabet == A26 and cipher.info.family.value in {
        "shift", "polyalphabetic", "substitution", "transposition", "polygraphic", "wheel",
    }:
        expected_letters = letters_only(ciphertext)
        matches = bool(expected_letters) and letters_only(produced) == expected_letters
        normalization = "A–Z letters only; case, spaces and punctuation ignored"
    result.update({
        "status": "reproduced" if matches else "mismatch",
        "label": "Round trip reproduced — not proof" if matches else "Round-trip mismatch",
        "round_trip": "passed" if matches else "failed", "normalization": normalization,
        "detail": "Re-encryption with the reported key " + ("reproduces" if matches else "does not reproduce")
        + " the input under the stated comparison. Even a passing round trip does not establish the correct key, cipher attribution or intended plaintext; no independent verification was performed.",
    })
    return result


def profile(candidate: Candidate) -> dict:
    from .ciphers import try_get

    cipher = try_get(candidate.cipher)
    family = cipher.info.family.value if cipher else "plain / unclassified"
    if candidate.cipher.startswith("paradigm_kryptos_"):
        family = "canonical corpus / composed construction"
    parameters = {name: json_key(candidate.notes[name]) for name in PARAMETERS if name in candidate.notes}
    if isinstance(candidate.key, dict):
        parameters = {**json_key(candidate.key), **parameters}
    if candidate.key is not None and not isinstance(candidate.key, dict):
        parameters.setdefault("key", json_key(candidate.key))
    if candidate.cipher == "caesar" and isinstance(candidate.key, int):
        parameters.setdefault("shift", candidate.key)
    if candidate.cipher == "affine" and isinstance(candidate.key, (tuple, list)) and len(candidate.key) == 2:
        parameters.update(a=candidate.key[0], b=candidate.key[1])
    if cipher and cipher.info.alphabet:
        parameters.setdefault("alphabet", cipher.info.alphabet)
    return {
        "family": family, "cipher_title": cipher.info.title if cipher else candidate.notes.get("title", candidate.cipher),
        "key_data": json_key(candidate.key), "parameters": parameters,
        "key_type": cipher.info.key_type if cipher else "construction / unclassified",
        "statistical_plausibility": {
            "rank_score": round(candidate.confidence, 4),
            "language_score": round(candidate.score.confidence, 4) if candidate.score else None,
            "is_probability": False,
            "detail": "Language-model score, tempered by sample size and evidence caps. Not the probability this answer is correct. IC, chi-squared and segmentation are diagnostics, not additional independent proofs.",
        },
        "verification": verification(candidate),
    }


TIE_BREAKS = (
    "rounded language/evidence rank score (0.001)", "rounded n-gram fitness (0.1)",
    "opening-word quality", "fewer decode layers", "shorter rendered key",
    "canonical equivalent-cipher preference",
)


def ranking_reason(candidate: Candidate, previous: Candidate | None) -> str:
    if candidate.notes.get("named_by"):
        return "Cipher identification influenced the leading attribution: " + str(candidate.notes["named_by"])
    if previous is None:
        return "Leading candidate in the solver's returned ranking; this does not establish a unique or correct plaintext."
    for index, (left, right) in enumerate(zip(previous.sort_key(), candidate.sort_key())):
        if left != right:
            if left < right:
                return f"The preceding candidate wins on {TIE_BREAKS[index]}; later tie-breaks cannot reverse that comparison."
            return "Presentation order differs from pure statistical sorting (for example, cipher-identification attribution or canonical naming). Compare the measurements rather than assuming the first reading is proven."
    return "Tied on all ranking criteria with the preceding candidate; retained encounter order is not evidence of correctness."


def describe_report(report: CrackReport, limit: int, plaintext_limit: int | None) -> dict:
    candidates = report.candidates[:max(0, limit)]
    leader = report.best or (candidates[0] if candidates else None)
    payloads = []
    for index, candidate in enumerate(candidates):
        payload = candidate.as_dict(plaintext_limit=plaintext_limit)
        gap = leader.confidence - candidate.confidence if leader else 0.0
        check = verification(candidate, report.ciphertext)
        if index == 0 and len(candidates) > 1 and not candidate.notes.get("named_by"):
            reason = "Leading candidate: "
            for criterion, left, right in zip(TIE_BREAKS, candidate.sort_key(), candidates[1].sort_key()):
                if left != right:
                    reason += (f"ahead of #2 on {criterion}." if left < right else "presentation attribution differs from pure score order.")
                    break
            else:
                reason += "tied with #2 on every criterion; encounter order is not evidence."
        else:
            reason = ranking_reason(candidate, candidates[index - 1] if index else None)
        reasons = [reason]
        if check["status"] == "corpus_match":
            reasons.append("Canonical archive recognition supplies rank score 1.0; the attached language score is a separate plausibility measurement, not the verification.")
        if candidate.score:
            dictionary = f"dictionary coverage {candidate.score.words:.1%}" if candidate.score.dictionary_assessed else "dictionary scoring was not assessed"
            reasons.append(f"N-gram fitness {candidate.fitness:.4f} (higher is better); {dictionary}; {candidate.score.sample_size} characters scored.")
            if candidate.confidence < candidate.score.confidence:
                reasons.append("The rank score is lower than the uncapped language score; evidence/attack adjustments limit how much the reading can be trusted.")
        else:
            reasons.append("No language-score breakdown is available for this candidate.")
        if candidate.notes.get("method"):
            reasons.append("Recovery method: " + str(candidate.notes["method"]))
        for note in ("evidence", "caveat", "language", "also_known_as"):
            if candidate.notes.get(note):
                reasons.append(str(candidate.notes[note]))
        payload["ranking"] = {
            "rank": index + 1, "gap_to_leader": round(gap, 4),
            "close_to_leader": index > 0 and abs(gap) <= CLOSE_SCORE_GAP,
            "close_peers": [j + 1 for j, other in enumerate(candidates) if j != index and abs(candidate.confidence - other.confidence) <= CLOSE_SCORE_GAP],
            "tied_with_previous": index > 0 and candidate.sort_key() == candidates[index - 1].sort_key(),
            "reasons": reasons,
        }
        payload["verification"] = check
        payloads.append(payload)
    best = next((payload for item, payload in zip(candidates, payloads) if item is report.best), None)
    if best is None and report.best:
        best = report.best.as_dict(plaintext_limit=plaintext_limit)
        best["verification"] = verification(report.best, report.ciphertext)
    close = [p["ranking"]["rank"] for p in payloads if p["ranking"]["close_to_leader"]]
    return {
        "best": best, "candidates": payloads,
        "candidate_comparison": {
            "returned": len(payloads), "available": len(report.candidates),
            "search_mode": "comparison" if report.comparison_mode else "fast",
            "corpus_shortcut": bool(best and best["verification"]["status"] == "corpus_match"),
            "close_score_gap": CLOSE_SCORE_GAP, "close_ranks": close,
            "ranking_order": list(TIE_BREAKS),
            "detail": "Close means an absolute rank-score gap of at most 0.03, a display heuristic—not a probability or confidence interval. Rankings cover only candidates actually returned by the bounded search; identical normalized readings are merged. Re-encryption does not prove intended plaintext.",
        },
    }
