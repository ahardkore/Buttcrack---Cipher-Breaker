"""Explicit offline labs, deliberately separate from automatic cipher guessing."""

from __future__ import annotations

from . import aes, enigma, keystream, rsa

LABS = {"rsa": rsa.analyze, "keystream": keystream.analyze, "aes": aes.analyze, "enigma": enigma.analyze}


def run(lab: str, options: dict) -> dict:
    if not isinstance(lab, str) or lab not in LABS:
        raise ValueError("lab must be rsa, keystream, aes or enigma")
    if not isinstance(options, dict):
        raise ValueError("Lab input must be a JSON object")
    return LABS[lab](options)
