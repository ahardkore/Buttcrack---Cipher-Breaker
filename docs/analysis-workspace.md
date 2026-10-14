# Interactive analysis workspace

Available in the local browser UI and the desktop application's browser-backed
interface. It needs no plotting library, external service, optional crypto
provider, or extra data downloads.

## Using it

- **Analyze current input only** analyzes the current input without carrying
  over any plaintext or key from a previous solve. This also works before solving.
- A completed solve automatically analyzes its first candidate against the
  **ciphertext captured when that solve was submitted**, not subsequently edited
  text. Choose any returned candidate in the workspace selector, or use its
  **Analyze this candidate** button. Changing Top 5/10 does not rerun the solver.
- Adjust the maximum tested period (2–40). Switch the repeat/period source between
  ciphertext and the selected plaintext without a new request. Ciphertext at the
  correct input layer is normally the relevant source for Vigenère lengths;
  residual plaintext periods are only diagnostic.
- Edit the alignment convention, key hypothesis, phase or first displayed letter
  and press **Apply alignment settings**. Alignment displays up to 80 positions
  in 20-letter blocks, with ciphertext, plaintext and key sequences side by side.
  Dots mean missing letters; underlined red ciphertext characters mark arithmetic
  disagreements. Display offsets do not reset the repeated key's phase.
- Clearing the results or starting another solve aborts the workspace request
  and clears its context. Aborted/older replies cannot overwrite newer analysis.
  An unavailable/busy analysis endpoint leaves existing solver results unchanged.

The workspace makes no changes to candidate ordering, confidence, verification,
solver search options or exported reports. It adds no local-storage/session
persistence. Requests go to the same local process via relative URLs.

## Measurements and normalization

Each text has an explicit sample count and 26 A–Z frequency counts/proportions.
The chart uses **one shared scale**, cyan for ciphertext and gold for plaintext.
Counts and percentages also appear as text, not only colored bars.

Only ASCII A–Z/a–z letters are retained and case folded. Spaces, punctuation,
digits and non-ASCII letters are removed, with no Unicode uppercase expansion
or transliteration. Every repeat/alignment position and key offset is zero-based
in this **normalized letter stream**, not the original file's character positions.
This can differ from a solver's cipher-specific preparation.

For letter counts `n_i` and total `N`, IC is `Σ n_i(n_i−1) / N(N−1)`.
It is not measurable below two letters. Shannon entropy is `−Σ p_i log2(p_i)`:

- **Letter entropy** is in bits per normalized A–Z letter.
- **Input-character entropy** is in bits per raw Unicode character of the
  examined prefix, including layout/case/punctuation. It is **not byte entropy**.

Empty entropy is not measurable; a single symbol has zero entropy. Entropy is a
marginal distribution measurement, not message unpredictability or proof of
randomness. Transposition preserves letter frequencies, letter IC and letter
entropy, so these measurements alone cannot rule it out.

The language reference is the selected/report language's monogram model.
Uniform-random letter IC is `1/26`; auto/detect defaults explicitly to the English
reference. A reference is an assumption, not language or cipher identification.

## Repeats, periods and Vigenère length hypotheses

The repeated-pattern table finds overlapping 3–5-letter patterns. It shows total
occurrences, the first 20 positions, adjacent stored-position distances, and
factors between 2 and the chosen maximum period. Each distinct pattern votes
once for each compatible period. Votes use all detected repeated patterns,
though only the top 30 patterns are displayed. This is a bounded Kasiski view,
**not** an all-pairs spacing calculation; overlaps are not independent evidence.

Each tested period splits the letters into interleaved columns and reports:

- Pooled-pair **weighted column IC**, `Σcolumn Σletter n_i(n_i−1) /
  Σcolumn N_column(N_column−1)`.
- Arithmetic mean of the column ICs, **including zero-valued ICs**.
- Shortest/average column size and a short-sample warning.
- Equal-letter matches at that lag divided by the number of compared pairs.
- Bounded Kasiski votes.

Periods run from 1 through `min(max_period, N // 2)`, so columns have at least two
letters. The top ten length hypotheses use this deliberately exposed formula:

```
adequacy = min(1, shortest column / 12)
ic_lift = clip((weighted_IC - 1/26) / (language_reference_IC - 1/26), 0, 1)
relative_votes = period_votes / largest_vote_count  # 0 when no votes
support = adequacy * (0.8 * ic_lift + 0.2 * relative_votes)
```

The IC denominator has a small positive floor. This support value is **not a
probability, significance test, solver confidence, or recovered key**. Equal
scores favor shorter periods. Shorter divisors with at least 93% of a displayed
hypothesis's support are highlighted for inspection. Multiples can share peaks;
repeats also occur by chance. Fewer than 60 letters or fewer than six letters in
the shortest column is flagged as particularly unreliable. Low letter diversity
gets its own warning.

Length estimates assume repeated-key polyalphabetic encryption, the correct
input layer and a relevant language. They do not establish Vigenère attribution;
plaintext repetition, transposition, encodings and other constructions can also
produce peaks. Autokey and keyed alphabets require other models.

## Alignment conventions and verification boundary

Automatic equation checking is limited to direct, non-layered reported ciphers:

| Convention | Encryption equation (A=0, modulo 26) | Key input |
|---|---|---|
| Vigenère | `C = P + K` | ASCII letters |
| Beaufort | `C = K − P` | ASCII letters |
| Variant Beaufort | `C = P − K` | ASCII letters |
| Gronsfeld | `C = P + K` | Decimal digits, shown as A–J |
| Caesar | `C = P + shift` | Integer 0–25, shown as one letter |

At normalized letter position `i`, the repeated key uses
`(i + phase_offset) % key_length`. The view reports equations checked and
mismatches **in the displayed window only**, plus unequal normalized lengths.
Even zero mismatches is only agreement with the selected equation: it is not
independent verification, full-message round-trip verification, authenticity or
proof of intended plaintext.

For layered, transposition, autokey, keyed-alphabet and unsupported constructions,
automatic mode shows positions but does **not** invent a repeating-key equation.
Choosing a manual convention explicitly tests a separate user hypothesis, not
an attribution made by the solver. The candidate's actual reported key/parameters
remain available in its results card.

## Bounds and local API

`POST /api/analysis-workspace` accepts a JSON object with `ciphertext`, optional
`plaintext`, `language`, `max_period`, `cipher`, `steps`, `key`, `alignment_model`,
`key_offset`, `alignment_start`, and `alignment_count`. The UI uses the same
Host/Origin/body-size protections as the other local endpoints. Concurrent
analysis/lab work shares the two-slot semaphore; a busy server returns 429.
Invalid settings return 400 and release the slot.

- First **16,000 raw characters** and **8,000 ASCII letters** per text.
- First **20 positions** per pattern; at most **30 displayed repeats**.
- Period maximum **40**, up to **10** displayed length hypotheses.
- Key at most **128 characters**; phase **0–127**.
- Display start **0–8,000**; API window **1–160** (UI uses 80).

Frontend-prefix truncation flags (`ciphertext_truncated`, `plaintext_truncated`)
ensure sampling warnings remain visible even when the browser caps its request.
The full candidate plaintext remains in the results panel. Avoid interpreting
a sampled alignment as verification of an entire message.
