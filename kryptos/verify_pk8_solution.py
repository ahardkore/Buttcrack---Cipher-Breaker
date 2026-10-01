#!/usr/bin/env python3
"""Reproduce the externally published PK8 solution with local cipher code.

The construction and answer were published in TTFH/KRYPTOS commit 3d60736f:
https://github.com/TTFH/KRYPTOS/commit/3d60736f
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from buttcrack.ciphers.keyed import Quagmire3  # noqa: E402
MANIFEST = ROOT / "pk_verified_solutions.json"
KEYS = ("METE", "METER", "METIER", "MASTERY")


def main() -> None:
    record = json.loads(MANIFEST.read_text())["PK8"]
    cipher = Quagmire3()

    encrypted = record["plaintext"]
    for keyword in KEYS:
        encrypted = cipher.encrypt(encrypted, {"key": keyword, "alphabet": "kryptos"})

    decrypted = record["ciphertext"]
    for keyword in reversed(KEYS):
        decrypted = cipher.decrypt(decrypted, {"key": keyword, "alphabet": "kryptos"})

    digest = hashlib.sha256(record["plaintext"].encode()).hexdigest()
    assert encrypted == record["ciphertext"], "PK8 encryption mismatch"
    assert decrypted == record["plaintext"], "PK8 decryption mismatch"
    assert digest == record["sha256"], "PK8 plaintext checksum mismatch"
    assert len(encrypted) == record["length"] == 153, "PK8 length mismatch"

    print("PK8 verification PASS")
    print(f"length={len(encrypted)} matched={sum(a == b for a, b in zip(encrypted, record['ciphertext']))}")
    print(f"keys={' -> '.join(KEYS)}")
    print(f"sha256={digest}")
    print(f"plaintext={decrypted}")


if __name__ == "__main__":
    main()
