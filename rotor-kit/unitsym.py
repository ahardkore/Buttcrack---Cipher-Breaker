#!/usr/bin/env python3
"""The pairwise (circulant) objective is invariant under alpha -> u*alpha for
every unit u mod 26, plus reflection and translation.  Only the text score
can pick the right representative, so: find a member of the equivalence class,
then try all 24 (unit, reflection) transforms and keep the one whose decryption
is English."""
from __future__ import annotations

import numpy as np
import common as C

UNITS = [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]


def resolve(ct: str, alpha: np.ndarray, fast=None):
    """Score every (unit, reflection) transform of alpha; return best."""
    from solver2 import Fast
    fast = fast or Fast(ct)
    best = (-1e18, None, None, None)
    for u in UNITS:
        for sign in (1, -1):
            beta = (sign * u * alpha) % 26
            if len(set(beta.tolist())) != 26:
                continue
            sc, sigma = fast.crack(beta, max_sweeps=14)
            if sc > best[0]:
                best = (sc, beta, sigma, (u, sign))
    return best, fast
