# Nachtlorn: replace blue with a book-grounded colour?

**Status: promising clue interpretation; no recovered object or solution.**

**Subsequent check:** the [continuation](nachtlorn-colour-continuation.md) finds a
black-bowl/mourning passage that leaves BLOOM intact, tests white on equal terms,
and records a bounded signed-cell construction preflight. GLOOM is not confirmed.

This is reset hypothesis **R5**, prompted by the user's suggestion that **blue**
is the outlier and should be replaced with something from the book. The original
transcript is unchanged; the proposed wording exists only as a derived hypothesis.

## What the pinned book actually supplies

The first episode of *Ulysses* describes:

> A bowl of white china … holding the green sluggish bile …

The full passage is recorded in the [result](data/nachtlorn-reset-colour-results.json).
It concerns Stephen's mother's deathbed. This is not the opening shaving bowl,
which contains lather. There are multiple bowls: the match is suggestive, not unique.

- **Green** describes the contents, fitting “at the bottom of the bowl.”
- **White** describes the vessel, so it is a genuine alternative, not excluded by
  the passage. The yellow in the opening modifies a dressinggown, not the bowl.

Replacing just the first word gives this **proposed**, not original, poem:

```text
green at the bottom of the bowl.
laughter, somewhere on the stairs.
one given.
one taken.
morning. neither be right.
```

Its initials spell **GLOOM**, rather than the original **BLOOM**. White instead
would produce **WLOOM**. The deathbed context also makes “morning” versus
“mourning” worth examining, but neither that pun nor GLOOM's meaning validates a
cipher key. Replacing one word also offers a possible reading of “one given /
one taken” without assuming two additional encryption operations.

## Bounded tests, registered before execution

Only GLOOM was tested against the body in this run. Two alternative roles were
kept separate, **not stacked**:

1. **Repeating letter key:** phase-zero A0 subtraction, addition and Beaufort;
   full literal body and explicit final-I removal. Six letter paths, **192** byte
   representations; **zero** complete registered structured objects. All letter
   roundtrips pass, which checks implementation, not plaintext correctness.
2. **Standalone authenticated password:** `GLOOM`, `gloom`, `Gloom`, using the
   existing finite five key-derivation recipes, five mode/nonce combinations,
   two packet layouts, 16-byte tags and empty associated data. **7,296** tag
   verifications; **zero** valid tags. Only raw-body byte representations were
   supplied, never the repeating-key outputs.

Both roles use whole-base26 A0/A1, both byte orders, and zero through seven
restored zero bytes. Structured acceptance requires a complete origin-zero
JSON/checksummed compressed packet or validated Bloom container, not a short word,
magic header, embedded fragment or executable pickle. No route, changed O initial,
key-phase search, wordlist or extra cipher layer was added.

These negatives do **not** reject the substitution, exclude other key roles or
show that blue is the final answer. The missing step remains an independently
justified mapping from the clues to a recovered object and its outlier rule.
Changing BLOOM to GLOOM also leaves their relative key-letter ordering identical:
ordinary columnar/Myszkowski transposition is not a new test under that change.

## Reproduce

With the existing optional PyCryptodome research dependency in the ignored scratch
target (the application's dependencies are unchanged):

```bash
export PYTHONPATH="$PWD/scratch/nachtlorn-crypto-deps${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/nachtlorn_colour_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt \
  --output docs/data/nachtlorn-reset-colour-results.json
python3 -m unittest tests.test_nachtlorn_colour_probe
```

Six tests cover the derived proposal, source preservation, zero restoration,
synthetic repeating-key recovery, authenticated synthetic recovery with a damaged
packet rejection, invalid inputs and both input overwrite guards. If the optional
crypto dependency is absent, the report explicitly marks authentication untested.
The original source SHA256 remains
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
