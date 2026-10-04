from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_verifier():
    path = ROOT / "kryptos" / "verify_pk10_solution.py"
    spec = importlib.util.spec_from_file_location("pk10_solution_verifier", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pk10_exact_round_trip() -> None:
    verifier = load_verifier()
    ciphertext = json.loads((ROOT / "kryptos" / "pk_all_ciphertexts.json").read_text())["PK10"]

    assert len(verifier.PK10_PLAINTEXT) == 504
    assert len(verifier.PK4_PLAINTEXT) == 224
    assert verifier.encode(verifier.PK10_PLAINTEXT) == ciphertext
    assert verifier.decode(ciphertext) == verifier.PK10_PLAINTEXT


def test_pk10_layer_primitives_round_trip() -> None:
    verifier = load_verifier()
    # Use a valid 504-character control for every PK10 rectangular layer.
    control = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 19 + "ABCDEFGHIJ"
    assert len(control) == 504
    for key in ("MARGINS", "UNDERLAY", "TWOYEARS", "HANDIWORK", "SMITHWORK", "BEAMWORK"):
        assert verifier.columnar(verifier.columnar(control, key, encode=True), key, encode=False) == control
    assert verifier.spiral(verifier.spiral(control, 12, encode=True), 12, encode=False) == control
    assert verifier.hill3(verifier.hill3(control, "ALCHEMIST", encode=True), "ALCHEMIST", encode=False) == control
