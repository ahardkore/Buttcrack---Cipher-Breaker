# Could the ciphertext be a transposed, substituted Ulysses passage?

**R24: not if the whole body is a contiguous passage of the pinned text with
only a fixed letter substitution and transposition.** This is an exact scoped
exclusion—not a complete break, a rejection of the book clue, or proof that the
whole body was intended to be prose.

## Why test this?

The poem's initials spell **BLOOM**. Leopold Bloom and the reproduced layout
seed 4300 make James Joyce's *Ulysses*, Gutenberg 4300, a supported but
unconfirmed association. One basic cryptanalytic possibility is that the book
supplies the plaintext. Rather than guess an excerpt, a substitution alphabet,
or a transposition route, this test covers **every contiguous normalized
passage** and **every fixed bijective alphabet and position permutation**.

A substitution relabels letter counts; a transposition rearranges positions.
Neither changes the sorted multiset of the 26 letter frequencies, and in
particular neither changes the largest frequency. This remains true whichever
operation comes first. A maximum-frequency mismatch is enough to reject a
candidate without guessing a key or searching for readable words.

## Exact result

The pinned full Gutenberg file has **1,197,205** ASCII letters after retaining
only original `A–Z`/`a–z` and uppercasing. All its material, including Gutenberg
boilerplate, is included, making this broader than just the novel's body. Every
contiguous window of the indicated length was checked.

| Cipher input | Letters | Book windows checked | Cipher's largest letter count | Minimum largest count across book windows | Minimum edits needed |
|---|---:|---:|---:|---:|---:|
| Original body | 8,736 | 1,188,470 | 412 | 888 | 476 |
| Explicit final-I removal | 8,735 | 1,188,471 | 412 | 888 | 476 |

Thus **no contiguous window** of either length has the necessary frequency
invariant, regardless of the fixed bijective substitution or transposition.
In either case, at least **476 single-glyph substitutions** would be required
to make the cipher's maximum frequency reach even the minimum possible book
maximum. That is a necessary lower bound—not a proposed repair, a sufficient
condition, or a way to recover the right book window.

The threshold is independently checkable: every such book window contains at
least **888 E's**, so every window has some letter occurring at least 888 times.
The recorded first minimum-maximum witness starts at normalized book offset
511,420 (zero-based); directly counting its letters shows its largest count is
exactly 888. Together, the all-window lower bound and witness prove the reported
minimum. The witness is not presented as a recovered passage.

## What it means for the attack

This rules out the attractive shortcut “the entire body is a contiguous
*Ulysses* passage hidden by just one monoalphabetic substitution and arbitrary
transposition,” including explicit removal of the final I. It does **not**
reject *Ulysses* as a key, the book association, noncontiguous excerpts, shorter
hidden material, encoded or compressed objects, changing alphabets, encryption
or other construction layers. No claim is made about all English plaintexts.

The remaining challenge is to identify a justified operation that recovers an
actual population, and then independently justify which member is the outlier.
We cannot infer the missing operation merely from this negative result. The
I-zero visual hypothesis and the author-described interconnected layers remain
open.

## Reproduce and verify

- [Registration and outcomes](data/nachtlorn-reset-plan.json)
- [Numerical result](data/nachtlorn-book-frequency-invariant.json)
- [Checker](../scripts/nachtlorn_book_frequency.py) and
  [controls](../tests/test_nachtlorn_book_frequency.py)
- [Pinned book provenance](data/nachtlorn-binary-book-source.json)

The book is an optional ignored scratch input, not added to Git. Its GitHub blob
is `b2300b64c6517c83b5a367943448b1c0208d813f`; its 1,580,890 bytes have SHA256
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`.
The original transcript remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No source was changed.

Seven tests include exhaustive small rolling-window comparisons, a planted
passage with a secret substitution and transposition, correction-bound and
non-sufficiency cases, ASCII-only normalization, both source-overwrite guards,
and an independent cumulative-count proof across all book windows plus the
minimum witness. The book-dependent check skips explicitly if the optional book
is absent. With it and the prior optional research dependencies present, **316
tests across 38 research modules passed** locally; full-repository Ruff passed.

```bash
gh api repos/GITenberg/Ulysses_4300/git/blobs/b2300b64c6517c83b5a367943448b1c0208d813f \
  | python3 -c 'import sys,json,base64,pathlib; x=json.load(sys.stdin); pathlib.Path("scratch/nachtlorn-ulysses4300.txt").write_bytes(base64.b64decode(x["content"]))'
python3 scripts/nachtlorn_book_frequency.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --output scratch/nachtlorn-book-frequency-replay.json
python3 -m unittest tests.test_nachtlorn_book_frequency -v
```
