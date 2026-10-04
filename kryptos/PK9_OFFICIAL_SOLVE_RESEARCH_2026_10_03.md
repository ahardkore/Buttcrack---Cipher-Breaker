# PK9 official-solve research record — 2026-10-03

**Local verification status: UNVERIFIED.**

This record separates two facts that must not be conflated:

1. Paradigm's public PK9 leaderboard now records a successful submission.
2. This repository still has no plaintext, complete key material, or construction
   that can be independently re-encrypted to all 144 published ciphertext
   characters.

The first fact is enough to correct the repository's description of the public
record. It is **not** enough to promote a local PK9 answer to
`pk_verified_solutions.json` or to mark the local verifier as passing.

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

## What has not been recovered

The canonical PK9 ciphertext is 144 characters and has SHA-256
`4871cfc214984051f09982d000af4fec8a6deea66458776e3a6af0bfd0abaa1e`:

```text
KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD
```

No public source located during this investigation supplies all of the
following as one reproducible answer:

- the exact 144-character plaintext;
- the three Q-wheel values/keys for Q(7), Q(6), and Q(5);
- the complete T(8) transposition key or permutation;
- normalization, padding, alphabet, and phase conventions;
- both forward encryption and reverse-decryption directions.

The published construction notation remains `Q(7)Q(6)Q(5)T(8)`. The repository's
exact-crib, word-wheel, and layer-order campaigns documented in
`PK9_SESSION_2026_10_02_GROUND_TRUTH_AND_SWEEPS.md` remain useful negative
results for the tested candidate families, but they do not disprove the
official construction or its plaintext.

## Rejected local material

The older `EARTH IS KEY` / period-28 / `Q4 ⊕ Q7` / 12×12 material remains an
archival, explicitly unverified candidate. It is inconsistent with the
published PK9 specification and does not provide an exact 144/144 round trip.
Its readable fragments and language scores are not evidence of the official
solution.

Likewise, `kryptos/pk9_solution_plaintext.txt` and
`kryptos/pk9_solution_pt.txt` are historical attack outputs, not canonical
answers. They contain no accepted exact forward/reverse proof and remain
excluded from both solution manifests.

## Verification gate and next steps

PK9 will only be promoted after a fresh, independent verifier demonstrates all
of the following:

1. the claimed construction decrypts the official ciphertext to exactly 144
   normalized plaintext characters;
2. the same construction re-encrypts that plaintext to the exact ciphertext
   above, character for character;
3. reverse decryption and forward encryption agree without a hidden padding or
   truncation exception;
4. the key material, transposition convention, alphabet, phase, and direction
   are recorded in machine-readable form; and
5. a second implementation or independently audited calculation reproduces the
   same result.

Until that evidence is public or independently recovered, the repository's
canonical status is **official solve reported, construction and answer locally
unverified**. PK9 must not be added to `pk_verified_solutions.json`, and the
historical candidates must not be presented as its plaintext.
