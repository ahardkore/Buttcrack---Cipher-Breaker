# Nachtlorn transcript — cryptanalysis

Analysis of `nachtlorn_transcript.txt` (secret gist, 2026-10-28), a 5-letter-group
"transcription" that opens with five lines of English and the instruction
**"Find the outlier."**

**Verdict: the published file contains no recoverable plaintext.** The letter body
is, to every test applied, indistinguishable from a one-time pad / uniform random
filler, and the only non-textual structure — the per-line indentation — does not
decode under any standard covert-channel reading. Reproduce with:

```console
$ python3 scripts/stego_channel_scan.py nachtlorn_transcript.txt
```

(The transcript itself is not committed here — it is a secret gist — so save it
locally first. The scanner is generic and works on any file.)

For the record, the ordinary solver agrees with the verdict: `buttcrack --file`
on the same text reports `NOT BROKEN`, best guess `vigenere (50%)`, and an
unintelligible output, because there is no substitution to undo.

---

## 1. Shape of the file

| property | value |
| --- | --- |
| bytes | 11,129, pure ASCII (no bidi/zero-width/control code points, no tabs, no trailing spaces, no doubled spaces) |
| header | 5 sentence fragments, a blank line, `Find the outlier.`, a blank line |
| body | **146 lines**; 145 lines of **12 five-letter groups** (60 letters) and a final line of 7 groups + one lone `I` (36 letters) |
| letters | **8,736** |
| indentation | leading spaces per line, values **0–7**, counts `0:19 1:20 2:17 3:18 4:16 5:16 6:23 7:17` |

```
blue at the bottom of the bowl.
laughter, somewhere on the stairs.
one given.
one taken.
morning. neither be right.

Find the outlier.

       VXGFA GJICA KZAYR VXBSW QGLXV QNPXI NUKSK EWHXK XDYIK LSVDA RONER HVFPZ
FLRXF UUNWZ QUDEW WKUFC YTJWZ BGCIM RNYTQ KQTFT PPXWS TYXKH CKCWO JLSAM
    GTGRL FMOKY IKNAK MDXEB FWRCD HORKG UBARE CPURO YCPOA PGSPJ LKANZ WSYWM
...
```

The header's five first letters spell **B‑L‑O‑O‑M**. That is the only
word-like structure anywhere in the file, and it is produced by the *plain*
header text, not by anything hidden.

## 2. The letter stream is random

Measured over all 8,736 letters:

| test | observed | uniform-random expectation | English expectation |
| --- | --- | --- | --- |
| index of coincidence | 0.03855 | 0.03846 | 0.0667 |
| monogram χ² (25 df) | 45.3 | 25 ± 7 | ≈ 10⁴ |
| count variance | 608 | 323 | — |
| digram χ² (676 df) | 715.8 | 676 ± 37 | ≫ 676 |
| trigram multiplicity | `{1:5217, 2:1365, 3:227, 4:24, 5:2}` | Poisson(0.50): `{0:10693, 1:5314, 2:1320, 3:219, 4:27, 5:2.7}` | very lumpy |
| IC at every lag 1–399 | 0.03853–0.03856 | flat | peak at the key length |
| **differential IC** at every lag 1–399 | 0.03839–0.03859 | flat | peak at the key length |
| best column IC (5-group / line columns) | 0.0386 / 0.0433 | flat | 0.066 |

Consequences:

* No monoalphabetic, polyalphabetic (any period up to ~400), autokey, or
  transposition structure survives. The **differential IC** test is the decisive
  one: for `C = P + K` with a key repeating at period *p*, the stream
  `C[i] − C[i+p]` collapses to plaintext structure and shows IC ≈ 0.066 at lag *p*.
  It is flat at 0.0384 for **every** lag, so no key of any period ≤ 400 is in use.
* No window of 60 letters anywhere in the file reads as language, under any of the
  26 Caesar shifts or Atbash (best −6.65/char; English ≈ −4.5, random ≈ −7.8).
* Dictionary words appear only at chance rates (9 five-letter dictionary words in
  8,736 letters where ~7 are expected; the one aligned group that is a word is
  `ORDRE`, which is a French/English-variant spelling and a coincidence).

So the letters are either a genuine one-time pad (unbreakable by construction) or
filler generated to look like random letters. A one-letter bias does exist and is
consistent across the whole file — `E` at 412 occurrences (+4.2σ) with `J` at 299
(−2.1σ), and a count variance 1.9× the multinomial value. That is the fingerprint
of a *generator* with a soft spot for `E` (an LLM asked to emit "random letters"
does exactly this), not of a message.

## 3. The indentation is the only covert channel, and it is empty

Nobody indents lines by a random 0–7 spaces, so this was the first suspect:

* per-value χ² = 2.2 (7 df), 17 repeats against 18 expected, no serial correlation
  — the digits are uniform random themselves;
* decoded as octal triples, as packed 3-bit values in all 8 phases and both
  directions, as nibbles, as all 254 two-class symbol splits (which covers parity,
  alphabet half, vowel/consonant, thresholds), as Baconian over each split, as
  base-8 big integers read from either end and from every prefix/suffix length, and
  as Morse with every dot/dash/separator assignment — **no candidate reaches
  language-level fitness** (best of 929 scored candidates: −6.13/char, i.e. noise);
* the indent does not correlate with its line (odd-letter count, letter sum, vowel
  count, distinct letters, first/last letter — all at the 1/8 chance level), so it
  is not a checksum or a pointer derived from the line;
* selections *driven* by the indent (letter at offset `indent+k`, letter on the
  visual column, slope sweeps `(a·line + b·indent) mod 60` over all slopes) are
  noise, as is every letter-property bitstream (bit planes, parity, alphabet half,
  vowel flag) and every position-in-group substream.

## 4. What is actually anomalous

If "the outlier" is meant literally, these are the only candidates:

1. **The final line.** 145 lines carry 12 groups; the last carries 7 groups and a
   lone `I`. A one-letter group is the single structural outlier in the file. Read
   as a Caesar line it does not resolve; read as text it suggests a transcript that
   stops mid-word ("… LATLU I").
2. **`E` over-representation** — a generator artefact (see above), not a message.
3. **`ORDRE`** — the only aligned group that is a dictionary word; chance-level.

## 5. Why this cannot be broken, and what would change that

A one-time pad has no exploitable structure, so no amount of cipher analysis
recovers the plaintext; the same is true of filler that was never actually encoded.
Everything in this file points at the second case: the visible body and the
indentation are *both* clean random streams, which is what a puzzle generator
produces when it writes the noise correctly and then forgets to write the payload.

To make this solvable, one of these has to exist:

* **a key or a second artefact** — the pad, the source text used as a running key,
  an image/audio file the "transcription" was made from, or the generator script;
* **the encoding rule**, if the message really is in the indentation but with a
  non-obvious alphabet (a permutation of the eight values was already excluded, so
  it would have to be something like a route or a substitution over an 8-symbol
  alphabet with an external key);
* **a corrected file** — if the transcript was truncated, the missing tail (24
  letters for the last line alone) may be where the payload begins.

Anything else is guesswork: with a flat 0.0385 IC and flat differential IC, the
information simply is not there to recover.
