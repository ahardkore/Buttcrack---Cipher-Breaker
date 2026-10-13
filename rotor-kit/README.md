# rotor-kit — the rotating alphabet, end to end

Working notes, attacks and measurements for the **self-rotating alphabet
(Chaocipher-style)** cipher, which is now a first-class cipher in the tool
(`buttcrack/ciphers/rotating.py`, registered as `rotating`).  Everything here
exists so the numbers quoted in the README and in the cipher module can be
reproduced rather than believed.

## The cipher, verified

Two mixed alphabets, one under the other: find the plaintext letter in the top
row, write the bottom-row letter underneath it, then rotate the bottom row so
that the letter just written leads.  Writing `alpha = B^-1` and `T` for the top
row, the definition collapses to

```
alpha(c_k) = alpha(c_{k-1}) + T.index(p_k)
```

which is exactly what `solver2.encrypt_text` and the shipped cipher implement —
checked against the author's own worked example, `THAT -> GZZG` with the natural
top row and a reversed bottom row.

## What is here

| file | what it is |
| --- | --- |
| `challenge.txt` | the 409-letter challenge ciphertext, unbroken here (see below) |
| `common.py` | corpus scoring: quadgrams with an unseen-gram floor, `to_idx`, key permutation, `encrypt_text`/`decrypt_with_key` |
| `solver2.py` | the fast quadgram scorer and the original hill climb over the necklace |
| `spectral.py`, `spectral2.py` | the pooled skip-matrix attack: `M_k` is a permuted circulant for every `k`, so their sum has several times the data on one set of phases |
| `unitsym.py` | resolves the objective's symmetry (`alpha -> u*alpha` for the 12 units mod 26, plus reflection and translation) by trying all 24 transforms and keeping the one whose decryption reads as English |
| `kp.py` | the known-plaintext solver: interval sums over Z_26 by CRT (Z_2 x Z_13) |
| `engine.py`, `run_real.py` | earlier alternating/portfolio engines, kept as negative results |
| `bench_app.py`, `bench_slice.py` | the recall benchmarks behind the thresholds quoted in the README (`.log` files are their output) |

The production form of the attacks lives in `buttcrack/ciphers/rotating.py`:
pure standard library, worker-safe, and wired into the registry, the engine,
the CLI, the desktop app and the web app.  This directory is the research
record, not a dependency of the tool.

## Measured results (2 cores, this container)

**Known plaintext is decisive.** A crib of 150-500 letters recovers the exact
key in under a second, at any message length, including a crib taken from the
middle of the message (the letter before the crib is not recoverable — that is
the necklace's start offset).  Through the app:

```console
$ buttcrack crack --file challenge409.txt --crib "THEMESSAGEOPENSTHE..." --budget 60
SOLVED  confidence 1.00  in 40.43s
  cipher    rotating
  method    known plaintext (linear solve mod 26)
```

**Ciphertext-only needs length.** The transition statistic is flat enough at a
few hundred letters that the truth sits inside the sampling noise; the climb
only becomes reliable once the message carries thousands of letters, and the
engine's ~25 s slice is the binding constraint inside the app.

| letters | budget | result |
| --- | --- | --- |
| 409 | any | **not broken** — the challenge ciphertext, and the reason the app offers `--crib` |
| 1200 | 90 s | 1 of 3 (bench_app.log) |
| 2000 | 90 s | 2 of 3 |
| 3000 | 90 s | 2 of 3 |
| 4000 | 90 s | 3 of 3 |
| 4000 | 20 s slice | 2 of 3 (bench_slice.log) |
| 7000 | 20 s slice | 3 of 3 |
| 7000 (real prose) | 25 s slice | 1 of 2 |

The first plaintext letter is never recoverable ciphertext-only: every key in
the equivalence class decodes the same message with a different first letter.

**Negative results worth keeping.** Score-multiset objectives are gameable;
single-matrix spectral attacks are too weak (truth 180.5 against a random
maximum of 177.4 at 409 letters) and need pooling over skips; the pooled
objective's near-symmetry means its landscape is flat within 0.1% of the truth,
so the *text* score has to do the ranking; and a naive hill climb over the raw
key never lands from a few hundred letters (measured 605.9 against a truth of
929.5 at 409 letters).

## Reproducing

```console
$ python3 -m unittest tests.test_rotating             # cipher + crib path
$ BUTTCRACK_SLOW=1 python3 -m unittest tests.test_rotating   # adds the 8000-letter search
$ PYTHONPATH=. python3 rotor-kit/bench_app.py 90      # the recall table
$ PYTHONPATH=. python3 rotor-kit/bench_slice.py 20    # what the engine's slice buys
```
