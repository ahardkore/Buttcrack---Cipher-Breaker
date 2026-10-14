# Explicit offline crypto labs

Open **Crypto Labs** in the local browser interface, or use the desktop's
**Crypto Labs** button / Labs menu. The four labs are presented in this order:
RSA, reused keystream, AES, Enigma. Each has an educational example and a clear
button. No lab inputs or keys are saved to browser storage or project files.
Requests go only to the local server; none of these labs use a remote oracle.
Use your own data or authorized exercises.

These are **not four new automatic cipher-breaker entries**. Secure modern
cryptography cannot be recovered from ciphertext alone by these methods. Inputs
must specify the actual parameters, and results explain their assumptions and
limitations. Enigma is historical, not modern encryption.

## 1. RSA weaknesses

Input: a `keys` array of objects with `n` (modulus), `e` (public exponent) and
optionally `c` (one **raw RSA integer**, not an encoded/padded message container).
Use decimal strings or `0x`-prefixed strings for large integers; JSON numbers in
browsers lose precision beyond 2^53−1. The interface rejects unsafe numbers.

Checks:

- Pairwise GCD for shared factors across supplied moduli. Identical moduli alone
  do not establish a factorization.
- Bounded Fermat search for unusually close factors (default 1,000 candidates per
  modulus, maximum 20,000; set `fermat_steps: 0` to skip).
- Wiener's continued-fraction attack for an unusually small private exponent.
- Exact integer roots when a low-exponent raw message has not wrapped modulo n.
- Low-exponent broadcast recovery for the same unpadded message encrypted under
  enough pairwise-coprime moduli with exponent 3, 5 or 7. All supplied members
  with that exponent are checked against the candidate; this is not a search
  for arbitrary subsets of matching messages.

Factors are checked by multiplication. Private-key derivation is attempted only
for distinct factors passing prime checks (deterministic below 2^64, probable
prime checks above that). Recovered raw plaintext is checked by re-encryption.
This verifies arithmetic, **not authentication, padding, or intended meaning**.
Leading zero bytes cannot be recovered from a bare integer without an external
length. No OAEP or PKCS#1 unpadding is attempted.

Limits: 1–32 keys, integers at most 4,096 bits, a 0.1–5 second search budget
(default 3). Budget checks occur between arithmetic operations, so this is a
cooperative search budget, not an interruptible wall-clock guarantee. A negative
result means only that these tests found no weakness; it is not a security audit.

Example input (`rsa.json`):

```json
{"keys":[{"n":"3233","e":"17","c":"2790"},{"n":"2867","e":"17"}],"fermat_steps":1000,"budget":3}
```

This intentionally tiny shared-prime example recovers raw plaintext integer 65
(`A`) for the first key. Do not use these parameters for real encryption.

## 2. Reused keystream

Input: a `ciphertexts` array of 2–16 hex strings, aligned to the same keystream
positions. The relation is `C1 XOR C2 = P1 XOR P2` **if the same keystream was
used**. Computing an XOR alone does not prove that prerequisite.

An optional UTF-8 `crib`, zero-based `message_index`, and byte `offset` derive an
implied keystream fragment and corresponding plaintext fragments in the other
messages. The lab labels all fragments as hypotheses. A wrong crib can produce
wrong plaintext while still satisfying every XOR relation. It does not score a
plausible reading as a verified solve or automatically recover the whole stream.
Offsets refer to bytes, not characters; each ciphertext is limited to 4,096 bytes.

This applies to reused one-time-pad material and to reused key/nonce combinations
in stream encryption, including AES-CTR and ChaCha20, **not arbitrary ciphertexts
that happen to have similar lengths**. It does not handle unknown alignment.

## 3. AES block analysis and known-key operations

`operation: "analyze"` compares complete aligned 16-byte blocks in hex `data`.
Repeated blocks are consistent with ECB, but do not prove AES or ECB; no repeats
does not rule out ECB. This feature needs neither a provider nor a key.

`operation: "encrypt"` or `"decrypt"` uses a **supplied key** through the maintained
`cryptography` provider. There is no homemade AES primitive and no key search.

- `key`: 16, 24 or 32 bytes of hex.
- `mode`: `ECB`, `CBC`, `CTR`, or `GCM` (default).
- `iv`: absent for ECB; 16-byte IV for CBC; complete 16-byte initial counter block
  for CTR; 12-byte nonce for GCM.
- `tag`: separate 16-byte GCM tag for decryption; absent for encryption.
- `aad`: additional authenticated data in hex for GCM only.
- `padding`: JSON boolean, default false; optional PKCS#7 for ECB/CBC only.
- `data`: hex bytes, maximum 16,384 bytes. Unpadded ECB/CBC requires whole blocks.

GCM authentication must pass before **any plaintext** is returned. A wrong key,
nonce, tag, AAD or modified ciphertext produces an error. ECB/CBC/CTR output is
unauthenticated: successful decryption, valid padding, and even an exact
re-encryption do not establish that the key or plaintext is intended/correct.

Never reuse a GCM nonce or CTR counter stream with the same key. Examples are
public known-answer test material, **not production encryption guidance**.

Source installs need the optional extra for AES operations:

```console
pip install ".[modern]"
```

The Windows build installs the provider into its isolated build environment and
bundles it; end users do not install Python or fetch dependencies. Both the frozen
build and installed CLI are checked against an AES known-answer vector. Provider
license texts are included in the bundle. Core solving and the other labs still
work without the provider, and a missing provider produces a clear AES error.

## 4. Enigma I

Supported: three distinct rotors from I–V (left to right), reflector B/C, three
letter `rings` (A=01), three initial `positions`, and up to ten disjoint
space-separated plugboard pairs. The simulator steps **before** each character
and implements the middle rotor's double step. Ring settings shift electrical
wiring, not the turnover notch's displayed letter.

`operation: "transform"` encrypts/decrypts symmetrically with the supplied
configuration. For I/II/III, reflector B, rings AAA, positions AAA and no plugs,
`AAAAA` becomes `BDZGO`, and `HELLOWORLD` becomes `ILBDAAMTAZ`.

`operation: "search"` varies **only initial positions** across at most 17,576
possibilities. Supply a `crib` of at least eight letters and an `offset` in the
space-stripped text; the crib must fit and end in the first 256 letters. Rotor
order, rings, reflector and plugboard are fixed, not searched. Results show how
many positions were examined, whether the search was complete or time-limited,
and up to 20 crib-matching candidates with re-encryption checks. A crib match is
still a candidate, not proof of intended plaintext.

Input is limited to 4,096 ASCII letters/spaces; spaces are removed and punctuation
is rejected. This is not a simulation of every Enigma variant or an unrestricted
Enigma-breaking engine.

## CLI and local API

All four labs use the same backend:

```console
buttcrack modern rsa --input rsa.json
buttcrack modern enigma '{"text":"HELLOWORLD"}'
```

CLI results are JSON; invalid inputs exit with code 2. Input files are read, not
modified. `POST /api/modern` takes `{"lab":"rsa", "options": {...}}` (or
`keystream`, `aes`, `enigma`), behind the existing Host/Origin protections.
Invalid parameters return HTTP 400; at most two lab operations run concurrently
(HTTP 429 when occupied). The labs are separate from automatic language scoring
and do not add misleading confidence scores to modern ciphertext.

## Before releasing

Run unit tests with the AES provider installed, exercise the browser examples,
and build/test the real Windows installer. The current environment's DOM checks
and known-answer tests do not replace a real Windows GUI/install test. Publish
the installer before advertising its version and improvement notes on the site.
