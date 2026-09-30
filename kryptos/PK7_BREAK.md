# PK7, broken from ciphertext alone

**Ciphertext (279 letters, as published):**

```text
FNRHTKRHSEDEJMBOWBDSCSDDXLICXULMBYQXWTGUIVNDYZBEQLVHFFFIDAKDCCJKWGOOUESCYELYMRAKIUJ
CUSEAXUQTYKOBVYDYMRBYWOTQEESCQSMDYDQJNPSWRSUOFMFJDYXSHCXNHVJVBYMZOZOATHTEOVLOQWZITH
TEAFMKGLASTBZRDMFRJPKWJOXZXPJCBOVAZEPKAEJPPSIUJODXTXERWTLTTYMRENBJGTNMLBDJMYJDDLRCX
CQCHYMJMHBEOLXEUFNJKBPRSHTEYXB
```

**Plaintext:**

> THREE WEEKS IN WE RISE BEFORE THE SUN AND EACH NEEDLE IS DONE BY NOON THE
> WHITESMITH SHOWS ME HIS TECHNIQUE FOR PURIFYING HIS METAL BEFORE DRAWING IT
> INTO A FINE WIRE HE HAS ME REPEAT THE SAME STEP FOUR TIMES WITH SLIGHT
> VARIATIONS STILL MY HAND FALTERS I AM PATIENT BUT I KNOW THIS IS NOT MY
> CALLING I HAVE MADE PEACE WITH IT AND WILL GO HOME SOON

**Key:**

| part | value |
| --- | --- |
| alphabet | `KRYPTOSABCDEFGHIJLMNQUVWXZ` (the Kryptos keyed alphabet) |
| Quagmire III | keyword `ANNEAL`, period 6 — keyed shifts `7, 19, 19, 11, 7, 17` |
| Hill 3×3 | keyword `ALCHEMIST` = `[[7,17,9],[14,11,18],[15,6,4]]`, det 17 (invertible mod 26) |

Encryption is `c_block = M · (p_block + k[pos mod 6])`, with every index taken
in the keyed alphabet. SHA256 of the plaintext:
`0147da64672740a2495a346c8b002051ae99193f7f20e9e1568265c3887525c3`.

Reproduce it:

```console
$ buttcrack crack --file kryptos/pk7.txt              # ~14 s, no hints
$ buttcrack decrypt keyed_hill --key '{"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "kryptos"}' "$PK7"
```

## How it was found

**1. The letters say nothing.** IC is 0.0393 against random's 0.0385, every
letter of the alphabet appears, and no period splits the text into English-like
columns. That rules out the monoalphabetic and periodic families and leaves
"polyalphabetic, polygraphic, or a stream", which is where the old solver gave
up and reported a repeating-key XOR fitted to noise.

**2. The block grid says a lot.** Two trigrams repeat three times each — `YMR`
at blocks 25, 33, 75 and `HTE` at blocks 51, 55, 91 — and *every* occurrence
starts on a multiple of three. Six aligned pairs where chance gives 0.24 is a
block cipher of width 3. All six also sit at odd block indices, so the
composite repeats every 2 blocks: a period-6 layer in front of a 3×3 block
cipher.

**3. A-Z Hill is the wrong problem.** The standard row-separation attack
(score each row of the decryption matrix against English monograms) returns
nothing here, because the arithmetic is not done on A-Z. In
`KRYPTOSABCDEFGHIJLMNQUVWXZ`, `A` is 7 and `E` is 9; relabelling the alphabet
is a permutation of Z/26 that does not commute with the matrix multiply, so
every row the A-Z attack scores is a linear functional of the wrong symbols.

**4. Separability survives both layers.** Writing `D = M⁻¹`,

```text
p[i] = Σ_j D[i][j]·c[j] − k[(block·3 + i) mod 6]      (keyed indices)
```

so plaintext position `i` still depends on row `i` of `D` alone, plus one shift
per phase (`block mod 2`). Scoring each candidate row with the blocks split by
phase — one histogram per phase, each allowed its own best shift — put the
three true rows at ranks 7, 20 and 103 of 15,372 usable rows. Quadgram
assembly of the top rows and a coordinate-ascent polish of the six shifts gave
the reading above at fitness −4.36 (English averages ≈ −4.3).

Two details matter for speed. Rows whose entries share a factor with 26 cannot
belong to an invertible matrix, and their output lands on a coset of Z/26,
which makes them *look* like the least flat histograms in the sweep — dropping
them removes the decoys. And a shift only rotates a histogram, so the
histogram's index of coincidence judges a row without trying 26 shifts; that
filter takes the sweep from 4.5 s to 0.8 s.

## Correction to the previous record

The record this repository carried for PK7 — cipher "Quagmire III (p6) +
Affine Hill 3×3", plaintext "HEPOINTEDTOTHEHEARTH…" — was not verifiable and
is now replaced. It fails on its own terms: the ciphertext blocks at positions
51, 55 and 91 are identical (`HTE`) and sit at the same phase, yet that record
maps them to three different plaintext trigrams (`MET`, `ENT`, `FOR`). No
composition of a period-6 substitution with a 3-letter block cipher can do
that, in either order. The replacement is verified the only way that settles
it: re-encrypting the plaintext under the stated key reproduces the published
ciphertext character for character (`tests/test_keyed_hill.py`).
