# PK10 Correct-Architecture Audit — 2026-10-04 (superseded)

> **Status update, 2026-10-04:** This pre-break audit is retained as a record of
> the rejected 7/8/9-clock search direction. PK10 is now solved. See
> [`PK10_BREAK_REPORT_2026-10-04.md`](PK10_BREAK_REPORT_2026-10-04.md) and
> [`verify_pk10_solution.py`](verify_pk10_solution.py) for the exact cumulative
> construction and 504/504 round-trip verification.

## Historical result

PK10 remained unsolved at the time of this audit. The next attack must use the published construction

```text
H(4x4) H(3x3) Q(?) T(?)
```

rather than the repository's legacy three-clock `{7,8,9}` hypothesis. Here `H` is a Hill layer, `Q` is a Quagmire layer, and `T` is a transposition layer. The official 504-letter ciphertext and challenge page provide no support for replacing `Q(?)` with three additive clocks.

This is a major search-space correction. The attractive identity

```text
504 = lcm(7,8,9)
```

is an arithmetic property of the message length, not evidence of a 7/8/9 keystream. Likewise, a 12×42 arrangement is one possible rectangle, not proof of a T(42) layer. The old candidate in `pk10_record_6943.txt` does not produce coherent English and does not instantiate the published pipeline. Its low rare-letter count and locally optimized quadgram score are properties selected by its objective, not independent validation.

## Facts retained

1. The official ciphertext is 504 uppercase letters.
2. 504 is divisible by both Hill block sizes: 126 four-letter blocks and 168 three-letter blocks.
3. The two block boundaries realign every `lcm(4,3) = 12` letters, yielding 42 twelve-letter superblocks. This is a genuine consequence of the published architecture, unlike the inferred clock periods.
4. A valid solution must specify two invertible matrices modulo 26, all vector/alphabet conventions, the Quagmire construction, and the transposition convention, then reproduce all 504 ciphertext letters.
5. The official leaderboard showed no PK10 solver when checked on 2026-10-04.

## Consequence for crib attacks

Assuming encryption order is exactly the displayed left-to-right pipeline, plaintext first passes through H(4×4), then H(3×3), then Q, then T. A plaintext crib cannot be compared directly with ciphertext until T is inverted. Conversely, guessing only a transposition exposes output from Q applied to Hill-mixed text, which need not have plaintext n-gram statistics. This explains why ordinary column-order annealing is not a sound discriminator for this architecture.

The natural algebraic unit is a 12-letter superblock. With a candidate inverse transposition and Quagmire key, each superblock supplies four 3-vectors after H(3×3) and three 4-vectors before H(4×4). Known plaintext spanning enough independent vectors can determine Hill matrices, but only after the outer layers are fixed. Future exact-crib work should therefore solve or enumerate outer-layer conventions jointly and use modular rank as an early rejection test.

## Immediate research plan

1. **Recover the complete public cipher conventions.** Determine whether the displayed notation is encryption order; identify the Quagmire variant/alphabet and transposition family. Do not search unspecified semantics.
2. **Build one reversible evaluator.** It must support H4 → H3 → Q → T encryption and exact inverse decryption, with synthetic round-trip tests for every convention.
3. **Exploit 12-letter alignment.** Reject crib placements whose induced Hill systems are inconsistent modulo 2 or modulo 13 before attempting full modulo-26 reconstruction.
4. **Use narrative priors only as bounded cribs.** Likely continuation language after PK8 may generate candidates, but a phrase is evidence only if it leads to a complete key and exact 504-character round trip.
5. **Require held-out evidence.** Keys fitted on one subset of blocks must improve untouched blocks. Do not describe optimized lexical fragments, rare-letter suppression, GPS coincidences, or local stationarity as proof.

## Reproduction

```bash
cd kryptos
python3 audit_pk10_architecture.py
```

The audit checks the official length, Hill divisibility/alignment, and labels the legacy 7/8/9 record as architecture-incompatible. It does not claim a plaintext.
