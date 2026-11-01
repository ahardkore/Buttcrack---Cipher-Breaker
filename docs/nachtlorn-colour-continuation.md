# Nachtlorn — colour alternatives and signed-cell construction check

**Unresolved. No plaintext, item population or final outlier has been recovered.**
This continues the user's blue-replacement suggestion without promoting GLOOM's
English meaning into evidence that it is the key.

## The most useful new reference finding

Episode 5 places these phrases in the same short passage:

> … the cold black marble bowl …
>
> … Notice because I’m in mourning myself.

Thus **blue → black** preserves **BLOOM**, while also providing a literal
**mourning** connection. That is an alternative to the earlier green/deathbed
reading, not a confirmed correction. It shows why “blue is the outlier” and
“the acrostic must change” are different hypotheses.

A whole-story audit found **17 exact bowl/bowls tokens**. It records every hit,
episode, and a fixed window of 40 ASCII word tokens on each side. None of these
windows contains the exact token blue. Some hits are other senses of bowls, and
proximity alone does not show that a colour modifies the vessel or contents.
This is exploratory reference work, not a held-out test or proof of an error.

| Proposed replacement | Acrostic | Actual book context |
|---|---|---|
| green | GLOOM | Episode 1: bile in the deathbed bowl; also the bay as a bowl |
| white | WLOOM | Episode 1: the china vessel |
| black | BLOOM | Episode 5: the marble holy-water bowl; mourning nearby |
| yellow | YLOOM | Episode 10: soup poured into bowls |

The opening yellow dressinggown is still **not** a bowl colour. No new yellow-key
search was launched merely because that colour appears elsewhere in the novel.
The first-episode imagery makes green/white relevant, but does not uniquely fix
that episode as the source of every poem line.

## R6: white received the same body tests as green

[White result and complete reference contexts](data/nachtlorn-reset-white-results.json).
Only the replacement, acrostic and password case variants changed; no new cipher
family or extra encryption stage was added:

- WLOOM, phase-zero subtraction/addition/Beaufort, full body or explicit final-I
  removal: **6 letter paths, 192 byte configurations, zero structured objects**.
- Standalone passwords WLOOM/wloom/Wloom on the raw body representations:
  **7,296 authentication attempts, zero valid tags**.

This does not reject white in every role. The earlier
[GLOOM result](data/nachtlorn-reset-colour-results.json) remains unchanged and
replays exactly after allowing the new, explicitly registered WLOOM alternative.
A non-word acrostic was not discarded using English scoring.

## R7: given/taken as signed records, not letter shifts

An **invertible Bloom lookup table** is a concrete construction alternative:
its logical entries can retain signed counts for additions and deletions, plus
key/checksum aggregates. The public
[reference sources](data/nachtlorn-iblt-reference-source.json) were pinned and read,
not executed during R7. The [subsequent R8 work](nachtlorn-fieldwise-and-poem-keys.md)
compiles the reviewed C++ algorithm only for independent synthetic controls. They are not attributed to the puzzle author.

A repository named `dantodor/gloom` also appeared in the reference search. Its
README advertises IBLT, but its inspected implementation is ordinary set-bit
Bloom membership, with no signed-count or peeling mechanism. **The namesake does
not validate GLOOM or provide a decoder.** Its linked C++ implementation does
supply a genuine signed-entry model: count32, key64, checksum32 and variable
value bytes. Crucially, that reference supplies **no wire serializer**.

Before examining body-derived count fields, R7 registered this preflight:

- raw, GLOOM and WLOOM letter-stage alternatives; the two keys each use the same
  three operations as above; full body and explicit final-I removal;
- whole-base26 A0/A1, either byte order, restoring 0–7 zero bytes;
- hypothetical packed count32 cell strides **16, 20, 24, 32, 48** bytes, both
  count byte orders and every byte alignment;
- a structural lead requires **32 consecutive cells** whose signed counts have
  magnitude at most **1,000,000**. This is a diagnostic threshold, not a p-value.

All **14 letter paths / 448 unique byte representations** were checked. **No
stripe passed. The longest bounded-count run was only 2 cells.** These representations
therefore do not expose the expected long count stripe of those particular
small packed-table models. This is not a universal IBLT rejection: different
layouts, integer widths, counter bounds and transformed encodings remain outside
scope. No additional mask or encryption stage is inferred from the negative.

Even a passing stripe would not be an accepted object. It would next need checksum,
bucket-placement, complete-peeling and forward-reconstruction checks. Synthetic
all-ones filler deliberately demonstrates that a stripe can flag without encoding
an IBLT. No recovered-item or outlier claim is made by this probe.

[Signed-cell preflight result](data/nachtlorn-reset-signed-cells-results.json).

## Decision

Keep the colour substitution as an open clue interpretation. **Do not anchor on
GLOOM:** black/mourning supplies a book-grounded reading that leaves BLOOM intact.
Neither colour-key role recovered objects, and the newly specified signed-cell
representations did not reveal their predicted structure. The recovery operation
and an independently justified final outlier rule remain unknown.

## Reproduce

```bash
export PYTHONPATH="$PWD/scratch/nachtlorn-crypto-deps${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/nachtlorn_colour_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --replacement white \
  --output docs/data/nachtlorn-reset-white-results.json
python3 scripts/nachtlorn_signed_cells_probe.py docs/data/nachtlorn-transcript.txt \
  --output docs/data/nachtlorn-reset-signed-cells-results.json
python3 -m unittest tests.test_nachtlorn_colour_probe tests.test_nachtlorn_signed_cells_probe
```

The colour tests need the existing optional PyCryptodome research dependency for
actual authentication checks; missing crypto is explicitly reported as untested.
The stripe-only CLI runs without it. Eight colour tests and six signed-cell tests
cover synthetic recoveries, alternative admission, source preservation, contexts,
all registered strides/orders, unaligned framing, count/run limits, noise,
degenerate flags, reversible paths and overwrite guards. Source bytes and layout
remain untouched.

Verification: **182 research tests pass across 21 modules**; **469 Python files**
parse successfully. Original source/book/archive hashes, all three colour/signed
result replays, ten pinned reference files, plan IDs and document links pass their
audits. No source correction or candidate answer was written into the transcript.
