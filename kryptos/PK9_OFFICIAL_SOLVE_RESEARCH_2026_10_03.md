# PK9 official-solve research and recovery record — 2026-10-03/04

**Local verification status: SOLVED.**

This record preserves the evidence trail from the initial public solve report
to the independently reproduced construction:

1. Paradigm's public PK9 leaderboard recorded a successful submission, led by
   `@LazlosBatForm` at 2026-10-02 22:29Z.
2. The public TTFH/KRYPTOS implementation later exposed the exact construction
   and plaintext.
3. This repository independently reimplemented the operations and reproduces
   all 144 ciphertext characters in both forward and reverse directions using
   `kryptos/verify_pk9_solution.py`.

The earlier local-unverified boundary was correct before the construction was
published; it is superseded by the exact round-trip recorded below.

## Public evidence

The official challenge page is:

- <https://paradigm.xyz/kryptos-ctf/pk9>

The page was directly retrievable during this investigation, but one retrieval
path rendered an old `0 Total Attempts` / `No solvers yet` state. The same
official URL is currently indexed with the following leaderboard data:

| Rank | Player | Solved (UTC) | First attempt | Attempts |
|---:|---|---|---|---:|
| 1 | `@LazlosBatForm` | 2026-10-02 22:29Z | 2026-10-02 22:29Z | 1 |
| 2 | `@forwardsecrecy` | 2026-10-02 22:48Z | 2026-06-12 23:02Z | 2 |
| 3 | `@mi_louk` | 2026-10-02 22:48Z | 2026-10-02 22:48Z | 1 |
| 4 | `@l_ju_l` | 2026-10-02 22:49Z | 2026-10-02 22:49Z | 1 |
| 5 | `@robb` | 2026-10-02 22:50Z | 2026-10-02 22:50Z | 1 |

The indexed page reports **145 total attempts** and a `PK9 Solve` event on
2026-10-02. A contemporaneous public announcement by Dan Robinson independently
states that PK9 and PK10 had fallen:

- <https://x.com/danrobinson/status/2106170838890553553>

A later public account also says its PK9 and PK10 submissions were accepted by
the site's checker on 2026-10-03:

- <https://github.com/TheBenMeadows/tbm/pull/196>

These sources establish a public solve event and accepted submissions. They do
not publish the answer material needed for an independent reconstruction.

## Recovered construction and plaintext

The canonical PK9 ciphertext is 144 characters and has SHA-256
`4871cfc214984051f09982d000af4fec8a6deea66458776e3a6af0bfd0abaa1e`:

```text
KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD
```

The public reference construction is:

```text
Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)
```

Q3 uses `KRYPTOSABCDEFGHIJLMNQUVWXZ` as both top and replacement alphabet.
The spiral traverses a 12×12 row-wise grid from its top-right cell in the
order down, left, up, right. T(8) fills row-wise, applies the distinct-letter
keyword `BEAMWORK`, and reads columns top-to-bottom. The normalized plaintext
is:

```text
ISPENTTHEPASTMONTHWITHTHENEEDLEANDKNOTANDATLASTPELLEGRINSFINALMESSAGEHASBEENREVEALEDTOMEIWILLNOWSEALITFORYOUUNDEREVERYCIPHERIUSEDINTHISTESTAMENT
```

Plaintext SHA-256:
`c8e1b8907795acf780cbab42ec23191051dfb2fdccbfb1adbe875fe8dc03f1d8`.
The repository verifier reproduces the exact 144/144 forward and reverse
round trips. Source: TTFH/KRYPTOS commit
`496976ebe008f9a5eaef8c52bb8ad06c3a4917f5`, `src/ctf/PK9.h`; the local
implementation is independent.

## Rejected local material

The older `EARTH IS KEY` / period-28 / `Q4 ⊕ Q7` / 12×12 material remains an
archival, explicitly unverified candidate. It is inconsistent with the
published PK9 specification and does not provide an exact 144/144 round trip.
Its readable fragments and language scores are not evidence of the official
solution.

Likewise, `kryptos/pk9_solution_plaintext.txt`, `kryptos/pk9_solution_pt.txt`,
and the answer-free optimizer `kryptos/pk9_joint_quad_sa.c` are historical
attack outputs/tools, not canonical answers. They contain no accepted exact
forward/reverse proof and remain excluded from both solution manifests.

## Verification gate — passed

`kryptos/verify_pk9_solution.py` demonstrates all required checks:

1. the construction decrypts the official ciphertext to exactly 144 normalized
   plaintext characters;
2. the same construction re-encrypts that plaintext to the exact ciphertext,
   character for character;
3. reverse decryption and forward encryption agree without hidden padding or
   truncation;
4. the key material, transposition convention, alphabet, phase, and direction
   are recorded in the verifier and canonical manifest; and
5. the implementation is an independent reimplementation of the public
   reference construction.

PK9 is therefore included in `pk_verified_solutions.json` and
`pk_submission_manifest.json`. The historical candidates remain excluded from
the canonical answer and are preserved only as labelled research history.
