# Public solver UI and local investigations

This changes `ventures/cipher-solver-web/`, the public, browser-only solver—not
the packaged Python desktop frontend. `build_pages.py` generates the shared
shell/navigation on every page; `scripts/build_site.py` mounts it alongside the
Kryptos app. The homepage order remains solver, limitations, wiki and technical
explanations. There is no new marketing hero or remote analysis service.

## Simple first, advanced on demand

On phones the header/navigation is compact, ciphertext uses a readable 16px
input, and Solve is a full-width 48px action. Solver / Wiki / Kryptos stay in
primary navigation; secondary tools/history are in a native **More tools**
disclosure. Keyboard focus, explicit labels, reduced-motion settings and 44px
interactive targets are preserved. The input is not silently truncated: requests
above 20,000 characters are rejected with guidance.

An on-demand **What changed?** improvements dialog is available inside Advanced.
It lists the interface/navigation, wiki and local-history updates without
interrupting beginners or writing a version/dismissal preference.

The initial interaction is paste and Solve (Ctrl/⌘+Enter also works). **Advanced
settings & examples** is closed initially. It exposes:

- An actual method selector, rather than a family-shaped sample masquerading as
  a selected algorithm; default is auto-detect.
- Optional supplied keys, direct-only / up to three encoding layers.
- **Explore more cipher families**, a slower opt-in to additional root attacks.
- Passive example loading and Clear (resets current input/settings/results).

The worker owns expensive calculations. **Stop search** terminates it; request
identities discard older queued messages. A worker creation/load failure restores
the controls and suggests serving the site instead of opening an HTML file.

Completed results scroll to the candidate, respecting reduced-motion. Plaintext
is fully present/copyable in a bounded scrolling box. **Key, method, ranking &
evidence**, **Input statistics & identification**, **Candidate rankings**, and
**Limitations & next checks** are separate closed disclosures. Switching Top
5/10 does not launch another search. Rankings are actual returned candidates;
none are fabricated when the list is short. Every method may internally
shortlist, and recursive branches retain their best candidate: the list is not
exhaustive. Broader-family comparison expands root work, not every recursive
branch, to avoid exploding a mobile search. Stop remains available.

Statistical candidates and supplied-key readings are explicitly unproven.
Scores/close-score gaps are heuristics, not probabilities. Green corpus labels
are derived from exact original-source/text/key/cipher agreement with the shipped
PK catalog, not stored `verified` flags. Direct corpus recognition returns one
reference, rather than invented competitors.

## Wiki → solver

Each of the 51 registry cipher articles has a prominent **Try this cipher** link
near its heading. It opens:

```
index.html?cipher=<registry-name>&example=<registry-name>#solver
```

Only public IDs appear in the URL—not private ciphertext or keys. IDs are
whitelisted against `examples.js`. The link selects the relevant method and
loads the **full** generated worked example with its documented key, without
automatically running or saving it. It does not substitute a Caesar sample for
an unsupported method. Article layout remains article-first.

`build_pages.write_examples()` encrypts and decrypts examples using each Python
registry cipher, preserving its complete ciphertext and actual recovered output
(including padding/lossy conventions). This avoids the infobox's shortened
preview. The generated asset is shared by the UI and worker. Query-aware internal
link checks validate the true destination and fragment, not the query string as
a filename.

### Live operations vs reference demonstrations

Supplied-key browser operations cover Caesar; Vigenère, Beaufort, Variant
Beaufort, Porta, Gronsfeld; autokey; additive KRYPTOS-alphabet Quagmire III; affine
(`a=5,b=8`); and Trithemius (`start=0, step=1`). Fixed/encoding operations include
Atbash, ROT13, reverse, Base64, hex, binary, decimal bytes and Morse. Selected
key-recovery attacks use only that method; periodic-family searches are filtered
to the requested variant. Quagmire III supplied-key operations use the fixed
KRYPTOS alphabet; other tableaux need other tools.

