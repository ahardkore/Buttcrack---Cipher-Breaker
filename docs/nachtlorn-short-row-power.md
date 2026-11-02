# Can a short book-key search reliably recover a planted message?

**R30: the selected search fails its synthetic recovery gate. The real short
row was not searched by this method.** This is an attack-sensitivity result,
not a negative result about the actual cipher or a recovered answer.

The user proposed the short final row as a possible outlier, while also
clarifying that the answer is an outlier at the **last layer**, not necessarily
the last printed row. *Ulysses* as a running key is another unconfirmed
hypothesis. A tempting next search would decrypt that 36-letter row at every
book offset and choose the most English-looking result. With over a million
possible starts and very little text, such a maximum can easily select noise.

## Fixed synthetic-only gate

Before touching the actual row with this search, the plan fixed eight synthetic
36-letter English phrases and eight book offsets. Each was encrypted with the
pinned book as a contiguous nonrepeating A0 running key using `C=P+K mod 26`.
Each control then:

1. Scores **all 1,197,170** book starts with room for the 36 letters.
2. Selects the best offset by the same fixed English-monogram likelihood used
   in R25, but only on the first **25** letters.
3. Checks the remaining **11** letters against the fixed +0.10 nats/letter
   held-out screen.
4. Compares all 36 recovered letters with the known synthetic plaintext.

The predeclared gate required **all eight** controls both to recover the exact
synthetic plaintext and pass the held-out screen. The source cipher row and
historical candidate words are not inputs to the controls.

## Outcome

| Measure | Synthetic controls |
|---|---:|
| Exact 36-letter recoveries | **2 / 8** |
| Held-out screen passes | **2 / 8** |
| Controls both exact and passing | **2 / 8** |
| Predeclared all-eight gate | **Failed** |
| Actual short-row search by this selector | **Not performed** |

Each of the six failures chose an incorrect offset despite a positive training
score. In these eight controls, the held-out check rejected all six incorrect
winners, but the examples are too few to establish its false-positive rate.
The experiment shows that this **particular** top-training monogram selector
can lose a real short message; it does not exclude a different attack, a short
payload, another key, or another layer. Nor would successful controls alone make
an actual output a verified final-layer outlier.

## Reproducibility

- [Registered gate and result](data/nachtlorn-reset-plan.json)
- [Individual synthetic outcomes](data/nachtlorn-short-row-power-controls.json)
- [Control runner](../scripts/nachtlorn_short_row_power.py) and
  [tests](../tests/test_nachtlorn_short_row_power.py)
- [Underlying numerical scan and its limits](nachtlorn-book-fullscan.md)

The synthetic runner uses the exact pinned book, optional NumPy 2.2.6, and the
previously tested FFT/direct-score machinery. The plaintext phrases are fixed
invented controls, not content claimed to be in the puzzle. The actual
ciphertext file is **not read** by this runner. Three tests cover encryption and
known recovery, invalid/overwrite guards, and independent scalar replay of all
published control winners; the underlying FFT tests check every offset on
small cases. **344 research tests across 44 modules passed** locally with
prior optional dependencies present; whole-repository Ruff passed.

Book SHA256:
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`.
Original transcript SHA256 remains
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

```bash
export PYTHONPATH="$PWD/scratch/nachtlorn-numpy-deps:$PWD"
python3 scripts/nachtlorn_short_row_power.py --book scratch/nachtlorn-ulysses4300.txt \
  --output scratch/nachtlorn-short-row-power-replay.json
python3 -m unittest tests.test_nachtlorn_short_row_power -v
```
