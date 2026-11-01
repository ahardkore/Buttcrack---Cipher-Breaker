# Nachtlorn — role assessment after the reset

**Unresolved. No answer or decoded population is claimed.** This work uses the
[reset rules](nachtlorn-reset.md), not historical candidate words. Possible roles
of a clue may coexist; the alternatives below are not mutually exclusive.

## What the reference supports—and what it does not

The exact pinned Gutenberg source identifies **Ulysses, James Joyce, EBook4300**.
The novel's opening contains a stairhead, a bowl of lather and morning air. Those
are consistent with some of the poem's imagery. This is an exploratory comparison
of already available evidence, **not held-out validation or a significance test**.

A fixed audit of episode1 found:

| Literal token or prefix | Occurrences |
|---|---:|
| blue | 0 |
| bowl* | 6 |
| stair* | 8 |
| laugh* | 11 |
| morning | 9 |

None of the five literal poem lines occurs in that episode. The opening therefore
is not a verbatim source for the poem, and not every image is accounted for.
Generic shared imagery does not specify a decryption operation.

The defensible current distinction is:

- **Reference/identifier:** a supported association. It could help explain why
  the formatting seed is 4300.
- **Literal cipher key:** possible, but no cipher family follows from the acrostic
  alone. It is not the default interpretation.
- **Named construction:** also possible, but the name alone supplies no file
  schema, hashing convention, object universe or outlier-selection rule.

In particular, the book association does **not** establish a literary population,
a character roster, the type of the recovered objects or the final answer class.

## A small registered named-construction check

Before checking body-derived packets, the reset plan fixed two public serialized
Bloom-filter formats as a concrete, bounded alternative to a password reading:

- fixed filter: `<dQQQQ`, a 40-byte header and exact-size little-endian bit array;
- scalable filter: `<idQd`, a 28-byte header, child count, size table and fully
  checked fixed-filter children.

The implementation reference's scalable-header comment says32 bytes, but its
actual struct format is28. The probe follows the executable format, not that
comment. The exact public source blob is [pinned](data/nachtlorn-bloom-schema-source.json).
It is only a schema reference, **not evidence that the author used that software**.

The test used only whole-number base26 A0/A1, both byte orders, full body or
explicit terminal-I removal, and restoration of 0–7 zero bytes lost by minimal
integer encoding. No repeating cipher, keyed alphabet, transposition, hidden
packet offset or membership-word query was used.

All **64** declared byte representations failed the complete schema checks.
This rejects those raw representations of those formats—not every Bloom-related
construction. No item set or outlier was recovered. Synthetic controls validate
both formats, both digit conventions/orders, terminal extraction and restoration
of a six-zero-byte header.

[Role/reference and container results](data/nachtlorn-reset-role-results.json).

## One registered book-based recovery rule

A separate hypothesis tested whether the supported reference identifies running
key material, rather than assuming a repeating acrostic key. It fixed:

- ASCII letters only, uppercased, from three canonical domains: the raw pinned
  file, the Gutenberg body, or the story beginning with Stately;
- normalized start position0, no repeated key, no offset/phase search or row reset;
- `C-K`, `C+K`, or `K-C` over A=0;
- full input or explicit terminal-I removal;
- the same two whole-base26 representations, byte orders and zero-restoration bound.

The required endpoint was a **complete structured packet**: origin-zero JSON,
checksum-valid gzip/zlib/bzip2/XZ consuming the entire packet, or a complete
validated Bloom-filter container. Embedded members, static-pickle syntax,
recognizable words and repaired phrases were not accepted endpoints.

All **18** letter paths roundtrip exactly to the original letters, but **none of
576** byte representations yields an accepted packet. The roundtrips are only
implementation checks; they are not plaintext evidence. Synthetic controls recover
a complete running-key/base26/gzip/JSON packet with a terminal marker and reject
embedded or trailing-junk packets.

This changes the endpoint from earlier historical book-key language searches;
it does not turn their negative scores into evidence. The current result rejects
only the explicitly registered running-key/encoding combinations. It does not
reject the book association or all uses of that book.

[Running-key results](data/nachtlorn-reset-running-book-results.json).

## Current decision

The reference association can account for a known construction parameter without
being a payload key or a declaration of the answer's subject. We still lack the
operation that recovers the body objects and the rule that selects their outlier.
**No additional cipher layer is inferred merely because these tests failed.**

The remaining poem operations—including what is given or taken—stay unassigned.
The original-row vertical-strip hypothesis remains open, with no freely chosen
zero/guide or substitution of pooled-page statistics. No historical candidate
has been reintroduced as a target or validation criterion.

## Reproduce

```bash
python3 -m unittest tests.test_nachtlorn_role_probe tests.test_nachtlorn_running_book_probe
python3 scripts/nachtlorn_role_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --output scratch/role-results.json
python3 scripts/nachtlorn_running_book_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --output scratch/running-book-results.json
```

The book is pinned in the [source provenance](data/nachtlorn-binary-book-source.json)
and stays in ignored scratch storage. The [reset plan](data/nachtlorn-reset-plan.json)
records the tests, their predictions and their bounded conclusions. Eleven new
tests pass. Neither input file was changed, and no recovered content was executed.