Not every Python/wiki cipher has an executable browser attack or supplied-key
implementation. For an **unchanged worked example**, with its exact method,
example ID and key, those cases may return **Worked example reference — not a
new solve**: the actual Python-generated reference decryption is a lookup, not
live execution or newly recovered plaintext. Current tests exercise 18 live
example operations and 33 explicit reference demonstrations. Editing the text
or key disables that lookup. Unsupported unrelated input returns no candidate
and coverage guidance; it never quietly runs another family. Manual invalid keys
are rejected rather than silently ignored or guessed. Auto mode rejects a
supplied key until a specific method is selected.

## Optional local history

**Optional local investigations** is closed initially. Solving, typing, example
loading, restoration and page load never write history. Users explicitly:

1. Solve (or restore) a result.
2. Open local investigations and enter a name.
3. Select **New investigation**, or an existing investigation to append an attempt.
4. Click **Save current result**.

Each attempt keeps the exact submitted ciphertext, requested method/key/depth,
comparison option, identification metrics, actual candidate shortlist,
diagnostics, elapsed time and timestamp. If input is edited while/after solving,
the saved result still belongs to its submitted snapshot—not the newer draft.
The UI calls out an input change during a running solve.

Choose an investigation to inspect attempts, compare A/B, or **Restore text,
settings & result** without invoking a worker. Restored results are prominently
labelled archived snapshots, not new searches or independent verification.
Candidate proof flags are dropped during schema validation; direct canonical
badges are re-derived from the shipped catalog when rendered. Saved language
scores are historical observations, not newly recomputed evidence.

Comparison shows requested/reported methods and keys plus readable plaintexts
side by side (stacked on phones). Different original inputs trigger a warning
that score comparisons are not directly meaningful. Clear current input leaves
saved investigations intact. Delete one attempt or one/all saved investigations requires
confirmation and does not remove the currently displayed result.

## Backups, limits and failure behavior

Storage key: `buttcrack.browser.investigations.v1`.
Backup schema: `browser-investigations/v1`.
A separately exportable current attempt uses `browser-attempt/v1`; it can be
exported without writing browser storage, including when storage is full.

History is limited to **12 investigations**, **10 attempts each**, **10 returned
candidates per attempt**, **20,000 ciphertext/candidate characters** and a
**2,000,000-character serialized history**. Import is limited to 4 MB. Names have
a 100-character limit; manual keys have a 512-character limit. Oversized or
invalid records, unknown methods, future schemas, duplicate IDs, nonfinite
measurements and null ranked candidates are rejected before writing.

Export local backups before clearing browser data. Import validates the entire
backup, asks before replacing history, and discards proof flags. There is no
automatic merge or cloud synchronization. Browser storage writes are atomic:
a rejected/quota write retains prior history. A corrupt/future history is not
automatically overwritten; users can export its raw backup before explicit reset.
The current result remains usable if history is unavailable/full.

Named investigations include keys, plaintext and ciphertext. Local storage is
not encrypted, is shared by scripts on the same origin, and is lost when browser
data is cleared. Research/solver code makes no analysis upload; the existing
hosted site's advertising scripts are outside that guarantee. For sensitive
work, use a locally served/offline copy. No session data is put in URL queries,
telemetry, remote APIs or automatic exports by this implementation.

## Validation

`npm run test:web` covers all 51 worked examples, live/reference scope, selected
method routing, legacy-auto compatibility, actual candidate collection, corpus
boundaries and history validation. `tests/browser/public-experience.spec.js`
exercises the actual pages/workers at a mobile viewport, wiki navigation, explicit
history, comparison and restoration. CI runs the deterministic web tests alongside
Kryptos tests before Playwright. Local DOM tests additionally check stale-worker
rejection, quota rollback, safe rendering and backup restore. Real browser/layout
validation is separate from DOM execution.
