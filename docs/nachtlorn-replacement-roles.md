# Nachtlorn — replacement words, digit alphabets and exact book addresses

**Unresolved. No validated body decoder, recovered population or final outlier.**
This continuation distinguishes three roles that earlier hypotheses conflated.
The user proposed substituting blue using the book; they did not confirm green,
a corrected acrostic, a password, a cipher family or a book-key address.

## R11: use the replacement word itself

The already recorded passages supply **BLACK** (marble bowl, mourning nearby),
**GREEN** (bile) and **WHITE** (china). The literal words could be key material
without turning them into BLOOM/GLOOM/WLOOM first.

Each received the same bounded, separate key-role tests as previous candidates:

- phase-zero repeating-letter subtraction/addition/Beaufort: **18 letter paths,
  576 packet representations; zero complete registered objects**;
- standalone authenticated passwords, upper/lower/title case and the existing
  five derivations/mode-framing bounds: **21,888 attempts, zero valid tags**;
- direct raw-byte XOR, ASCII or SHA256 material: **1,152 trials, zero objects,
  whole-printable-ASCII candidates or origin-zero NPY/SQLite diagnostics**.

These are alternatives, not consecutive encryption stages. Classical word-key
families may overlap old language searches; the result is not claimed to be an
entirely new cipher family. No historical preferred word was a target or gate.

[Literal-word results](data/nachtlorn-reset-literal-word-results.json).

## R12: a keyword can specify the numeric digit alphabet

A keyword alphabet was constructed by deduplicating the keyword in order and
appending unused A–Z. Six explicit keywords were admitted before examining
outputs: **BLOOM, GLOOM, WLOOM, BLACK, GREEN, WHITE**. For example, the literal
BLOOM alphabet is `BLOMACDEFGHIJKNPQRSTUVWXYZ`.

The primary interconnected reading was **BLOOM as digit alphabet / BLACK as
password**: the black-bowl correction preserves the original acrostic. The other
admitted colour readings were bounded alternatives, not extra cipher layers.

Only raw source letters were interpreted under these alphabets: no letterwise
cipher or XOR first. The existing full/drop-I, whole-base26 A0/A1, two byte
orders and 0–7 restored-zero conventions give **384 unique byte representations**.

- Direct packet inspection: **zero complete objects or diagnostic candidates**.
- Colour-word authenticated passwords: **131,328 attempts, zero valid tags**.
- All **24** glyph/numeric/source roundtrips pass; this verifies the mapping,
  not plaintext correctness.

Direct BLOOM-alphabet inspection overlaps the historical baseline. The explicit
colour-password combinations and other admitted alphabets are the scoped inputs
here; this is not described as an exhaustive new family search.

A synthetic control using the primary BLOOM/BLACK pairing recovers a complete
AES-GCM-authenticated gzip/JSON packet and rejects a damaged tag. Another control
recovers a directly encoded gzip packet without encryption. Missing optional
crypto is explicitly reported as untested, never as a negative tag result.

[Keyword-digit results](data/nachtlorn-reset-keyword-digit-results.json).

## R13: use the passages as addresses, not passwords

The book clue can identify **where** key material starts rather than a word to
repeat. Eight starts were registered from exact, unique passages:

1. The deathbed **bowl** token.
2. Immediately after that token.
3. **White** in the same passage.
4. **Green** in the same passage.
5. **Black** in “cold black marble bowl.”
6. The **bowl** in that phrase.
7. Immediately after that bowl token.
8. **Mourning** in “Notice because I’m in mourning myself.”

Each running key is the uppercase ASCII letters from that exact position to
Gutenberg END. No repeated key, arbitrary offsets, key phases, wordlist, extra
cipher or preferred-word search was added. Offsets use normalized-LF story
characters; prefixes and key hashes are recorded so every start is auditable.
These passages were already seen: this is exploratory clue-bound testing,
**not held-out literary validation** or an author-confirmed instruction.

The same three letter operations and packet representations give **48 letter
paths / 1,536 packet configurations; zero complete structured objects**. All
original-letter roundtrips pass. A synthetic anchored running-key/gzip/JSON
control recovers the expected packet, with terminal-I handling and no source
repair.

Other passages—including the initial shaving bowl and the sea-as-bowl image—are
outside this eight-address test. Nothing here excludes every use of the book.

[Anchored-book results](data/nachtlorn-reset-anchored-book-results.json).

## Decision

None of these roles supplies the missing population. The exact black/mourning
passage is still relevant reference evidence, but does not justify a specific
cipher or password. The book might contribute to formatting, addressing, key
material or interpretation; none of the new recovery rules is established.
No new encryption stage is inferred simply because these alternatives failed.
Original source wording, letters, whitespace and terminal I remain unchanged.

## Reproduce

```bash
export PYTHONPATH="$PWD/scratch/nachtlorn-crypto-deps${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/nachtlorn_replacement_role_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --mode literal \
  --output docs/data/nachtlorn-reset-literal-word-results.json
python3 scripts/nachtlorn_replacement_role_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --mode alphabet \
  --output docs/data/nachtlorn-reset-keyword-digit-results.json
python3 scripts/nachtlorn_anchored_book_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt \
  --output docs/data/nachtlorn-reset-anchored-book-results.json
python3 -m unittest tests.test_nachtlorn_replacement_role_probe \
  tests.test_nachtlorn_anchored_book_probe
```

Only authenticated checks require the existing optional research crypto package;
the fixed-address running-key test uses the standard library.

Verification: **208 research tests pass across 26 modules**; **479 Python files**
parse successfully. Original source/book/archive hashes and exact layout pass.
Changed-core historical results and all R11–R13 results replay exactly; plan IDs,
links and the fixed branch pass their audits. No background work remains pending.
