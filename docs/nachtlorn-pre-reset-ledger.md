# Nachtlorn — construction and interpretation ledger

**Status: unresolved. The author describes interconnected stages, not necessarily
four or five successive encryptions.** The intended endpoint is an English-language
solution; that does not establish that all 8,736 body letters decrypt to prose.

**Latest follow-up:** [hidden relationships and terminal-I extraction](nachtlorn-structure-and-marker-checks.md)
found no single-block additive-checksum exception, accepted binary payload or
valid AEAD tag in the stated families. The last-I-only extraction was tested
separately from remove-all-I. FRODO and TRACT remain unverified.

**Previous follow-up:** [raw numeric, remove-I/base25 and case-sensitive byte keys](nachtlorn-numeric-continuation.md)
recovered no verified object or final outlier. No source edits were made. FRODO
and TRACT remain hypotheses, not solutions.

## What is supplied, and what is a hypothesis?

**Author clarification, relayed by the user:**

> roughly four or five interconnected layers, depending on how you count them.
> not all of them are encryption layers, though. some are part of the construction,
> others are about figuring out what you've actually recovered.

**The user's interpretation:** each poem line unlocks a layer, and the answer is
the outlier at the last layer. This is a useful working hypothesis, not a statement
that the author confirmed a one-line/one-layer correspondence.

In particular, **last layer is not the same as last printed line**. Nor should a
failed reading automatically lead to adding another cipher.

## The poem: literal facts before algorithm assignments

| Line | Initial | Supported observation / possible further role |
|---|---|---|
| blue at the bottom of the bowl. | B | Bowl imagery can support a literary reading; no cipher family is established. |
| laughter, somewhere on the stairs. | L | Stairs and morning imagery can support that same reading. |
| one given. | O | A proposed line-order reading increments this O to P. |
| one taken. | O | The matching proposal decrements this O to N. |
| morning. neither be right. | M | May be a warning or validation clue; its exact operation is unresolved. |

The five initials **jointly spell BLOOM**. Thus a clue can depend on several lines,
and a line can do more than one job. The middle two lines can jointly propose:

```text
B L O O M
    +1 −1
B L P N M
```

**BLPNM is reproducible under this interpretation, but not a confirmed key.**
It is a key hypothesis, not permission to edit ciphertext or repair a decoded word.

## A four/five-stage model consistent with the clarification

This is a dependency model to test, **not the recovered solution**:

1. **Clue extraction:** obtain BLOOM from the poem.
2. **Literary identification:** connect Bloom with Joyce's *Ulysses*, Gutenberg 4300.
3. **Construction identification:** understand how the displayed material was generated.
4. **Recovery:** apply the justified extraction/decryption rule to recover objects or text.
5. **Interpretation:** determine the expected class and identify its outlier.

Steps 1 and 2 might count as one layer, explaining four versus five without
inventing an extra encryption. The author has not confirmed this particular
partition. Construction and recovery may also share parameters or dependencies.

### What is actually verified

- The acrostic is **BLOOM**.
- The archived book metadata identifies **James Joyce, Ulysses, Gutenberg 4300**.
  Its role as the intended clue bridge is supported, not confirmed by the author.
- All **146** leading-space counts exactly match consecutive
  `random.Random(4300).randrange(8)` draws. This verifies a layout-generator fit,
  not the letter generator, the unique possible seed, or the whole construction.
- The original transcript remains **11,129 bytes**, SHA-256
  `04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

## Recovered fragments are not yet a recovered population

The read-only audit rechecked these literal, unedited Vigenere readings:

| Candidate | Key | Source group | Position |
|---|---|---|---|
| FRODO | BLOOM | GCCRA | Body row 128, group 2; letter offset 7,625 |
| TRACT | BLPNM | UCPPF | Body row 127, group 8; letter offset 7,595 |

Offsets are zero-based; rows/groups are one-based. The JSON labels source columns
in **both** coordinate conventions to avoid mixing them. The exact TRACT context
is **DINTRACTCOMEDUEDATEZ**, not CONTRACT.

**FRODO could be a semantic outsider in a Joyce context. That does not yet make it
the answer.** We still lack a rule that selects its group and establishes what
population it is an outlier from. A targeted check found no matches from an
explicit thirteen-name Joyce roster under BLOOM, BLPNM or BLNPM at phase zero.
That finite check neither proves nor disproves a literary mechanism; it does not
supply the missing population or a significance result.

The separate native-pad fragment remains literally **SHAREISPAGETTI**. Its raw-word
offset 653 is unexplained, and changing it to SHARESPAGHETTI is a post-discovery
spelling proposal, not an established layer or solution.

## New construction tests: no intermediate-English assumption

The [whole-block and packed-object checks](nachtlorn-construction-checks.md)
tested 750,300 seeded block generators with no prefix matches. They also tested
the possibility that 8,736=624×14 encodes numeric objects rather than prose.
Across 5,376 capacity conditions, the best uint32/uint64 packings still need
392/304 leading-symbol replacements, not one exceptional object. The constraints
were independently replayed and synthetic positives passed. These negatives
are bounded to the documented APIs, keys and routes; they do not close the
recovery gap or confirm FRODO/TRACT.

## New binary-recovery tests: serialized objects rather than prose

The [binary-envelope continuation](nachtlorn-binary-recovery.md) tested 5,501
clue-key/route paths followed by base-26 and safe binary-object recognition.
It also checked four pinned Ulysses preset dictionaries and a smaller family
of 79,056 byte-mask configurations. No accepted payload or long-text candidate
was recovered within these documented families and resource caps. Synthetic
JSON/CSV controls passed without an English gate. This does not establish an
actual recovery layer or confirm an outlier.

## The next decisive gap

The key question is now:

**What does the construction let us recover, and what rule makes exactly one of
those recovered objects the outlier?**

A proposed break must justify its parameters from the clues, reproduce its
extraction without searching for a favorite word, and explain the final selection.
Where a cipher is involved, its inverse must also reproduce the original input.
A roundtrip alone is not enough: reversible nonsense roundtrips too.

## Reproducible source and audit

- [Exact transcript](data/nachtlorn-transcript.txt)
- [Source provenance](data/nachtlorn-source.json)
- [Book metadata](data/nachtlorn-ulysses-metadata.yaml), from
  [GITenberg](https://github.com/GITenberg/Ulysses_4300/blob/master/metadata.yaml)
- [Computed clue audit](data/nachtlorn-clue-audit.json)
- [Read-only audit script](../scripts/nachtlorn_clue_ledger.py)

```bash
python3 scripts/nachtlorn_clue_ledger.py
python3 scripts/indent_seed_check.py docs/data/nachtlorn-transcript.txt \
  --seed 4300 --body-start 9
```

These checks use only the standard library and the archived source. **146 targeted
tests pass**, covering the clue audit and the new construction checks, including
independent numeric-capacity replay and held-out predictive controls.

Earlier reports reference temporary `/home/user/work` research files that are not
present in this checkout. Their historical experiment results have not been rerun
here. The facts in this ledger were freshly checked against the archived original
and do not rely on those temporary files.
