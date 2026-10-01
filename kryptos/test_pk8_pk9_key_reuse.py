#!/usr/bin/env python3
"""Test literal reuse of PK8's Q5/Q6/Q7 keys in both PK9 layer orders.

This is a finite 8! sweep under the tentative complete-columnar width-8 family.
It is a narrow bridge exclusion, not a general PK9 attack.
"""

from __future__ import annotations

import json
import sys
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from buttcrack.ciphers.keyed import Quagmire3  # noqa: E402
from buttcrack.ciphers.transposition import ColumnarTransposition  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402

Q_KEYS = ("METER", "METIER", "MASTERY")


def remove_q_layers(text: str) -> str:
    cipher = Quagmire3()
    for keyword in reversed(Q_KEYS):
        text = cipher.decrypt(text, {"key": keyword, "alphabet": "kryptos"})
    return text


def best_over_orders(make_plaintext):
    model = get_model()
    best = (float("-inf"), (), "")
    for order in permutations(range(8)):
        plaintext = make_plaintext(order)
        score = model.search_fitness(plaintext)
        if score > best[0]:
            best = (score, order, plaintext)
    return best


def main() -> None:
    ciphertexts = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())
    ciphertext = ciphertexts["PK9"]

    # P -> Q5 -> Q6 -> Q7 -> T8 -> C: undo T first, then the Q layers.
    q_then_t = best_over_orders(
        lambda order: remove_q_layers(ColumnarTransposition.rebuild(ciphertext, order))
    )

    # P -> T8 -> Q5 -> Q6 -> Q7 -> C: undo Q first, then T.
    q_removed = remove_q_layers(ciphertext)
    t_then_q = best_over_orders(
        lambda order: ColumnarTransposition.rebuild(q_removed, order)
    )

    for label, (score, order, plaintext) in (
        ("Q5+Q6+Q7 then T8", q_then_t),
        ("T8 then Q5+Q6+Q7", t_then_q),
    ):
        print(f"{label}: best_score={score:.6f} read_order={order}")
        print(f"plaintext={plaintext}")


if __name__ == "__main__":
    main()
