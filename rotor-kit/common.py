#!/usr/bin/env python3
"""Shared machinery for the rotating-alphabet (self-rotating necklace) cipher."""
from __future__ import annotations

import gzip
import math
import random
from pathlib import Path

import numpy as np

REPO = Path("/home/user/Buttcrack---Cipher-Breaker")
DATA = REPO / "buttcrack" / "data"

ENGLISH_FREQ_PCT = np.array(
    [8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153,
     0.772, 4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056,
     2.758, 0.978, 2.360, 0.150, 1.974, 0.074])


def _load_quad():
    QG = np.full(26 ** 4, math.log10(0.01), dtype=np.float64)
    with gzip.open(DATA / "english_quadgrams.txt.gz", "rt") as fh:
        for line in fh:
            g, n = line.split()
            code = ((ord(g[0]) - 65) * 17576 + (ord(g[1]) - 65) * 676
                    + (ord(g[2]) - 65) * 26 + (ord(g[3]) - 65))
            QG[code] = math.log10(int(n))
    return QG


def _load_bigram_probs():
    E = np.zeros((26, 26))
    with gzip.open(DATA / "english_bigrams.txt.gz", "rt") as fh:
        for line in fh:
            g, n = line.split()
            E[ord(g[0]) - 65, ord(g[1]) - 65] = int(n)
    return E / E.sum()


QG = _load_quad()
BIGRAM_PROB = _load_bigram_probs()
LOG_UNI_MAT = np.log(ENGLISH_FREQ_PCT / ENGLISH_FREQ_PCT.sum())
LOG_BI_MAT = np.log(np.maximum(BIGRAM_PROB, 1e-13))


def to_idx(text: str) -> np.ndarray:
    return (np.frombuffer(text.upper().encode("ascii"), dtype=np.uint8)
            .astype(np.int64) - 65)


def to_text(idx) -> str:
    return "".join(chr(65 + int(x)) for x in idx)


def rng_perm(rng: random.Random) -> np.ndarray:
    p = list(range(26))
    rng.shuffle(p)
    return np.array(p, dtype=np.int64)


def qg_score(t: np.ndarray) -> float:
    if len(t) < 4:
        return 0.0
    codes = t[:-3] * 17576 + t[1:-2] * 676 + t[2:-1] * 26 + t[3:]
    return float(QG[codes].sum())


def encrypt_text(pt: str, top: str, bottom: str) -> str:
    """Author's algorithm, verified against the worked example THAT -> GZZG."""
    pos_t = {c: i for i, c in enumerate(top)}
    s = 0
    out = []
    for p in pt:
        t = pos_t[p]
        out.append(bottom[(s + t) % 26])
        s = (s + t) % 26
    return "".join(out)


def decrypt_with_key(ct: str, top: str, bottom: str) -> str:
    x = {c: i for i, c in enumerate(bottom)}
    ix = [x[c] for c in ct]
    return "".join(top[(ix[k] - ix[k - 1]) % 26] for k in range(1, len(ct)))
