#!/usr/bin/env python3
"""What the app's BRUTAL slice buys: the engine caps this attack at ~20 s."""
import random
import sys
import time
from pathlib import Path

from buttcrack.ciphers import get
from buttcrack.ciphers.base import CrackContext

c = get('ratchet')
corpus = "".join(ch for ch in Path('examples/english_samples.txt').read_text().upper() if ch.isalpha())
SLICE = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
for L in (4000, 7000):
    for trial in range(3):
        rng = random.Random(808 + 13 * trial + L)
        top = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        bot = top[:]
        rng.shuffle(top)
        rng.shuffle(bot)
        key = "".join(top) + "|" + "".join(bot)
        text = (corpus * (L // len(corpus) + 1))[:L]
        ct = c.encrypt(text, key)
        ctx = CrackContext.create(budget=SLICE, workers=2)
        t0 = time.time()
        hits = list(c.crack(ct, ctx))
        dt = time.time() - t0
        stat = [h for h in hits if 'ciphertext' in str(h.notes.get('method'))]
        if stat:
            best = max(stat, key=lambda h: sum(a == b for a, b in zip(h.plaintext, text)))
            tail = sum(a == b for a, b in zip(best.plaintext[1:], text[1:])) / (len(text) - 1)
            print(f"L={L:5d} trial{trial} slice={SLICE:.0f}s: {dt:5.1f}s tail-match {tail:.5f} fitness {best.fitness:.2f}", flush=True)
        else:
            print(f"L={L:5d} trial{trial} slice={SLICE:.0f}s: {dt:5.1f}s NO CANDIDATE", flush=True)
