"""Multi-message XOR relations and crib hypotheses under keystream reuse."""

from __future__ import annotations

from .common import byte_result, hex_bytes, integer


def analyze(options: dict) -> dict:
    values = options.get("ciphertexts")
    if not isinstance(values, list) or not 2 <= len(values) <= 16:
        raise ValueError("ciphertexts must contain 2–16 aligned hex strings")
    streams = [hex_bytes(value, "ciphertext", limit=4096) for value in values]
    if any(not data for data in streams):
        raise ValueError("Ciphertexts must not be empty")
    pairs = []
    for i, left in enumerate(streams):
        for j in range(i):
            relation = bytes(a ^ b for a, b in zip(left, streams[j]))
            pairs.append({"indices": [j, i], "plaintext_xor_if_reused": relation.hex(), "overlap_bytes": len(relation)})
    result = {
        "lab": "keystream", "status": "conditional analysis; keystream reuse is not proven",
        "pairs": pairs, "fragments": [],
        "limitations": "Requires the same keystream aligned at the same byte positions. Pairwise XOR alone does not prove reuse. A wrong crib yields wrong fragments that still satisfy XOR; recovered bytes are hypotheses, not verified plaintext. Never reuse an AES-CTR or ChaCha20 key/nonce pair.",
    }
    crib = options.get("crib", "")
    if not isinstance(crib, str) or len(crib) > 4096:
        raise ValueError("crib must be UTF-8 text of at most 4096 characters")
    if crib:
        known = crib.encode("utf-8")
        index = integer(options.get("message_index", 0), "message_index", 0, len(streams) - 1)
        offset = integer(options.get("offset", 0), "offset", 0, 4096)
        if offset + len(known) > len(streams[index]):
            raise ValueError("The crib must fit entirely inside its selected ciphertext")
        key = bytes(a ^ b for a, b in zip(known, streams[index][offset:]))
        result["implied_keystream"] = {"offset": offset, "hex": key.hex()}
        for i, data in enumerate(streams):
            fragment = bytes(a ^ b for a, b in zip(data[offset:], key))
            result["fragments"].append({"message_index": i, "offset": offset, "assumed_crib_source": i == index, "hypothesis": byte_result(fragment)})
    return result
