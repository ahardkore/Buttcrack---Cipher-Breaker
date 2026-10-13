# tlock-kit — opening `what-is-locked.age`

**TL;DR.** The pasted file is an [age](https://age-encryption.org) file whose single
key is time-locked with [tlock](https://github.com/drand/tlock) to **drand** round
**33542211**. The key is the League of Entropy's threshold BLS signature of that
round, and that signature will not exist until the round is emitted at

> ## 2026-10-31 06:59:57 UTC

(≈17.9 days after this analysis, on 2026-10-13). There is **no password, no key
and no weakness to brute-force** — the lock is a time gate, so the honest answer
to “break this” is: *it opens itself on Halloween morning UTC; here is the
verified kit that does it the moment the round exists.*

You get two independent ways to open it on unlock day: a tested Node CLI
(`unlock.mjs`) and a zero-install browser page (`web/index.html`). Both are
validated end-to-end against real drand data (19/19 checks, §5).

Your intuition — “it works similar to bitcoin” — is half right, and the half
that's right is the important half. drand publishes a new round every **3
seconds** on a fixed, pre-agreed schedule, like blocks; the file's key is bound
to one specific future round, so its availability is chain-timed exactly like a
timelocked Bitcoin transaction. The difference: there is no mining and no
proof-of-work anywhere — the rounds are signed by the threshold key of a
consortium of 16+ independent organizations (Cloudflare, EPFL, UChicago, …), so
there is nothing to out-compute and no faster machine lets you jump ahead.

---

## 1. What the file actually is (evidence)

Decoding the armor of the pasted block gives:

```
age-encryption.org/v1
-> tlock 33542211 52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
pW785uBPLzqhyPHMb4LLlowr5sViQtA7X95Bsp7CN8mJm2vxzrvmXoH1GBrfc4KR
...
-> ,6p*m.7-grease  !+naI krm 8G
...
```

* **age v1**, ASCII-armored.
* Exactly one real recipient stanza: `tlock 33542211 <chain>` (the other stanza
  is age's mandatory "grease", which carries no key material).
* The chain hash `52db9ba7…4e971` is drand **quicknet** (League of Entropy
  mainnet): 3-second rounds, BLS12-381 unchained scheme, genesis 2023-08-23.
* **No passphrase/scrypt stanza, no X25519 or SSH recipient** → nothing to crack
  with hashcat/John, and `buttcrack` (classical ciphers: Caesar, Vigenère,
  transposition, Kryptos research, …) has no mechanism that can touch it. That is
  why the desktop app was unsuccessful on this file — no classical-cipher tool
  can ever open it, regardless of settings.

## 2. Why it cannot be opened before round 33542211

tlock is **identity-based encryption** with the drand round number as the
identity. Encryption needs only the chain's public key (available to everyone,
yourself included — hence anyone can *make* such a file). Decryption needs the
per-round private key, which is produced by the League of Entropy only when it
threshold-signs that round — 33542211 simply hasn't happened yet. Until then the
key exists nowhere, on no disk and in no memory, and no amount of compute can
fake a BLS signature for it. After 06:59:57 UTC on 2026-10-31 the round's
signature is public and the file decrypts instantly (the math takes
milliseconds). Note the round is emitted at that timestamp — give it a minute or
two before retrying if the very first attempt is a hair early.

## 3. How to open it — step by step

Two ways. **Option A** is the CLI kit; **Option B** is a page you open in a
browser (also the preview served by this workspace) — no install needed. Both
run locally, and both do the same verified decryption.

### Option A — CLI (Node ≥ 18), from this `tlock-kit` folder

```bash
npm install                      # once — installs tlock-js 0.9.0 (drand's own library)
# save the BEGIN AGE ENCRYPTED FILE … END block from chat as what-is-locked.age
node unlock.mjs what-is-locked.age
```

Before the unlock round, that exits with a clear message and status **LOCKED**
(plus the exact unlock timestamp). From 2026-10-31 06:59:57 UTC onward it prints

```
UNLOCKED ✓  plaintext written to what-is-locked.txt (…bytes)
--- first 4000 bytes ---
…
```

and leaves the full plaintext in `what-is-locked.txt`.

Prefer to check the status without attempting decryption at all? The same script
already reports it — it never fails anywhere except the (expected) “too early”
path, and never corrupts anything.

### Option B — browser page (no install)

`web/index.html` decrypts completely client-side: drag the `.age` file in, it
reads the round from the file, shows a live countdown to the unlock moment from
the real chain, and unlocks with one click when the round exists. The file never
leaves the machine; the only network request is a fetch of the beacon from the
drand API you select.

```bash
npm run serve:web        # → http://localhost:4173   (any static server works)
```

…or simply **double-click `web/index.html`** — the page ships with its bundled
`app.bundle.js`, so it works from `file://` too. It also has an **offline mode**:
if your browser cannot reach the drand API (CORS/network), save the beacon JSON
from `<api>/public/33542211` in a tab and load it into the page; decryption then
needs no network at all.

### Option C — start it and forget it (watch mode)

Don't want to be awake at the unlock moment? Start the watcher and walk away:

```bash
nohup node watch.mjs what-is-locked.age > watch.log 2>&1 &   # then: tail -f watch.log
```

It asks drand every 15 s for the latest round, prints a live countdown, and the
instant round 33542211 exists it decrypts and writes `what-is-locked.txt`
(exit 0). The chain — not your local clock — decides when that is, so a skewed
clock can never fire it early. `WATCH_INTERVAL_MS=3000` polls faster near the
end. Prefer a nudge instead? Import `unlock-reminder.ics` into your calendar.

### No network on unlock day? (offline mode)

1. On any machine with a browser/open internet, open:
   `https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/33542211`
   and save the JSON exactly as served (e.g. `beacon-33542211.json`).
2. On the offline machine:
   ```bash
   node verify-beacon.mjs beacon-33542211.json     # optional but recommended
   node offline.mjs what-is-locked.age beacon-33542211.json
   ```
   `offline.mjs` does the whole decryption from the JSON alone — no network — and
   still cryptographically verifies the beacon before using it, so a tampered or
   wrong-round file fails loudly instead of producing garbage.

### If api.drand.sh is blocked in your network

Everything above takes `DRAND_CHAIN_URL`, e.g.:

```bash
DRAND_CHAIN_URL=https://drand.cloudflare.com/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971 node unlock.mjs what-is-locked.age
# also: https://api2.drand.sh/<chain>   https://api3.drand.sh/<chain>
```

## 4. Unlock moment around the world

| Zone | Local time of unlock |
|---|---|
| UTC | 2026-10-31 06:59:57 |
| Central Europe (CET, UTC+1) | 2026-10-31 07:59:57 |
| US Eastern (EDT, UTC−4) | 2026-10-31 02:59:57 |
| US Pacific (PDT, UTC−7) | 2026-10-30 23:59:57 |
| India (IST, UTC+5:30) | 2026-10-31 12:29:57 |
| China (CST, UTC+8) | 2026-10-31 14:59:57 |
| Japan (JST, UTC+9) | 2026-10-31 15:59:57 |
| Sydney (AEDT, UTC+11) | 2026-10-31 17:59:57 |

## 5. How this kit was verified (all offline, against real drand data)

`npm test` runs `test/run-tests.mjs`, which serves a **real** captured chain
info and a **real** published beacon (round 33025409, real BLS signature) from a
local mock API, then exercises the genuine code path:

```
PASS  roundTime(33542211) == 2026-10-31T06:59:57Z  — library says 2026-10-31T06:59:57.000Z
PASS  real beacon 33025409 verifies against quicknet public key
PASS  tampered beacon is rejected
PASS  encrypt→decrypt round trip on real published round 33025409
PASS  round 33542211 still locked  — It's too early to decrypt the ciphertext - decryptable at round 33542211
PASS  unlock.mjs decrypts the canary (exit 0)
PASS  unlock.mjs correctly reports LOCKED with the unlock date (exit 2)
PASS  offline.mjs decrypts from beacon JSON alone (exit 0)
PASS  verify-beacon.mjs accepts the real beacon
PASS  verify-beacon.mjs rejects the tampered beacon
PASS  web core: parses round + chain from the armored file
PASS  web core: browser decrypt path reproduces the canary
PASS  web core: countdown formatting
PASS  web bundle built (web/app.bundle.js)
PASS  real file header: parser reads round 33542211 + quicknet chain  — {"round":33542211,"chainHash":"52db9ba70e…"}
PASS  real file header: decoded stanza text matches
PASS  real file header: grease stanza present (no key material)
PASS  watch.mjs auto-decrypts when the round is already published (exit 0)
PASS  watch.mjs keeps waiting on a locked file and reports the countdown

ALL CHECKS PASSED ✔  — kit validated end-to-end against real drand data.
```

In other words: the tooling was proven to work by round-tripping a canary
through the identical encrypt/decrypt path, and the target round was proven
still locked with the library's own error — the same error your file produces
today, through no fault of the file.

## 6. Files in this kit

| File | Purpose |
|---|---|
| `unlock.mjs` | status + decryption (online; uses drand API, verifies beacon) |
| `offline.mjs` | decryption from a saved beacon JSON (no network; verifies beacon) |
| `verify-beacon.mjs` | check a beacon JSON's BLS signature against quicknet's key |
| `web/index.html` | browser unlocker (drag & drop, countdown, offline beacon mode) |
| `web/app.bundle.js` | self-contained bundle of `web/src/*` (committed so `file://` works) |
| `web/src/core.js`, `web/src/app.js` | browser logic (core is unit-tested by the suite) |
| `web/serve.mjs` | tiny static server: `npm run serve:web` |
| `watch.mjs` | start-and-forget watcher: polls the chain and decrypts automatically the moment the round lands |
| `fixtures/target-header.b64` | the first 8 armor lines of your actual file — the parser is tested against these real bytes |
| `unlock-reminder.ics` | calendar event with an alarm ~1 minute before 06:59:57Z |
| `mock/drand-server.mjs` | local API replica used by the tests (serves the real captured data) |
| `test/run-tests.mjs` | the 10 checks above — `npm test` |
| `evidence/round-info.txt` | the full target analysis (stanza, math, observed state) |
| `evidence/quicknet-info.json` | real chain info captured 2026-10-13 |
| `evidence/beacon-33025409.json` | real published beacon used to validate decryption |
| `evidence/test-run.log` | captured output of the passing test suite |

## 7. Honest caveats

* The file's **full ciphertext never reached this workspace** (it exists only as
  the chat paste; tooling here truncated a single ~180 KB write). The analysis
  above used the decoded header, which is all that's needed to establish the
  mechanism and unlock time. Drop the `.age` file into this folder —
  `what-is-locked.age` — and everything is ready to go; and on/after
  2026-10-31 simply run it.
* Do not trust third-party “drand unlock” sites with this file; keep decryption
  local (this kit does everything on your machine; the only external call any
  script makes is to a drand API you choose).
* `tlock` v0.1.0-era ciphertexts are **not** compatible with v1.x rules — this
  file's stanza uses the current chain hash and `tlock-js 0.9.0` reads it
  unchanged; nothing to convert.
* Keep a note somewhere loud: **2026-10-31, 06:59:57 UTC**.
