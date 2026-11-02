# Nachtlorn — active evidence ledger after reset

**Status: unresolved. The working model has been reset.** Earlier word fragments,
proposed keys, literary rosters and spelling repairs are quarantined in the
[pre-reset ledger](nachtlorn-pre-reset-ledger.md). They are not targets, scoring
features, acceptance criteria or reasons to choose the next model.

Current operating rules: [reset record](nachtlorn-reset.md) and
[machine-readable plan](data/nachtlorn-reset-plan.json).


**Latest continuation:** [whole-packet stored-gzip constraints](nachtlorn-stored-gzip.md)
exclude five length/convention cases by exact trailer arithmetic. The two full-body
cases time out under both Z3 and an independently budgeted cvc5 cross-check.
Neither solver produces a source candidate: no actual-source CRC check is reached.
The drop-final-I exclusions apply only to this narrow gzip construction; no packet,
population, final outlier or general gzip exclusion is established.

**Latest user-proposed lead:** replace blue using the book. **Green** was our
contents-colour candidate, yielding **GLOOM**; white is a vessel-colour alternative. The
[colour assessment](nachtlorn-colour-hypothesis.md) records the source distinction
and bounded tests: no recovered object or authenticated packet. This is a
hypothesis, not a source correction or a confirmed key.

**Earlier reset step:** [role assessment](nachtlorn-reset-role-assessment.md) checks
reference evidence separately from a cipher/password assumption. The book link
is supported as an association, not an answer class. Registered raw Bloom-filter
schemas and a fixed book-running-key/structured-packet test recovered no objects.
No historical candidate was used, and no extra cipher layer is inferred.

**Earlier continuation:** the [colour/signed-cell assessment](nachtlorn-colour-continuation.md)
records a black-bowl/**mourning** passage that preserves **BLOOM**, negative
WLOOM key tests, and a negative signed-count-stripe preflight. No object population
or final outlier is established; GLOOM is not privileged by being an English word.

**Earlier continuation:** [fieldwise tables and poem-key checks](nachtlorn-fieldwise-and-poem-keys.md)
test the independent field encoding and the explicit **GLPNM/WLPNM** unit-shift
hypothesis. Both fail their bounded recovery gates; direct byte-XOR roles also
recover no packet. No population or final outlier is claimed.

**Earlier continuation:** [replacement-role assessment](nachtlorn-replacement-roles.md)
separates literal **BLACK/GREEN/WHITE** keys, keyword digit alphabets and eight
exact book addresses. All registered recovery gates remain negative. The book
association is not a confirmed payload key or an answer class.

**Earlier continuation:** [exact representation invariants](nachtlorn-prefix-invariants.md)
rule out raw big-endian whole-base26 gzip, bzip2 and XZ under every digit-alphabet
permutation, not just selected keywords. The first six glyphs independently
certify the exclusions. Short zlib headers remain compatible with many alphabets;
this is not a packet recovery or a reason to prefer zlib. Scope and all four
numeral/final-I conventions are recorded under R14.

**Earlier continuation:** [little-endian congruences](nachtlorn-little-endian-invariants.md)
find explicit gzip/zlib/XZ header-compatible alphabets in all four models, but
none of the 12 arbitrary witnesses validates as a complete packet under the
bounded checks. Four bzip2 queries time out: UNKNOWN, not an exclusion. Header
compatibility does not choose a key, a byte order, a population or a final outlier.

## Literal source observations

The five poem lines are:

```text
blue at the bottom of the bowl.
laughter, somewhere on the stairs.
one given.
one taken.
morning. neither be right.
```

Their literal initials spell **bloom**, or **BLOOM** after uppercasing. This does
not, by itself, establish a cipher, password, book, data structure or answer class.
The instruction is **Find the outlier.**

The archived transcript contains 146 body rows and 8,736 letters. There are 145
rows of 60 letters and one of 36, printed as 1,747 five-letter groups and one
singleton **I**. These are observations about presentation, not a declaration of
the recovered object's type or the final outlier.

## A reproduced construction component: layout only

The following forward model reproduces **every body byte**, not only the leading
indent counts:

1. Keep the original letter stream unchanged.
2. Wrap it at 60 letters per row.
3. Separate groups of five with one space.
4. Prefix successive rows with `random.Random(4300).randrange(8)` spaces.
5. End each row with LF.

No padding, letter deletion or encryption is needed to reproduce this layout.
Copying the original eight-line preamble back also reproduces the complete file.
This is a verified **formatting fit**, not decryption, a unique-seed proof, an
author-confirmed recipe or identification of the letter generator.

An incomplete last group follows automatically from the supplied length under
this formatter. A separate role for the final I remains possible, but must be
justified rather than assumed. Exact formatting also does not rule out an
intentional alignment or letter-dependent visual extraction.

## Author statement versus user hypotheses

**Author clarification, relayed by the user:**

> roughly four or five interconnected layers, depending on how you count them.
> not all of them are encryption layers, though. some are part of the construction,
> others are about figuring out what you've actually recovered.

This supports considering construction, recovery and interpretation separately.
It does not specify four/five ciphers, a particular stage order or a datatype.

**User hypotheses retained without promotion to fact:**

- Each poem line may unlock a layer; the final answer may be the outlier at the
  final interpretation stage.
- A sideways page may represent original rows as vertical strips, with actual
  letter counts on each side of a zero guide. The zero must be justified before
  selecting an outlier. A whole-page pooled plot is not this model.
- The I, give/take language and final line may have further roles. None is assigned.

The two supplied pages are the complete material. Care was taken to preserve
spacing and indentation; that is not proof of a particular visual encoding.

## Interpretation candidates are not established facts

The external association between Bloom and Joyce's *Ulysses*, Gutenberg4300, is
real. Its intended role in this puzzle remains unconfirmed. It is not a default
population definition, nor permission to search for a preferred literary name.

Similarly, assigning +1/−1 to particular initials, using a named token as a
password, or interpreting it as a named construction are hypotheses. Each needs
an explicit forward model and a prediction beyond a recognizable fragment.

## Next decision gate

Before a proposed extraction runs, record:

- the clue basis and fixed parameters;
- the operation and its inverse, where applicable;
- the type and population of recovered objects;
- the rule that selects the exceptional object;
- a structural prediction, falsifier and suitable controls.

Exploration can suggest a model, but an output noticed during exploration is not
independent validation. Inspect the answer only after the selection rule is fixed.
No new encryption layer is added merely because an earlier attempt failed.

## Reproducible source and audit

- [Original transcript](data/nachtlorn-transcript.txt)
- [Source provenance](data/nachtlorn-source.json)
- [Fresh facts-only audit](data/nachtlorn-reset-facts.json)
- [Facts-only script](../scripts/nachtlorn_reset_audit.py)
- [Book metadata](data/nachtlorn-ulysses-metadata.yaml), an external association,
  not a confirmed puzzle role

```bash
python3 scripts/nachtlorn_reset_audit.py docs/data/nachtlorn-transcript.txt
python3 -m unittest tests.test_nachtlorn_reset_audit
```

The fresh script imports no wordlist, English scorer, historical fragment search
or proposed-key routine. The old `nachtlorn_clue_ledger.py` is a historical audit,
not the active reset tool. Prior negative experiments remain available through
the [historical log](nachtlorn-analysis.md), with their original bounded scopes.

Original source: 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
