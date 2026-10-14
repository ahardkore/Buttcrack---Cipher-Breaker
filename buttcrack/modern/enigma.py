"""Enigma I simulation and bounded initial-position crib search (historical)."""

from __future__ import annotations

import time
from itertools import product

from .common import deadline, integer

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROTORS = {
    "I": ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II": ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III": ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV": ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V": ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}
REFLECTORS = {"B": "YRUHQSLDPXNGOKMIEBFZCWVJAT", "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL"}


def letters(value: object, name: str, *, length: int | None = None) -> str:
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError(f"{name} must be ASCII letters/spaces, at most 4096 characters")
    if any(char not in ALPHABET + ALPHABET.lower() + " \n\r" for char in value):
        raise ValueError(f"{name} accepts ASCII letters and spaces only")
    text = value.upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if any(char not in ALPHABET for char in text) or (length is not None and len(text) != length):
        raise ValueError(f"{name} must contain {'exactly ' + str(length) if length else 'only'} A–Z letters")
    return text


class Machine:
    def __init__(self, options: dict) -> None:
        names = options.get("rotors", ["I", "II", "III"])
        if not isinstance(names, list) or len(names) != 3 or any(not isinstance(n, str) or n not in ROTORS for n in names) or len(set(names)) != 3:
            raise ValueError("rotors must be three distinct names from I, II, III, IV, V, ordered left to right")
        rings = letters(options.get("rings", "AAA"), "rings", length=3)
        reflector = options.get("reflector", "B")
        if not isinstance(reflector, str) or reflector not in REFLECTORS:
            raise ValueError("reflector must be B or C")
        self.reflector = [ALPHABET.index(char) for char in REFLECTORS[reflector]]
        self.notches = [ALPHABET.index(ROTORS[name][1]) for name in names]
        self.forward, self.backward = [], []
        for name, ring in zip(names, rings):
            wiring = [ALPHABET.index(char) for char in ROTORS[name][0]]
            inverse = [wiring.index(i) for i in range(26)]
            r = ALPHABET.index(ring)
            self.forward.append([[(wiring[(c + p - r) % 26] - p + r) % 26 for c in range(26)] for p in range(26)])
            self.backward.append([[(inverse[(c + p - r) % 26] - p + r) % 26 for c in range(26)] for p in range(26)])
        plugboard = options.get("plugboard", "")
        if not isinstance(plugboard, str) or len(plugboard) > 50:
            raise ValueError("plugboard must be up to ten space-separated pairs, such as AB CD")
        pairs = plugboard.upper().split()
        if len(pairs) > 10:
            raise ValueError("At most ten plugboard pairs are supported")
        self.plugs = list(range(26))
        used = set()
        for pair in pairs:
            if len(pair) != 2 or any(c not in ALPHABET for c in pair) or pair[0] == pair[1] or used.intersection(pair):
                raise ValueError("Plugboard pairs must be distinct A–Z letters without reused letters")
            used.update(pair)
            a, b = map(ALPHABET.index, pair)
            self.plugs[a], self.plugs[b] = b, a

    def step(self, positions: list[int]) -> None:
        middle_notch, right_notch = positions[1] == self.notches[1], positions[2] == self.notches[2]
        if middle_notch:
            positions[0] = (positions[0] + 1) % 26
        if middle_notch or right_notch:
            positions[1] = (positions[1] + 1) % 26
        positions[2] = (positions[2] + 1) % 26

    def transform(self, text: str, positions: str) -> str:
        p = [ALPHABET.index(char) for char in positions]
        output = []
        for char in text:
            self.step(p)
            value = self.plugs[ALPHABET.index(char)]
            for i in (2, 1, 0):
                value = self.forward[i][p[i]][value]
            value = self.reflector[value]
            for i in (0, 1, 2):
                value = self.backward[i][p[i]][value]
            output.append(ALPHABET[self.plugs[value]])
        return "".join(output)


def analyze(options: dict) -> dict:
    end = deadline(options)
    text = letters(options.get("text", ""), "text")
    if not text:
        raise ValueError("text must not be empty")
    machine = Machine(options)
    operation = options.get("operation", "transform")
    limitation = "Historical Enigma I, not modern encryption. Fixed rotor order, rings, reflector and plugboard. Search varies only the three initial positions; crib matches are candidates, not proof of intended plaintext. Spaces are removed; non-letter punctuation is rejected."
    if operation == "transform":
        positions = letters(options.get("positions", "AAA"), "positions", length=3)
        output = machine.transform(text, positions)
        return {"lab": "enigma", "status": "known-configuration transform", "output": output, "positions": positions, "round_trip_verified": machine.transform(output, positions) == text, "limitations": limitation}
    if operation != "search":
        raise ValueError("operation must be transform or search")
    crib = letters(options.get("crib", ""), "crib")
    if len(crib) < 8:
        raise ValueError("Search requires at least eight crib letters")
    offset = integer(options.get("offset", 0), "offset", 0, len(text))
    if offset + len(crib) > len(text) or offset + len(crib) > 256:
        raise ValueError("The crib must fit the ciphertext and end within its first 256 letters")
    candidates, examined = [], 0
    exhausted = False
    for chars in product(ALPHABET, repeat=3):
        if time.monotonic() >= end:
            exhausted = True
            break
        position = "".join(chars)
        prefix = machine.transform(text[:offset + len(crib)], position)
        examined += 1
        if prefix[offset:] == crib:
            plain = machine.transform(text, position)
            candidates.append({"positions": position, "plaintext": plain, "crib_matches": True, "reencryption_verified": machine.transform(plain, position) == text})
            if len(candidates) >= 20:
                break
    return {"lab": "enigma", "status": "crib-matching candidates" if candidates else "no match in examined initial positions", "candidates": candidates, "positions_examined": examined, "total_positions": 26 ** 3, "search_complete": examined == 26 ** 3, "budget_exhausted": exhausted, "candidate_limit_reached": len(candidates) >= 20, "limitations": limitation}
