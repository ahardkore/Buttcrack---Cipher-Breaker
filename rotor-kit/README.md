# rotor-kit — the Ratchet cipher, end to end

> **Naming.** This cipher shipped as **`ratchet`** (`Ratchet`, self-rotating alphabet) in
> `buttcrack/ciphers/ratchet.py`; the research below was written while it was called
> `rotating`. `rotating`, `rotating_alphabet` and `chaocipher` remain aliases.

Working notes, attacks and measurements for the **Ratchet** cipher (a
self-rotating alphabet, Chaocipher-style), which is now a first-class cipher in
the tool (`buttcrack/ciphers/ratchet.py`, registered as `ratchet`).  Everything here
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
| `challenge.txt` | the 409-letter challenge ciphertext the cipher was recovered from (see below) |
| `common.py` | corpus scoring: quadgrams with an unseen-gram floor, `to_idx`, key permutation, `encrypt_text`/`decrypt_with_key` |
| `solver2.py` | the fast quadgram scorer and the original hill climb over the necklace |
| `spectral.py`, `spectral2.py` | the pooled skip-matrix attack: `M_k` is a permuted circulant for every `k`, so their sum has several times the data on one set of phases |
| `unitsym.py` | resolves the objective's symmetry (`alpha -> u*alpha` for the 12 units mod 26, plus reflection and translation) by trying all 24 transforms and keeping the one whose decryption reads as English |
| `kp.py` | the known-plaintext solver: interval sums over Z_26 by CRT (Z_2 x Z_13) |
| `engine.py`, `run_real.py` | earlier alternating/portfolio engines, kept as negative results |
| `bench_app.py`, `bench_slice.py` | the recall benchmarks behind the thresholds quoted in the README (`.log` files are their output) |

The production form of the attacks lives in `buttcrack/ciphers/ratchet.py`
(the module shipped as `rotating.py` while the cipher was being named): pure
standard library, worker-safe, and wired into the registry, the engine, the CLI,
the desktop app and the web app.  This directory is the research record, not a
dependency of the tool.

## The published challenge

`../examples/ratchet-challenge.txt` is a second, longer challenge written for
the cipher's wiki page: 6,778 letters, published with a 150-letter crib taken
from its own middle and the SHA-256 of the answer.  **`ratchet-challenge-solution.txt`
in this directory is the answer** — do not open it unless you want the puzzle
spoiled; the page publishes the hash precisely so the puzzle can be checked
without the answer travelling with it.  Measured on this container: the crib
attack is exact in 1.4 s with `--hint crib_offset=4066` and in 29 s by sweeping
every offset, and the ciphertext-only route is exact in 107 s with
`--budget 300 --workers 4`.  The page's tests (`tests/test_ratchet.py`,
`TestPublishedChallenge`) pin the ciphertext, the crib's offset and the digest
to those artifacts.

## Measured results (2 cores, this container)

**Known plaintext is decisive.** A crib of 150-500 letters recovers the exact
key in about a second, at any message length, including a crib taken from the
middle of a message — the whole message comes back, not just the part after the
fragment.  The message's *first* letter is the necklace's start offset and is
not recoverable; everything from the second letter on is.

```console
$ buttcrack crack --file ../examples/ratchet-challenge.txt --crib "NEANARCHIVE..." \
      --hint crib_offset=4066 --budget 90
SOLVED  confidence 1.00  in 33.0s
  cipher    ratchet
  method    known plaintext (linear solve mod 26)
```

The 33 s is the collection being tried on the way to the cipher that declares
the hint — the ratchet attack itself is 1.3 s.  Sweeping every offset instead
of naming one costs 29 s.

**Ciphertext-only needs length.** The transition statistic is flat enough at a
few hundred letters that the truth sits inside the sampling noise; the climb
only becomes reliable once the message carries thousands of letters, and the
engine's ~25 s slice is the binding constraint inside the app.

| letters | budget | result |
| --- | --- | --- |
| 409 | 60 s | **not broken** without a crib — the original challenge, and the reason the app offers `--crib` (with one: 0.46 s) |
| 6,778 (the published challenge) | 300 s, 4 workers | **exact** in 111 s (direct) / 107 s (through the engine) |
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
$ python3 -m unittest tests.test_ratchet              # cipher + crib path + the published puzzle
$ BUTTCRACK_SLOW=1 python3 -m unittest tests.test_ratchet    # adds the 8000-letter search
$ PYTHONPATH=. python3 rotor-kit/bench_app.py 90      # the recall table
$ PYTHONPATH=. python3 rotor-kit/bench_slice.py 20    # what the engine's slice buys
```
