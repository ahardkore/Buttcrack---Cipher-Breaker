# Nachtlorn — whole-packet gzip constraints, two backends

**Unresolved. No plaintext, recovered population, or final outlier.**

R16 goes beyond [R15's header witnesses](nachtlorn-little-endian-invariants.md):
it requires a complete gzip member of one explicitly limited construction.
R17 checks only R16's two unresolved cases with a different solver, without
changing the packet rules or increasing the original experiment's budget.
Both experiments were registered before their actual-source solver queries.

## Results

A0 assigns glyphs bijectively to digits 0–25. A1 adds one to each assigned digit
in the base-26 polynomial. Neither convention chooses an alphabet or literary key.

| Retained source | Convention | Minimal bytes | R16: Z3 | R17: cvc5 |
|---|---|---:|---|---|
| Full body | A0 | 5,132 | Exact exclusion: trailer interval | Not rerun |
| Full body | A0 | 5,133 | UNKNOWN: timeout | UNKNOWN: timeout |
| Full body | A1 | 5,133 | UNKNOWN: timeout | UNKNOWN: timeout |
| Remove final I | A0 | 5,132 | Exact exclusion: trailer interval | Not rerun |
| Remove final I | A0 | 5,133 | Exact exclusion: trailer interval | Not rerun |
| Remove final I | A1 | 5,132 | Exact exclusion: trailer interval | Not rerun |
| Remove final I | A1 | 5,133 | Exact exclusion: trailer interval | Not rerun |

**Five exact exclusions, two unresolved cases.** All actual-source solver checks
returned before producing even one candidate numeral: **zero source CRC checks
were reached**. This is not evidence of repeated CRC failure, an exhaustive
negative result for the full body, or a general exclusion of gzip.

The original Z3 checks took 30.059319 and 30.055377 seconds. The independently
budgeted cvc5 checks took 30.000143 and 30.000214 seconds. Each case had a
30,000 ms total search budget and a cap of 512 distinct candidate numerals.
No cap was reached. R17 preserves the original R16 UNKNOWN results; it does not
replace them or silently extend their budgets.

- [R16 machine-readable results](data/nachtlorn-reset-stored-gzip-results.json)
- [R17 machine-readable results](data/nachtlorn-reset-stored-gzip-cvc5-results.json)
- [Registration and outcomes](data/nachtlorn-reset-plan.json)

## Exactly which construction was tested?

The body is interpreted as one base-26 integer under an arbitrary bijective
alphabet, then written as minimal **little-endian** bytes. Both full-body and
explicit final-I removal variants are admitted. The tested packet requires:

1. The ten-byte gzip header begins `1f 8b 08 00`: DEFLATE, no optional header
   fields. MTIME, XFL and OS are unrestricted.
2. Exactly one nonempty final **stored** DEFLATE block, with a payload of at
   most 65,535 bytes. Only the low three bits of the block's first byte are
   constrained (`001`); ignored alignment bits remain unrestricted.
3. Correct LEN/NLEN complement, CRC32 and ISIZE, with the entire packet consumed
   by an independent bounded gzip decoder and matching the parsed payload.
4. Exact roundtrip to the retained original letters. Zero through seven trailing
   zero bytes may be restored to the minimal byte representation; these are not
   changes to the original transcript.

CRC32 is checked on each concrete packet **after** structural model enumeration;
it is not encoded as an SMT constraint. The registered class has 23 bytes of
overhead, so for minimal length `n` and restored zeros `z`:

```text
payload length L = n + z - 23
ISIZE            = L.to_bytes(4, 'little')
```

The ISIZE must end with exactly `z` zero bytes. Source-length bounds and this
arithmetic leave the seven cases above. They all require `z = 2`; the possible
payload sizes are 5,111 and 5,112 bytes. Reversing the nonzero part of ISIZE gives
the integer's high-end byte prefix `13f7` or `13f8`.

The high-prefix interval is decomposed exactly into disjoint partial glyph
assignments. Five cases have **empty covers**, ruling them out before any SMT
or CRC search. The two surviving covers still admit, respectively,
13,130,372,138,129,326,080,000 and 13,181,463,080,301,035,520,000 complete
alphabet mappings **before** applying the low-bit packet constraints. These are
not counts of complete packets or satisfying SMT models.

The low 120 bits encode the gzip magic/flags, block type, LEN and NLEN. All 26
glyph digits must remain distinct and in range. Each satisfying assignment would
be reconstructed in ordinary Python and independently validated. A rejected
packet is blocked using observed-glyph assignments, avoiding repeated numerals
from permutations of unused glyphs. Completed UNSAT enumeration would justify
an exclusion; UNKNOWN, budget expiry and candidate caps do not.

## Independent backend and controls

R16 uses Z3 5.3.3 (package `z3-solver==5.3.3.0`). R17 uses cvc5 1.4.2, with
Z3 only constructing/serializing the shared constraints and blocking clauses;
**cvc5 performs all R17 satisfiability checks and supplies its models**. Both
use seed 4300. The adapter parses standard SMT-LIB, skips the export's automatic
`check-sat`, and retains incremental declarations for subsequent blocking clauses.

The reports preserve the source hash, backend versions, budgets, status/reason
and initial SMT-LIB fingerprints. R17 also hashes the unchanged R16 result file.
The fingerprints identify individual serializations, not canonical logical
formulas: A0 matches R16's fingerprint, while A1's rebuilt serialization differs.
Both runs use the same unchanged constraint builder and derived case inputs;
no byte-for-byte identity of the A1 exports is claimed.

Synthetic controls recover independently constructed, checksum-valid stored
members under both numeral conventions, including nonzero ignored alignment
bits. Corrupt CRC controls exercise enumeration and incremental blocking;
corrupt NLEN controls are unsatisfiable. Tests distinguish UNKNOWN, expired
budgets and candidate caps from exclusions, and guard source/result overwrites.
The interval decomposition is also checked against exhaustive small-alphabet
permutations and an independent exact counter.

**250 tests across 29 research modules pass** with both optional solvers and the
existing optional cryptography dependency present (25.709 seconds). This is a
focused research regression suite, not a fresh run of the entire repository's CI.

## Reproduce

Optional research dependencies are not added to application requirements:

```bash
python3 -m pip install --target scratch/nachtlorn-smt-deps z3-solver==5.3.3.0
python3 -m pip install --target scratch/nachtlorn-cvc5-deps cvc5==1.4.2
export PYTHONPATH="$PWD/scratch/nachtlorn-smt-deps:$PWD/scratch/nachtlorn-cvc5-deps"
python3 -m unittest tests.test_nachtlorn_stored_gzip_probe tests.test_nachtlorn_stored_gzip_cvc5
python3 scripts/nachtlorn_stored_gzip_probe.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-r16-replay.json
python3 scripts/nachtlorn_stored_gzip_cvc5.py docs/data/nachtlorn-transcript.txt \
  --previous docs/data/nachtlorn-reset-stored-gzip-results.json \
  --output scratch/nachtlorn-r17-replay.json
```

Bounded solver outcomes can vary; these commands do not turn timeouts into
proofs. Published source: 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
The transcript and its whitespace remain unchanged.

## What remains open

The drop-final-I variants fail **only for this no-optional-header, single stored
block construction**. That does not establish a meaning for I, select the full
body as the intended construction, or reject compressed DEFLATE blocks, multiple
blocks, optional fields, multiple members, other representations or other formats.

Two independent timeouts are a computational limit, not independent negative
evidence. No further solver-budget escalation is registered in this pass. Before
another body search, require a clue-grounded forward construction or an exact
representation invariant with a discriminating prediction—not another semantic
key grid or a return to quarantined fragments. Recovery must still proceed from
construction to an actual object/population and an independently justified
outlier rule; even a valid gzip packet alone would not finish the puzzle.
