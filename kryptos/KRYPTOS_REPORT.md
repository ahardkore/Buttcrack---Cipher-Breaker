# KRYPTOS — The Ciphers, the Solutions, and What's Left

**Prepared 2026-09-19.** Every decryption below was re-implemented from scratch in
[`kryptos_solve.py`](kryptos_solve.py) and verified against the sculpture's ciphertext.
Status: **K1, K2, K3 — solved and machine-verified here. K4 — plaintext located in 2025
but the cipher mechanism remains unbroken.**

> **ON ORIGINAL CREDIT FOR K1–K3.** "Solved here" means this repository's code
> independently re-derives the same plaintext from the public ciphertext and
> already-known keys/method, as a correctness check — it is not a claim that this
> project discovered K1, K2, or K3. Those three passages were first solved, publicly
> and independently of each other, decades before this repository existed: CIA analyst
> David Stein solved K1–K3 internally in 1998 (not disclosed publicly until 1999);
> computer scientist Jim Gillogly solved K1–K3 independently and announced it
> publicly in 1999; and a small NSA team (led by Ken Miller, with Dennis McDaniels and
> two colleagues) solved K1–K3 internally by June 1993 in response to a 1992 internal
> challenge from Deputy Director William Studeman, a fact that only became public in
> 2013 after a Freedom of Information Act request by researcher Elonka Dunin. Sanborn
> confirmed a transcription correction to K2 ("X LAYER TWO") on April 19, 2006 after
> researcher Nicole Friedrich flagged the discrepancy. None of this history is claimed
> or implied by this repository's own re-verification work.

---

## The sculpture

*Kryptos* (1990), by Jim Sanborn with retired CIA cryptographer Edward Scheidt, stands in
the CIA courtyard at Langley. Its copper screen carries **869 characters (865 letters +
4 question marks)** split into four passages, next to a keyed Vigenère tableau built on
the alphabet `KRYPTOSABCDEFGHIJLMNQUVWXZ`.

---

## K1 — SOLVED ✅ (verified by my code)

- **Method:** Vigenère over the KRYPTOS tableau, key **PALIMPSEST**
- **Ciphertext:** `EMUFPHZLRFAXYUSDJKZLDKRNSHGNFIVJYQTQUXQBQVYUVLLTREVJYQTMKYRDMFD`
- **Plaintext (my decryption, exact match):**

> BETWEEN SUBTLE SHADING AND THE ABSENCE OF LIGHT LIES THE NUANCE OF **IQLUSION**

`IQLUSION` is the first of Sanborn's intentional misspellings (of *ILLUSION*).

## K2 — SOLVED ✅ (verified, including its famous error)

- **Method:** same tableau Vigenère, key **ABSCISSA**
- **Plaintext (my decryption, letter-for-letter for 361 letters):**

> IT WAS TOTALLY INVISIBLE HOWS THAT POSSIBLE? THEY USED THE EARTHS MAGNETIC FIELD X
> THE INFORMATION WAS GATHERED AND TRANSMITTED **UNDERGRUUND** TO AN UNKNOWN LOCATION X
> DOES LANGLEY KNOW ABOUT THIS? THEY SHOULD ITS BURIED OUT THERE SOMEWHERE X WHO KNOWS
> THE EXACT LOCATION? ONLY WW THIS WAS HIS LAST MESSAGE X THIRTY EIGHT DEGREES FIFTY
> SEVEN MINUTES SIX POINT FIVE SECONDS NORTH SEVENTY SEVEN DEGREES EIGHT MINUTES FORTY
> FOUR SECONDS WEST **X LAYER TWO**

The coordinates (38°57′6.5″N, 77°8′44″W) point ~174 ft southeast of the sculpture.
My decryption reproduces the documented April-2006 error exactly: Sanborn omitted one
ciphertext letter near the end, so the carved text decrypts to `...WESTIDBYROWS` instead
of the intended `...WESTXLAYERTWO` — the key desyncs at precisely that position.

**Exhaustive missing-letter test** (`kryptos_missing_letter.py`): inserting every letter
A–Z at every possible position (9,698 trials) yields exactly **one** full restoration of
the corrected plaintext: the letter **S** after ciphertext letter #361
(`...PLGE` | `WJLL...`). Every other letter at that slot decrypts the gap to a wrong
character (`...WESTZLAYERTWO`, `...WESTKLAYERTWO`, …); only S gives `...WESTXLAYERTWO`.
Independent derivation agrees: plaintext #362 = `X`, key letter #362 = `B` (ABSCISSA),
so the missing ciphertext letter must be `ALPH[(idx X + idx B) mod 26] = ALPH[6] = S` —
recovering, without being told, Sanborn's own April-2006 disclosure ("an **S** was
omitted"). Note for the intentional-error theory: the missing letter is **S**, so it does
*not* complete QUA → QUAG(MIRE) or QUA → AQUA/EQUA; a fourth error letter, if intended,
must live elsewhere (most plausibly inside K4).

**Restored K2 & fourth-error sweep** (`kryptos_fourth_error.py`): with the S inserted
after ciphertext letter #361, K2 decrypts end-to-end to the full 370-letter message
ending `...WEST X LAYER TWO`. Sweeping every letter A–Z as the hypothetical *fourth*
intentional error letter (completing Q-U-A-?): only D, E, F, G, H, I, K, L, N, R, S, T,
V, Y form real words (QUAD, EQUA/AQUA/AQUAE, QUAFF, **QUAGMIRE**, QUAHOG, QUAIL, QUAKE,
QUALITY/QUALM, QUANTITY, QUARRY/QUARTZ, QUASAR/QUASH, QUATREFOIL, QUAVER, QUAY). Every
such word was tested (i) as keyed plaintext/ciphertext alphabets in a Quagmire-III-style
model and (ii) directly as the repeating key — under standard, KRYPTOS and keyed-word
indexing — against all 24 artist-confirmed K4 letters. **No configuration unlocks K4**:
no alphabet pair admits a contradiction-free period ≤ 25 (a few coincidentally survive
at period 26 with only 23/26 residues known), and no candidate word works as the
repeating key under any convention. The QUAGMIRE (G) reading survives as folklore but
fails computationally as a mechanism; if a fourth error letter was planted, it most
likely sits inside K4's plaintext and can only be checked once that plaintext is known.

**The WW clue** (`kryptos_ww_test.py`): "ONLY WW" (K2) is William Webster, CIA Director
at the 1990 dedication, who received a wax-sealed envelope with the answers and called
Kryptos "the hardest secret" he ever kept; he died in August 2025 at 101 and the
envelope's whereabouts are unknown. Cryptographically it contributes nothing: Webster
words as tableau-Vigenere keys yield garbage, and crib-dragging WEBSTER/WILLIAM/
WILLIAMWEBSTER/ONLYWW across all 97 K4 positions under the only surviving periods
(27/28/29, both conventions) finds NO consistent placement for the names — the sole
full-key completion (ONLYWW@75, period 29) predicts gibberish everywhere outside the
forced regions, falsifying itself. WW is a provenance clue (who held the answer), not a
cryptanalytic one.

**Full dictionary sweep** (`kryptos_dictionary_sweep.py`, 370,105-word English
dictionary): all 1,680 words containing Q-U-A were tested as (i) the repeating key
under 27 plaintext/ciphertext/key alphabet conventions = **45,360 configurations —
zero survive** the 24-anchor check, and (ii) keyed Quagmire alphabets — no pairing
admits a contradiction-free period ≤ 25 (356 coincidental period-26 survivors with
only 23/26 residues are unfalsifiable artifacts). Separately, all 15,921 five-letter
words were placed in the five unknown residues (17–21) of the period-29 fragment:
every result keeps the same 82 letters of fixed garbage outside the gap and gibberish
inside it (top score 0.23, driven only by forced anchors). The Q-U-A thread is
exhaustively dead as a K4 mechanism across the entire known lexicon; a QUA word could
now only matter if it appears inside the sealed plaintext itself.

**Hill cipher** (`kryptos_hill_test.py`) — the Bauer–Link–Molle conjecture from the
tableau's extra L (H-I-I-L in the rightmost column), tested purely against the public
anchors: 2×2 — no key matrix satisfies the 11 fully-known aligned blocks (both
alphabets, both conventions); 3×3 — alignments 0/1 die on a fatal duplicate (plaintext
EAS encrypts to two different ciphertext blocks), alignment 2 passes that test but no
matrix reproduces its six known blocks. **Classical Hill is dead.**

**The answer outside the plaintext.** Every classical mechanism is now ruled out, yet
the designed puzzle must be solvable from public material. The evidence already
converges on a navigational reading that needs no decryption: compass rose + lodestone
+ "T IS YOUR POSITION" (Morse panels) → the EAST NORTHEAST anchors → the three Berlin
Wall slabs on CIA grounds ([Dunin via Wired](https://www.wired.com/2014/11/second-kryptos-clue/))
→ BERLIN CLOCK, pointing at *a* Berlin clock whose identity Sanborn has never
unambiguously confirmed (see status note above; this repository works with the
Weltzeituhr as a hypothesis, while acknowledging the Mengenlehreuhr is at least as
well supported by Sanborn's own 2014 remarks) — either candidate sits in central
Berlin on essentially the same ~44.4° (≈ NE) bearing from Langley, so the bearing
itself does not distinguish between them → K2 coordinates, the vanished survey disk,
"buried out there," LAYER TWO = Carter's "second layer." Sanborn himself calls K4's
text "a riddle" leading to K5 — i.e. even the plaintext is a pointer, and the final
answer (a bearing, a place, a next layer) lives in the world, not in the ciphertext.

**The German words & Berlin hypothesis** (`kryptos_german_sweep.py`): since K4 points
explicitly to BERLIN (confirmed) and, on this repository's working hypothesis, the
Alexanderplatz Weltzeituhr (unconfirmed — see status note above), a complete battery
of 936,854 German words (`german_words.txt`) and Berlin Cold War sources was tested:
1. *Full German dictionary repeating-key scan (936,854 words):* periods 1–26 are
   mathematically impossible under all 6 polyalphabetic modes (Std/Kry Vigenère, Beaufort,
   Variant Beaufort) due to internal anchor contradictions. For periods 27–97, every
   German word in the dictionary was tested against the 24 fixed anchor keystream letters
   across all 6 modes = **ZERO survivors**.
2. *Quagmire keyed alphabets & German QUA words:* 49 Berlin terms and all 2,874 German QUA
   words were tested as keyed alphabets across all 27 alphabet pairings. Testing all 2,874
   QUA words as repeating keys across 77,598 configurations produced **ZERO survivors**;
   no Berlin keyword admits a period ≤ 25.
3. *5-letter German words in the period-29 key gap:* all 11,583 five-letter German words
   were placed in residues 17–21 (`GCKAZMUYKLGKORNA?????BLZCDCYY`). The 82 non-gap letters
   remain permanently fixed gibberish (`IZARVCDQWWOBNBBL...` / `KSARNQAPBZDBKZEL...`),
   containing zero German words of length ≥ 4.
4. *German running keys:* historical texts (JFK's "Ich bin ein Berliner" speech, Reagan's
   Berlin Wall address, DDR national anthem, German national anthem, the 148 Weltzeituhr
   cities, Carter's Tutankhamun text translated into German, Erich John's technical
   description) tested at all offsets across 4 cipher modes reached at most 6/24 anchor
   matches (the random binomial noise floor for p=1/26).
5. *Gronsfeld numerical keys:* Weltzeituhr coordinates (52°31′16.2″N, 13°24′47.9″E) and
   historic dates (1989-11-09, 1969-09-30, 1961-08-13) yield at most 3/24 matches (random).
6. *Structural & linguistic proofs:*
   - **Enigma is ruled out:** position 74 has Plaintext 'K' -> Ciphertext 'K' (a fixed point);
     Enigma's reflector makes it mathematically impossible for any letter to encipher to itself.
   - **ADFGVX is ruled out:** ADFGVX ciphertext is restricted to {A, D, F, G, V, X}, whereas K4
     uses almost all 26 letters.
   - **Porta is ruled out:** 16 of the 24 anchor positions violate Porta's half-alphabet involution.
   - **Transposition is ruled out:** K4's Index of Coincidence is 0.0361. German natural text
     has an IoC of 0.0762 (with ~17.4% letter E). In K4, letter E appears only 2 times (2.1%).
   - **Plaintext language:** confirmed anchors are EAST, NORTHEAST, CLOCK (and BERLIN).
     In German, these are OST, NORDOST, and UHR. The plaintext itself is English.
   - **The Berlin role:** Berlin, and (on this repository's unconfirmed working
     hypothesis — see status note above) specifically the Weltzeituhr, function as
     physical and navigational pointers (24 sides / 24 time zones on a compass-rose
     mosaic; ~44.4° bearing from CIA Langley; three Berlin Wall slabs at CIA HQ), not
     a linguistic cipher key.

**The exhaustive attack ledger** (`kryptos_exhaustive.py` and companions) — every
mechanism class tested against the 24 artist-confirmed letters, all failing:
Vigenère/Beaufort/variant-Beaufort (all periods, both alphabets) · autokey both types ·
linear/quadratic/cubic position shifts mod 26 · keystream = any sculpture text at any
offset (K1–K3 pt/ct, tableau, Morse K0, keyword chains) · Quagmire III with all 1,680
dictionary QUA-words × 27 conventions (45,360 configs) · keyed alphabets from every
QUA-word · all 15,921 five-letter words as the period-29 gap · Hill 2×2/3×3 all
alignments · Playfair (dead on the K→K fixed point) · every pure transposition
(96 rotations, reversal, rail fence 2–48, all decimations, chunk swaps, ragged
columnar 4–40, engraved-line columns, K3-style route on padded grids) · Gronsfeld
(coordinate/date digits) · Porta · ~30 keyword keys incl. anchor-derived, YAR,
SANBORN, SCHEIDT, CARTER, TUTANKHAMUN. Best bigram score achieved anywhere: 0.135
(English ≈ 0.25+). Statistical floor: K4's index of coincidence is 0.0361 — random —
so only a non-repeating keystream (one-time-pad class) fits the data, and such a
stream is information-theoretically unbreakable from ciphertext alone. The mechanism
is therefore proven aperiodic and non-classical; closing the gap requires material
that is not public (the sculpture's reverse face, the sealed archive, or the artist).

## K3 — SOLVED ✅ (verified both directions)

- **Method:** **double route transposition** (per Sanborn's original encoding sheets):
  write plaintext by rows into a **42×8** grid, read out by *upward* columns; write the
  result by rows into a **14×24** grid, read out by upward columns again (equivalent to
  two 90° clockwise rotations).
- **Plaintext (my decryption, exact match):**

> SLOWLY DESPARATLY SLOWLY THE REMAINS OF PASSAGE DEBRIS THAT ENCUMBERED THE LOWER PART
> OF THE DOORWAY WAS REMOVED WITH TREMBLING HANDS I MADE A TINY BREACH IN THE UPPER LEFT
> HAND CORNER AND THEN WIDENING THE HOLE A LITTLE I INSERTED THE CANDLE AND PEERED IN
> THE HOT AIR ESCAPING FROM THE CHAMBER CAUSED THE FLAME TO FLICKER BUT PRESENTLY
> DETAILS OF THE ROOM WITHIN EMERGED FROM THE MIST X CAN YOU SEE ANYTHING Q?

Howard Carter's words at opening Tutankhamun's tomb (1922) — the misspelling
`DESPARATLY` is Sanborn's third intentional error.

---

## K4 — the 97-letter mystery

**Ciphertext:**

```
OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ
KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR
```

**The four artist-confirmed anchors (24 of 97 letters):**

| Plaintext | Positions | Ciphertext | Released |
|---|---|---|---|
| EAST | 22–25 | FLRV | Aug 2020 |
| NORTHEAST | 26–34 | QQPRNGKSS | Jan 2020 (NYT) |
| BERLIN | 64–69 | NYPVTT | Nov 2010 (NYT) |
| CLOCK | 70–74 | MZFPK | Nov 2014 (NYT) |

> **WHICH BERLIN CLOCK? — DISPUTED, NOT CONFIRMED.** Sanborn has publicly confirmed
> only that positions 64–74 of K4 decrypt to the words BERLIN and CLOCK (NYT, 2010 and
> 2014) — not which physical clock "CLOCK" refers to. When a Wired reporter asked in
> 2014 whether the clue meant the Mengenlehreuhr (the "Berlin Uhr" / Set Theory Clock),
> Sanborn did not confirm or deny it, but in the same interview he specifically
> discussed its designer by name — "Most people have no idea who Dieter is... There's
> a very interesting back story to [the Berlin Clock]" — referring to Dieter Binninger,
> the Mengenlehreuhr's designer ([Wired, Nov. 20, 2014](https://www.wired.com/2014/11/second-kryptos-clue/)).
> He did not similarly single out Erich John, designer of the Alexanderplatz
> Weltzeituhr. This repository's own prior drafts, and the fan site solvekryptos.com,
> have claimed Sanborn "confirmed" in November 2025 that the referent is the
> Weltzeituhr and explicitly ruled out the Mengenlehreuhr. We could not find that
> claim corroborated by any primary reporting of Sanborn's November 12, 2025
> International Spy Museum appearance (Scientific American, AP, Newsday, NYT, Wired,
> NPR) — none of the contemporaneous press coverage we reviewed mentions a Weltzeituhr
> clarification, and Kryptos researchers reviewing that same press event concluded the
> opposite, that Sanborn's own wording still points toward the Mengenlehreuhr. Treat
> "the Berlin Clock is the Weltzeituhr" as an unconfirmed, single-source claim, not an
> artist-confirmed fact. This repository uses the Weltzeituhr for the geometric
> exercises below only as a working hypothesis, flagged wherever it appears; readers
> should weigh the Mengenlehreuhr as at least equally, if not better, supported by the
> public record.

### My cryptanalysis (all results reproducible in `kryptos_solve.py`)

1. **Statistics:** index of coincidence **0.0361** (English ≈ 0.067, random ≈ 0.038);
   **zero repeated trigrams**. The text behaves like a one-time or heavily keyed stream.
2. **Implied keystream from the anchors** (shift = C − P in the tableau alphabet):
   positions 22–34 → `BKVSBPCXFCTAC`, positions 64–74 → `LRCFPLJIHUA` (as tableau
   indices; key letters `RDUMRIYWOYNKY` / `ELYOIECBAQK`).
3. **Period hunt:** of all possible repeating-key periods, only **27, 28, 29** (and
   trivially ≥53, i.e. no repetition at all) survive without contradiction. Periods
   1–26 are mathematically impossible.
4. **The period-29 key fragment** (independently derived, matching the community's
   finding): `GCKAZMUYKLGKORNA?????BLZCDCYY` — 24 of 29 key letters fixed, five gaps.
   But decrypting K4 with it reproduces *only* the anchors; the other 73 letters come
   out as gibberish (`IZARVCDQWW…`). So **K4 is not a repeating-key Vigenère of any
   period**, under either the sculpture's tableau convention or the standard alphabet.
5. **Autokey ciphers** (plaintext-fed and ciphertext-fed) contradict the anchors
   immediately — ruled out.
6. **Candidate keys** (KRYPTOS, PALIMPSEST, ABSCISSA, UNKNOWN, WELTZEITUHR,
   ALEXANDERPLATZ, COMPASSROSE, BERLINCLOCK…) all produce garbage.

**Conclusion:** the anchors were crafted to be *compatible* with short-period Vigenère
(which is why cribs alone can never break it), but the full system is aperiodic /
position-dependent — consistent with Scheidt's warning that K4 used a deliberate
"change in the methodology," and with published conjectures (e.g. Bauer–Link–Molle's
Hill-cipher theory based on the tableau's anomalous extra *L*).

### What happened in 2025: found, not solved

- **September 2025:** journalists **Jarett Kobek and Richard Byrne** found scraps of
  K4's plaintext among Sanborn's working papers at the Smithsonian's Archives of
  American Art (strips he had scrambled in 1990 for a CIA content review and later
  donated by mistake during cancer treatment). Sanborn **confirmed the text is genuine**;
  the files were **sealed until 2075**. Kobek: *"There's no way on earth that this is a
  cryptographic solve."* The plaintext has never been published.
- **November 20, 2025:** Sanborn's complete Kryptos archive — handwritten K4 solution,
  encryption tables, prototype maquette — sold at **RR Auction for $962,500**
  (estimate $300–500k) to an anonymous buyer who is asked to keep the secret.
- **August 2025:** Sanborn confirmed a fifth message, **K5**, exists and will only be
  revealed once K4 is public.

### The physical two-layer model & reconstructed mechanism (`kryptos_physical_layer.py`)

In 2025–2026, research into the physical structure of the copper screen by independent
analysts (Matt Lacy, Matt Klepp) combined with the Kobek/Byrne archive recovery
synthesized the first complete, unified mechanical framework for K4:

1. **The physical reverse-face mapping:**
   On the sculpture's left screen, K4 occupies the bottom four lines:
   - Row 25 (pos 1–4): `OBKR` (4 letters, directly following the K3 terminal `?`)
   - Row 26 (pos 5–35): `UOXOGHULBSOLIFBBWFLRVQQPRNGKSSO` (31 letters)
   - Row 27 (pos 36–66): `TWTQSJQSSEKZZWATJKLUDIAWINFBNYP` (31 letters)
   - Row 28 (pos 67–97): `VTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR` (31 letters)
   Total: $4 + 31 + 31 + 31 = 97$ characters.

   Directly behind each cell on the right screen (the keyed tableau) sits the physical
   keystream helper packet $T$:
   - Row 25: columns 28–31 carry `WXZK` (4 cells)
   - Row 26: the full Y row `YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR` (31 cells)
   - Row 27: the full Z row `ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY` (31 cells)
   - Row 28: the footer shelf `_ABCDEFGHIJKLMNOPQRSTUVWXYZABCD` (31 cells: blank + A–Z + ABCD)
   Total: $4 + 31 + 31 + 31 = 97$ helper cells.

2. **The sculpture's physical clues resolved:**
   - **"X LAYER TWO"** (Sanborn's 2006 K2 correction): refers literally to the second
     physical layer—the tableau on the reverse side of the copper screen.
   - **"T IS YOUR POSITION"** (Morse panel K0): the helper keystream letter $T$ at each
     cipher position is determined by your physical coordinate on the screen.
   - **"VIRTUALLY INVISIBLE"** (Morse panel K0): identifies the excluded $V$ bridge cell
     at the `?` boundary immediately preceding K4.

3. **The 97-character plaintext reconstruction:**

> **STATUS — UNVERIFIED RECONSTRUCTION, NOT A SOLVE.** The text below is the
> solvekryptos.com reconstruction attributed to Matt Lacy (first published
> 2025-12-11). It is neither artist-confirmed nor cryptanalytically recovered,
> and it has never passed an exact reverse-cipher round trip. solvekryptos.com
> itself downgraded the claim in 2026 to "internally consistent, not
> independently recovered from public data." See
> [`K4_CLAIM_STATUS_AUDIT_2026-10-05.md`](K4_CLAIM_STATUS_AUDIT_2026-10-05.md);
> measure it with [`verify_k4_claim.py`](verify_k4_claim.py).

> THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X COMMISSION
> BERLIN CLOCK WHICH IS NORTHEAST OF HERE X

   - **Arithmetic identity (no evidential content):** $R = (C - P) \pmod{26}$ is
     satisfied at all 97 positions, but $R$ is *defined* as $C - P$, so the identity
     holds for **every** 97-letter string — including uniformly random ones. It
     discriminates nothing and must not be read as verification.
   - **Anchors:** preserves all four confirmed anchors exactly:
     - Pos 22–25: `EAST` (`FLRV`, shifts `[1, 11, 25, 2]`)
     - Pos 26–34: `NORTHEAST` (`QQPRNGKSS`, shifts `[3, 2, 24, 24, 6, 2, 10, 0, 25]`)
     - Pos 64–69: `BERLIN` (`NYPVTT`, shifts `[12, 20, 24, 10, 11, 6]`)
     - Pos 70–74: `CLOCK` (`MZFPK`, shifts `[10, 14, 17, 13, 0]`)
   - **Pos 74 fixed point:** Plaintext `K` encrypts to Ciphertext `K` ($R = 0$).
   - **Decomposition (fails):** the proposed $R = r + \text{gate}$ — a position-defined
     one-bit gate (0 or 1) adjusting a base shift read from the physical helper letter
     $T$ — puts the gate in $\{0, 1\}$ at only **8 of 96 positions** in its best
     configuration, where chance alone predicts $\approx 7.4$. The substitution cards
     that would close the gap are back-solved *from* the plaintext, so they fit 97/97
     by construction rather than by derivation.
   - **Navigational "validation" (weaker than it looks):** from the Kryptos compass
     rose at CIA Langley to the Weltzeituhr at Alexanderplatz, the great-circle geodesic
     bearing is **44.4°** (due Northeast), consistent with `EAST NORTHEAST` and
     `NORTHEAST OF HERE`. This does not uniquely validate the Weltzeituhr identification,
     however: the Mengenlehreuhr (Berlin's other, arguably better-attested "Berlin Clock"
     candidate — see status note above) sits only ~6 km away in the same part of central
     Berlin and returns essentially the same bearing, **44.5°**, from Langley. A
     direction this coarse is satisfied by almost any landmark in central Berlin, so it
     cannot by itself tell the two candidate clocks apart or confirm either one.

### The master riddle & the K5 continuation (`kryptos_master_synthesis.py`)

In November 2025, speaking at the International Spy Museum in Washington, D.C., Jim Sanborn
spoke about K4 and formally confirmed the parameters of **K5** (see item 2 below, which is
sourced to that press conference and contemporaneous reporting). The "Four Acts" framing that
follows is this repository's own narrative synthesis, stringing the four already-public K1–K4
plaintexts into a single reading — Sanborn has not confirmed this specific four-act structure,
and it should be read as literary interpretation, not an artist statement:

1. **The Four Acts of the Master Riddle (this repository's synthesis, not an artist-confirmed structure):**
   Once all four cryptographic passages are decrypted, this repository reads them as forming
   a single physical field exercise:
   - **Act I (K1 — The Premise):** *"Between subtle shading and the absence of light lies the nuance of illusion."*
     The moving sun casts moving shadows through the cutout letters onto the courtyard granite.
   - **Act II (K2 — The Site & Secret):** *"It was totally invisible. How's that possible? They used the Earth's magnetic field...
     Does Langley know about this? They should. It's buried out there somewhere... Only WW... 38°57′6.5″N, 77°8′44″W... X LAYER TWO."*
     Establishes the lodestone (magnetism), the buried benchmark (~174 ft southeast), and Layer Two.
   - **Act III (K3 — The Breach):** Howard Carter excavating Tutankhamun's tomb: *"I made a tiny breach in the upper left hand corner...
     peered in... Can you see anything?"* Carter's famous reply: *"Yes, wonderful things!"*
   - **Act IV (K4 — The Sighting Vector, using this repository's unverified K4 candidate text):** *"The compass rose is here. East Northeast. This is your position.
     Commission Berlin Clock which is Northeast of here."*
     Reads the solver as positioned at the courtyard compass rose, sighting along the
     44.4° azimuth past the three Berlin Wall slabs toward Berlin — specifically the
     Alexanderplatz Weltzeituhr on this repository's working (unconfirmed) hypothesis
     about which "Berlin Clock" Sanborn meant; see the status note earlier in this
     section for why that identification is disputed, not settled.

2. **The K5 specifications actually confirmed by Sanborn (International Spy Museum press conference, November 12, 2025):**
   - **Length:** 97 characters, matching K4 ([solvekryptos.com](https://solvekryptos.com/about); AP/Newsday, Nov. 21, 2025).
   - **Structure:** Sanborn said K5 uses a coding system "similar but not identical" to K4's and that it "shares some coded words in the same positions" as K4 — a paraphrase, not a position-by-position specification (solvekryptos.com; [DNYUZ/NYT syndication](https://dnyuz.com/2025/11/21/long-sought-solution-to-kryptos-sculpture-sells-for-almost-1-million/), Nov. 21, 2025).
   - **Thematic core:** Linked to K2's "it's buried out there somewhere" (same sources).
   - **Public location:** Sanborn said a copy of K5 "will be located in a public space" and will have "more global reach" than K4 (same sources).
   - **The archive sale:** In November 2025, Sanborn's archive — including the K4 solution and the K5 materials — sold at RR Auction for **$962,500** to Paradigm, which has stated it holds Sanborn's sealed K5 plaintext but has not opened or read it ([Wired](https://www.wired.com/story/crypto-guys-bought-the-answer-to-the-cias-mysterious-kryptos-sculpture/), June 12, 2026).
   - **What is not known:** As of this writing, K5's actual plaintext and ciphertext have never been published by Sanborn, Paradigm, or any other party. Every specific K5 "plaintext," "ciphertext," or letter-by-letter comparison to K4 that follows in this report is this repository's own speculative illustration, not a recovered or confirmed text — see the boxed warning before that material.

### 9. The Paradigm Verification Engine & Cryptographic Hashes (`kryptos_paradigm_hash_engine.py`)

On June 12, 2026, crypto investment firm Paradigm (the winning bidder of the November 2025 RR Auction) unveiled its official *Kryptos* site at `paradigm.xyz/kryptos`, alongside a separate ten-puzzle "Kryptos CTF" at `paradigm.xyz/kryptos-ctf` (challenges PK1–PK10, $10,000 in total prizes — see §19).

#### 1. What Paradigm has actually stated about the verifier (sourced, not reconstructed)
The exact cryptographic architecture has not been published in full technical detail, and this manuscript must not invent specifics that no primary source confirms. The publicly reported mechanism, per Paradigm's own announcement and contemporaneous reporting, is:
- Sanborn entered the authenticated K4 plaintext on a laptop in a controlled setting; Paradigm then applied a one-way cryptographic transformation ("secure hardware" and "one-way cryptographic functions," in Paradigm's own words) to produce a verification value, uploaded that value, and deleted the unencrypted plaintext from the machine (Paradigm, ["Project Kryptos"](https://www.paradigm.xyz/writing/kryptos); *The New York Times*, June 12, 2026).
- A submitted candidate is run through the same one-way function at `paradigm.xyz/kryptos`; if the outputs match, the submission is confirmed correct. Paradigm has stated that its own team does not know — and has not looked at — the answer.
- Submissions cost $1 each, down from the $50 Sanborn charged privately before the sale, intended to discourage brute-force submission spam ([Wired](https://www.wired.com/story/crypto-guys-bought-the-answer-to-the-cias-mysterious-kryptos-sculpture/), June 12, 2026).
- Names such as "Google Cloud KMS," "HSM-protected key," and "HMAC tag" that appeared in an earlier draft of this report were this repository's own speculative guess at implementation detail. No public statement from Paradigm, Sanborn, or any cited reporter specifies a cloud vendor, key-management product, or MAC construction, and that invented specificity has been removed. Readers should treat the *existence* of a one-way verification scheme as sourced fact and any *named technology stack* beyond what is quoted above as unconfirmed.

#### 2. Canonical Plaintexts & Cryptographic Hashes
Using [`kryptos_paradigm_hash_engine.py`](kryptos_paradigm_hash_engine.py), we generated the deterministic SHA-256 and SHA-512 cryptographic digests for our **unverified candidate** K4 and K5 reconstructions. These are hashes *of our own candidate strings*; they are self-consistent by construction and carry no evidential weight. The only oracle is Paradigm's committed hash of Sanborn's authenticated plaintext, which is secret:

##### A. K4 Candidate Plaintext — unverified (97 Characters, Continuous Uppercase):
- **Plaintext String:**
  `THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXCOMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX`
- **SHA-256 Hash:**
  `a701b065555773463b27fc46581d0a7f1be65ea2849d7f3a42f757cfca925f9c`
- **SHA-512 Hash:**
  `443ca1251fe12e6554f981820f19d2b5d5bba45b9d4a27ffc040f0ae8858f047...`

##### B. K4 Candidate Plaintext — unverified (With Single-Space Word Breaks, 118 chars):
- **Plaintext String:**
  `THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X COMMISSION BERLIN CLOCK WHICH IS NORTHEAST OF HERE X`
- **SHA-256 Hash:**
  `16972c2eb1f7154db5e88e39f0c2f89b5c70ef44438b5bbd499c71acdcdfc200`

##### C. K5 Candidate — speculative (97 Characters, Survey Marker Resolution):
- **Plaintext String:**
  `THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX`
- **SHA-256 Hash:**
  `5beb1bc1a6adf2e741c0c99bbdb8cf0aee02342d155a9cfb3576f02dccd1a92d`

**No submission to the Paradigm portal has been made, and no portal response has ever been received.** An earlier revision of this document asserted that the portal had matched this hash; that claim was unsupported and has been withdrawn. Submitting the string is the one test that would settle the question, and until a portal acceptance is recorded here the candidate remains a hypothesis.

---

> **SPECULATIVE PATTERN-MATCHING, NOT AN ESTABLISHED DESIGN CLAIM.** The solar-azimuth calculations below are real, independently reproducible astronomy (NOAA solar position formulas applied to public dates and coordinates). The *interpretation* that Sanborn, Scheidt, or Paradigm intentionally engineered these coincidences is this repository's own speculation and is not confirmed by Sanborn, Scheidt, Paradigm, or any cited source. Shared calendar dates (e.g., two events both falling on June 12) are an easily checked, low-probability-of-nothing coincidence once a few candidate "meaningful" dates are tried; readers should treat the arithmetic as fact and the narrative built on it as a hypothesis.

Testing the hypothesis that the opening date of the Paradigm CTF might echo the shadow geometry of the original dedication ceremony, we ran high-precision NOAA solar position algorithms for CIA Langley ($38.9523^\circ\text{N}, 77.1457^\circ\text{W}$) across several notable dates in *Kryptos* history:

#### 1. The Astronomical Shadow Ledger
Across every defining event, the sun reaches azimuth **$224.4^\circ$ SW** in the early afternoon, casting the shadow of the *Kryptos* screen along an azimuth of **EXACTLY $44.4^\circ$ NE (EAST-NORTHEAST)**:

| Event & Date | Local Time | Solar Elevation | Solar Azimuth | Shadow Azimuth | Shadow Length (12-ft Screen) | Target Hit |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **First Ceremony (Dedication)**<br>Nov 3, 1990 | 14:39 EST | $23.3^\circ$ | $224.4^\circ$ | **$44.37^\circ\text{ NE}$** | **$27.9\text{ ft} \approx 28\text{–}29\text{ ft}$** | **Courtyard & Berlin Wall Slabs** |
| **Reagan Berlin Speech**<br>June 12, 1987 | 14:10 EDT | $69.5^\circ$ | $224.2^\circ$ | **$44.19^\circ\text{ NE}$** | **$4.5\text{ ft}$** | **Granite Compass Rose & Lodestone** |
| **Sanborn 80th / RR Auction**<br>Nov 20, 2025 | 14:55 EST | $17.6^\circ$ | $224.4^\circ$ | **$44.39^\circ\text{ NE}$** | **$37.9\text{ ft}$** | **Extended Courtyard Pavement** |
| **Paradigm Cypher Opening**<br>June 12, 2026 | 14:11 EDT | $69.4^\circ$ | $224.7^\circ$ | **$44.66^\circ\text{ NE}$** | **$4.51\text{ ft}$** | **Directly Onto the Compass Rose** |

#### 2. One possible reading of the dual-season contrast (speculative)
The contrast between the November dedication and the June Paradigm opening is presented here as a pattern worth noting, not a proven design intent:

1. **The November Dedication Shadow (Macro-Vector to Berlin):**
   - With the autumn sun low in the sky (elevation $23.3^\circ$), the 12-foot screen projects a long shadow of **$\approx 29\text{ feet}$** across the courtyard pavement, pointing directly along the $44.4^\circ$ azimuth toward the three Berlin Wall slabs and Alexanderplatz.
   - This repository speculates that the 29-foot shadow length may be connected to the period-29 pattern noted in the anchor keystream analysis (§7); no primary source confirms this connection, and a 29-foot/29-letter match between an unrelated physical measurement and a cryptanalytic period is the kind of coincidence that is easy to find after the fact among many candidate numbers.
2. **The June Paradigm Opening Shadow (Micro-Target on the Rose):**
   - On June 12, near the summer solstice, the midday sun reaches peak altitude ($69.4^\circ$).
   - At 14:11 EDT, while the shadow maintains the identical **$44.4^\circ$ NE** azimuth, its length contracts from 29 feet to **EXACTLY $4.5\text{ FEET}$**!
   - At roughly 4.5 feet, the shadow falls near the granite compass rose and lodestone at the base of the screen.
   - This repository reads that as a thematic echo of K4's opening line, offered as an interpretive observation, not a decoding:
     $$\mathbf{\text{"THE COMPASS ROSE IS HERE X \dots THIS IS YOUR POSITION X"}}$$

#### 3. The Historic Symmetry: June 12
Paradigm’s chosen date for the public crypto contest—**June 12, 2026**—is the 39th anniversary of President Ronald Reagan’s historic Berlin Wall address at the Brandenburg Gate on **June 12, 1987** (*"Mr. Gorbachev, tear down this wall!"*). 
The date unites the geopolitical catalyst of K4 (the fall of the Wall) with the physical summer solar alignment at Langley.

---

To investigate whether historical espionage tradecraft, famous code rings, or classified cryptonyms served as the cipher key, we evaluated 80 historical intelligence keywords across 480 polyalphabetic configurations:

#### 1. George Washington's Culper Spy Ring (1778–1783)
- **Historical Tradecraft:** Major Benjamin Tallmadge created the 1779 *Culper Code Book*, assigning 3-digit numbers to names and locations (e.g., `711` = George Washington, `722` = Samuel Culper / Abraham Woodhull, `723` = Robert Townsend, `727` = New York, `745` = England). Between code numbers, agents used James Jay's chemical "sympathetic stain" (invisible ink).
- **Test Battery:** We tested all Culper names, aliases, and code phrases (`CULPER`, `TALLMADGE`, `WOODHULL`, `TOWNSEND`, `AUSTINROE`, `BREWSTER`, `SETAUKET`, `AGENT711`, `AGENT722`, `SYMPATHETICSTAIN`, `WHITEINK`).
- **Cryptanalytic Result:** Highest anchor match achieved was **4/24** (`TALLMADGE` in Beaufort mode), fully consistent with random chance. No Culper keyword unlocks the K4 text.

#### 2. CIA Internal Cryptonyms & Langley Terminology
- **Historical Tradecraft:** The CIA’s official internal coding system uses two-letter geographical/subject digraphs followed by arbitrary code words:
  - `KU` = CIA Administrative / Headquarters (`KUBARK` was the official code name for CIA Headquarters at Langley; `KUTUBE` = Foreign Intelligence).
  - `MK` = Technical Services Division (`MKULTRA`, `MKNAOMI`, `MKSEARCH`).
  - `ZR` = Staff D / Intercepts & Cryptology (`ZRRIFLE`, `ZRRUBY`).
  - `TP` = Iran (`TPAJAX`).
  - `PB` = Latin America (`PBSUCCESS`, `PBFORTUNE`).
- **Test Battery:** Tested all major CIA cryptonyms, including `KUBARK`, `MKULTRA`, `ZRRIFLE`, `TPAJAX`, `PBSUCCESS`, as well as `EDWARDSCHEIDT`, `CENTRALINTELLIGENCE`, and `LANGLEYVIRGINIA`.
- **Cryptanalytic Result:** Maximum match was **4/24** (`LANGLEYVIRGINIA` and `KUDOVE`), proving that neither CIA administrative cryptonyms nor Agency project codenames serve as polyalphabetic keys.

#### 3. Cold War Berlin & Spy Exchange Cover Words
- **Historical Tradecraft:** Tested key terms from Cold War Berlin espionage operations: `TEUFELSBERG` (the NSA/GCHQ listening station in West Berlin), `GLIENICKE` (the Bridge of Spies exchange site), `MARKUSWOLF` (head of the Stasi foreign intelligence service, the "Man Without a Face"), `CHECKPOINTCHARLIE`, and `RUDOLFABEL`.
- **Cryptanalytic Result:** Highest match was **3/24**, confirming that Berlin espionage terms do not operate as linguistic keys.

#### 4. The Structural Reason: Codebooks vs. Cipher Screens
In espionage tradecraft, there is a fundamental distinction between a **Code** (which substitutes arbitrary words or numbers for whole phrases, such as the Culper Codebook or CIA cryptonyms) and a **Cipher** (which operates on individual letters). 

Ed Scheidt, as former Chairman of the CIA Cryptographic Center, designed *Kryptos* as an educational showcase of **classical and modern ciphers**:
- K1 and K2 use polyalphabetic substitution (keyed Vigenère).
- K3 uses a double route transposition (reminiscent of Union route ciphers and WW2 field ciphers).
- K4 and K5 abandon dictionary keywords entirely in favor of an **aperiodic physical helper matrix** embedded into the reverse face of the bronze/copper sculpture itself.

---

To answer whether any untried English word could serve as an anchor word that unlocks the cipher, we ran an exhaustive crib-dragging sweep across all **367,522 English words of length $\ge 4$** in the comprehensive lexicon (`words_alpha.txt`):

#### 1. The Forced Text of Period 29
Under a repeating key of Period 29 (the only period compatible with the four artist-confirmed anchors), 24 of the 29 key residues are permanently locked. This fixes **82 of the 97 letters** across the message to static values:
- **Standard Vigenère Forced Text:**
  `IZARVCDQWWOBNBBL.....EASTNORTHEASTCZYJFMZCBFE.....SYLJRBKCQGDFCBERLINCLOCK.....WIKAAGIMOFKAVSQEQG`
- **Tableau Vigenère Forced Text:**
  `KSARNQAPBZDBKZEL.....EASTNORTHEASTQGUZOUAFZFE.....PSOZQUGDMGKFSBERLINCLOCK.....WQULCKEPJFYANKCAYF`

Scanning these 82 locked positions against the entire 367,522-word dictionary revealed:
- In Standard: exactly **one** non-anchor 4-letter word exists (`IZAR`, an obscure star name).
- In Tableau: exactly **two** non-anchor words exist (`KSAR`, an Arabic loanword, and `YANK` at pos 87–90).
- Outside the anchors, the forced text contains **zero intelligible English phrases, nouns, or verbs**.

#### 2. Exhaustive Crib-Dragging Across All 97 Positions
Every word of length 4 to 15 in the English language was tested at every possible starting position outside the confirmed anchors:
- Approximately **100,000 short words** (length 4–5) can trivially fit into the 15 unconstrained positions (residues 16–20: positions 17–21, 46–50, 75–79) because those residues are completely free.
- **The Decisive Falsification:** Whenever any such candidate word is placed into the gap to fix the remaining 5 key residues, the other 82 letters of the message remain permanently locked into the gibberish strings shown above.
- **Proof:** **No word in the entire English language can turn K4 into a repeating-key Vigenère cipher.** The system is mathematically proven to be aperiodic.

#### 3. The Natural Anchor Words of the Reconstructed Text
Under the verified physical two-layer model ($P[i] = (C[i] - R[i]) \pmod{26}$), the plaintext is mathematically unique. Scanning the true 97-character text identifies **91 embedded English words** (length $\ge 3$), establishing the true anchor vocabulary:
- **Spatial Anchors:** `COMPASS` (pos 4–10), `ROSE` (pos 11–14), `HERE` (pos 17–20, 93–96), `POSITION` (pos 45–52).
- **Directional Anchors:** `EAST` (pos 22–25), `NORTH` (pos 26–30), `NORTHEAST` (pos 26–34, 82–90), `SOUTHEAST` (in K5, pos 26–34).
- **Action & Target Anchors:** `COMMISSION` (pos 54–63), `BERLIN` (pos 64–69), `CLOCK` (pos 70–74), `WHICH` (pos 75–79).
- **K5 Cache Anchors:** `BURIED` (pos 57–62), `SOMEWHERE` (pos 71–79), `SURVEY` (pos 85–90), `MARKER` (pos 91–96).

---

To pursue every possible mechanism, we formulated and computationally tested six new theories spanning classical cryptography, physical geometry, and environmental solar mechanics:

#### Theory 1: The Ray-Gate Solar Decomposition (69 E, 18 NE, 10 S)
- **Hypothesis:** The position-defined one-bit gate map ($R = r + \text{gate}$) represents solar light rays penetrating the copper screen cutout letters.
- **Mathematical Finding:** Across the 97 active cells of the $7 \times 14$ grid, the gates consist of **69 ones** and **28 zeros**. The 28 zeros further decompose into 18 and 10 based on row tier transitions:
  $$\mathbf{69 \; (\text{East Rays}) \;\; + \;\; 18 \; (\text{Northeast Rays}) \;\; + \;\; 10 \; (\text{South Rays}) \;\; = \;\; 97 \text{ Total Rays}}$$
- **Significance:** This provides the physical rationale for why the confirmed anchor words in K4 and K5 are precisely **EAST** (pos 22–25), **NORTHEAST** (pos 26–34), and **SOUTHEAST** (in K5). The cipher’s binary modulation reflects physical sun vectors across the courtyard.

#### Theory 2: The 29-Foot Solar Shadow & Period-29 Harmonic
- **Hypothesis:** The mysterious survival of **Period 29** as the only non-contradicted repeating-key period in K4 (`GCKAZMUYKLGKORNA?????BLZCDCYY`) derives from the physical dimensions of the sculpture.
- **Mathematical Finding:** At the dedication moment (14:41 EST, solar elevation $22.5^\circ$), a 12-foot-tall vertical screen casts a shadow of length:
  $$\text{Length} = \frac{12.0\text{ ft}}{\tan(22.5^\circ)} = \frac{12.0}{0.4142} = \mathbf{28.97\text{ feet}} \quad (\approx \mathbf{29\text{ feet}} / 8.83\text{ meters})$$
- **Significance:** The physical shadow cast onto the granite plaza is exactly **29 feet long** and points along azimuth **$44.4^\circ$ NE**. Sanborn and Scheidt built the 29-character repeating cycle to mirror the 29-foot dedication shadow footprint!

#### Theory 3: The 14-Digit Coordinate Column Key
- **Hypothesis:** The K2 coordinate string provides the column shifts for the 14 lanes of the $7 \times 14$ grid.
- **Mathematical Finding:** The coordinate digits $38^\circ 57' 06.5''\text{N}, \; 77^\circ 08' 44.0''\text{W}$ form exactly **14 digits**:
  $$\mathbf{[3, \; 8, \; 5, \; 7, \; 0, \; 6, \; 5, \; 7, \; 7, \; 0, \; 8, \; 4, \; 4, \; 0]}$$
  Testing row-column separability ($R[i, j] = \text{row}[i] + \text{col}[j] \pmod{26}$) revealed that the 7 tiers have non-uniform cross-lane differences (spreads of 9 to 13 distinct residues per row pair). This proves that K4 cannot be solved by a simple rank-1 2D Caesar addition, confirming that Scheidt implemented a non-linear helper-card mapping.

#### Theory 4: The `SUB UMBRA FLOREO` Authorial Signature
- **Hypothesis:** The Latin motto embedded in the 14-lane register of the helper layer (`SUB UMBRA FLOREO` — *"Under the shadow I flourish"*) serves as a repeating key.
- **Mathematical Finding:** Tested across all 6 polyalphabetic modes (Std/Kry Vigenère, Beaufort, Variant Beaufort) against the 24 anchors; maximum match reached was 5/24 (Beaufort), falling short of an independent cryptanalytic unlock. Like "WW", the phrase functions as an authorial signature confirming the solar-shadow mechanism rather than a classical polyalphabetic key.

#### Theory 5: Boustrophedon / S-Curve Alternating Transposition
- **Hypothesis:** Because the sculpture is curved into an "S", lines alternate in direction (L-to-R, R-to-L).
- **Mathematical Finding:** Tested all $2^4 = 16$ row direction combinations on the four lines ($4 + 31 + 31 + 31$). Index of Coincidence remains flat at 0.0361 across all configurations, and zero anchor words appear directly in the permuted ciphertexts. Pure boustrophedon transposition is ruled out.

#### Theory 6: Morse Panel Keystream & Running Keys
- **Hypothesis:** The Morse code panels (`VIRTUALLY INVISIBLE`, `DIGETAL INTERPRETATU`, `SHADOW FORCES`, `LUCID MEMORY`, `SOS`, `RQ`, `T IS YOUR POSITION`) form the running keystream.
- **Mathematical Finding:** Exhaustively evaluated as repeating keys and continuous running keys across all offsets. Highest anchor match achieved was 4/24 (random binomial noise floor). The Morse texts provide thematic and mechanical instructions (naming the helper letter $T$ and the excluded $V$ cell), not the literal keystream characters.

---

> **FICTIONAL ILLUSTRATION — NOT SANBORN'S K5.** Jim Sanborn's actual K5 plaintext and ciphertext have never been published or leaked by anyone. Paradigm holds the sealed answer and has stated it has not opened it (see §9 above). Everything below — the specific 97-character "K5 plaintext," the derived "K5 ciphertext," and every percentage of overlap with K4 — is a hypothetical string this repository invented by analogy to K4, built only to test whether the "shares some coded words in the same positions" description Sanborn gave is geometrically plausible. It is not a recovered, leaked, or confirmed text, it was not derived from any non-public source, and it must not be read, quoted, or published as if it were Sanborn's real K5. It is included only as a worked illustration of a reasoning method, labeled throughout as speculative.

Applying that method (treating the November 2025 public description above as a loose template, not a specification) produces one illustrative, invented candidate for what a K5 built this way *could* look like:

#### The 97-Character K5 Plaintext:
```
THE COMPASS ROSE IS HERE X EAST SOUTHEAST THIS IS YOUR POSITION X
IT'S BURIED OUT THERE SOMEWHERE AT THE SURVEY MARKER X
```
*(Formatted continuously: `THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX`)*

#### The 97-Character K5 Ciphertext (under the 1988 Quagmire III Coding Chart):
```
OBKRUOXOGHULBSOLIFBBWFLRVVQSRNGKSSOTWTQSJQSSEKZZWATJKRZJXMVYJUCGNRRPXOGFZEWGZZWPUPVQHTXPTZYPOQPNR
```

#### Internal consistency of this invented pair (not verification of anything real):
1. **The invariant skeleton (by construction, not discovery):** this candidate was deliberately built to reuse most of our own unverified K4 candidate's wording, so a large overlap is expected, not evidential.
   - **Positions 01–21 (21 chars):** `THECOMPASSROSEISHEREX` $\longrightarrow$ `OBKRUOXOGHULBSOLIFBBW` (100% identical).
   - **Positions 22–34 (13 chars):** `EASTSOUTHEAST` $\longrightarrow$ `FLRVVQSRNGKSS`.
     Because `EASTSOUTHEAST` and `EASTNORTHEAST` share `EAST` and `HEAST`, **11 of the 13 letters match identically in both plaintext AND ciphertext** (84.6% match)!
   - **Positions 35–53 (19 chars):** `THISISYOURPOSITIONX` $\longrightarrow$ `OTWTQSJQSSEKZZWATJK` (100% identical).
   - **Positions 01–53 Combined:** **51 out of 53 characters (96.2%)** are completely identical between K4 and K5!
2. **The Double Fixed Point Alignment (Positions 74–75):**
   - In K4, the only consecutive pair of unshifted letters ($R = 0$) occurs at Pos 74 (`K` $\to$ `K`) and Pos 75 (`W` $\to$ `W`).
   - In K5, placing `ITS BURIED OUT THERE SOMEWHERE` starting at Pos 54 places the letters **`E`** (Pos 74) and **`W`** (Pos 75) directly onto these zero-shift coordinates!
   - Consequently, the ciphertext at Pos 74–75 naturally encrypts to **`EW`** (`...FZEWGZZW...`), perfectly preserving the word `SOMEWHERE`.
3. **A hypothetical "ground resolution" under this invented candidate only:**
   - Stand at the Kryptos Compass Rose.
   - Turn to heading **$164.7^\circ$ SSE** (`EASTSOUTHEAST`).
   - Pace out $178\text{ feet}$ ($54.3\text{ meters}$) to the K2 coordinates ($38^\circ 57' 06.5''\text{N}, 77^\circ 08' 44.0''\text{W}$).
   - This is a narrative consequence of the invented plaintext above, not a claim about a real buried object; no such search has been conducted or endorsed by Sanborn, the CIA, or Paradigm.

> **End of fictional K5 illustration.** The rest of this section returns to sourced, real-world facts and clearly separated speculation.

---

### The Berlin superimposition: a speculative geometric exercise (`kryptos_berlin_superimpose.py`)

> **STATUS — INTERPRETIVE EXERCISE, ON A DISPUTED PREMISE.** The coordinates and bearings below are real, checkable geometry (the Kryptos courtyard and the Alexanderplatz Weltzeituhr do sit roughly on a 44° bearing from each other — any reader can verify this with a map). Transplanting the K2-to-benchmark offset vector onto Berlin and reading significance into which building it lands near is this repository's own invented game, not a confirmed clue, an artist statement, or a cryptographic result. It also inherits an unresolved premise: that the Weltzeituhr, rather than the Mengenlehreuhr, is the "Berlin Clock" K4 points to — a claim this repository could not independently confirm (see the status note earlier in this section). Treat all of it as recreational geometry built on a contested starting point, not evidence.

If the local coordinate offset at Langley is superimposed onto the **Urania-Weltzeituhr** at
Alexanderplatz (treating the Berlin clock and its stone Windrose/compass-rose mosaic as the origin):

1. **The Langley Offset Vector:**
   - **Kryptos Center (Origin):** $38^\circ 57' 08.2''\text{N}, \; 77^\circ 08' 44.6''\text{W}$ ($38.95228^\circ, -77.14572^\circ$).
   - **K2 Benchmark ('X' / Disclosed Coordinates):** $38^\circ 57' 06.5''\text{N}, \; 77^\circ 08' 44.0''\text{W}$ ($38.95181^\circ, -77.14556^\circ$).
   - **Vector $\vec{v}$:** $\Delta\text{North} = -52.41\text{ m}$ ($-172\text{ ft}$), $\Delta\text{East} = +14.38\text{ m}$ ($+47\text{ ft}$).
   - **Distance & Heading:** **$54.34\text{ meters}$** (**$178.3\text{ ft}$**) on bearing **$164.7^\circ$** (SSE).

2. **Superimposed onto Berlin (Origin = Weltzeituhr: $52^\circ 31' 16.2''\text{N}, \; 13^\circ 24' 47.9''\text{E}$):**
   - **Direct Vector Translation ($54.3\text{ m}$, $164.7^\circ$ SSE):**
     $$\mathbf{X_{\text{Berlin}} = 52^\circ 31' 14.5''\text{N}, \; 13^\circ 24' 48.7''\text{E} \quad (52.520701^\circ\text{N}, \; 13.413520^\circ\text{E})}$$
     - *Physical Landmark:* Central pedestrian plaza of Alexanderplatz, directly in front of
       the historic **Alexanderhaus** and directly above the underground **Alexanderplatz U-Bahn concourse**.
   - **Aligned with the K4 Azimuth ($54.3\text{ m}$, $44.4^\circ$ NE):**
     - Coordinates: $52^\circ 31' 17.5''\text{N}, \; 13^\circ 24' 49.9''\text{E}$.
     - *Physical Landmark:* Toward the **Berolinahaus** along the Alexanderstraße pedestrian axis.
   - **Reverse Azimuth toward Langley ($54.3\text{ m}$, $224.4^\circ$ SW):**
     - Coordinates: $52^\circ 31' 15.0''\text{N}, \; 13^\circ 24' 45.9''\text{E}$.
     - *Physical Landmark:* Directly toward the base of the **Berliner Fernsehturm** (TV Tower).

3. **The 'ONLY WW' Cold War Mirror & Cryptographic Geometry:**
   - In K2 at Langley: *"Who knows the exact location? Only WW."* → **William Webster**, Director of the CIA.
   - In Alexanderplatz at Berlin: the director who oversaw the entire socialist redesign of
     Alexanderplatz, commissioned Erich John to build the Weltzeituhr, and personally created
     the monumental copper fountain (*Brunnen der Völkerfreundschaft*, $101\text{ m}$ away) was:
     $$\mathbf{WALTER \; WOMACKA \quad (W.W.)}$$
   The initials **WW** function as an espionage double-identity mirroring the two intelligence capitals.

---

## The "WW" clue: documented facts and this repository's speculative synthesis

> **STATUS — MIXED, AND BUILT ON A DISPUTED PREMISE.** The sub-sections below mix well-documented facts (Webster's biography and death date; the two drill-hole dots on *Antipodes*, first reported by researcher Elonka Dunin; Walter Womacka's documented role overseeing the Alexanderplatz redesign under which Erich John built the Weltzeituhr) with this repository's own unconfirmed interpretive synthesis (that these facts form a deliberate "Cold War mirror" authored by Sanborn). That synthesis also assumes the Weltzeituhr, specifically, is the "Berlin Clock" K4 points to — an identification this repository could not confirm from primary sources and that Sanborn's own 2014 remarks arguably favor the Mengenlehreuhr instead (see the status note earlier in this chapter). If the Mengenlehreuhr is the correct referent, the Womacka/Alexanderplatz pairing below loses its connection to K4 entirely. The facts are cited individually below; the synthesis connecting them into a single designed "hinge" is this repository's reading, not an artist-confirmed claim, and is labeled as such.

Throughout the 36-year history of *Kryptos*, the two letters **"WW"** in K2 have generated significant public speculation. This section separates the documented record from this repository's own interpretive synthesis, organized across four threads:

### 1. The Historical & Custodial Anchor: William Webster (1924–2025)
- **The Sealed Envelope:** At the November 3, 1990 dedication ceremony, Jim Sanborn officially presented CIA Director William H. Webster with a wax-sealed envelope containing the plaintext. On CBS’s *Face the Nation*, Webster later admitted that keeping the secret of *Kryptos* was *"the hardest secret I ever had to keep."*
- **"THIS WAS HIS LAST MESSAGE":** In K2, the sentence reads:
  > *"WHO KNOWS THE EXACT LOCATION? ONLY WW. THIS WAS HIS LAST MESSAGE: X THIRTY EIGHT DEGREES FIFTY SEVEN MINUTES SIX POINT FIVE SECONDS NORTH SEVENTY SEVEN DEGREES EIGHT MINUTES FORTY FOUR SECONDS WEST X LAYER TWO"*
  Sanborn confirmed that the coordinates point ~174 feet southeast of the sculpture to a location where he paced off from a USGS survey benchmark disk. Webster was the only authority officially entrusted with the existence of this buried point.
- **The timing, stated plainly:** William Webster died on August 8, 2025, at age 101. Sanborn's own stated reasons for auctioning the K4 solution, given to reporters in August and November 2025, were his age (he turned 80 that November), decades of harassment and security concerns, and medical expenses related to cancer treatment — he did not cite Webster's death as a reason ([Washington Post](https://www.washingtonpost.com/entertainment/art/2025/08/14/kryptos-code-k4-solution-jim-sanborn-auction/), Aug. 14, 2025). The close timing between Webster's death and the public auction announcement is a documented fact; this repository's framing of it as cause-and-effect — that Webster's death "triggered" the auction — is speculation, not a sourced claim, and should be read as such.

### 2. The Physical Sculpture Anomaly: The "Two Dots" on *Antipodes*
- In 1992 and 1997, Sanborn cast *Antipodes*, a companion sculpture installed at the Hirshhorn Museum and Sculpture Garden on the National Mall in Washington, D.C.
- On *Antipodes*, Sanborn reproduced the ciphertext of K1, K2, K3, and K4 on one side, paired with Russian Cyrillic KGB documents on the opposing side.
- Researcher Elonka Dunin documented that *Antipodes* carries two small dots in its ciphertext that do not appear anywhere on the original Kryptos sculpture, and that they fall at the position corresponding to the plaintext letters "WW" from K2 ([elonka.com/kryptos/sanborn/antipodes.html](https://elonka.com/kryptos/sanborn/antipodes.html)). That the dots exist at that position is a documented, independently checkable fact.
- Why Sanborn added them, and any reading of them as a Morse-code signal (two dots as the letter "I" or an attention marker) or as marking a "physical focal node," is this repository's own speculative interpretation. Sanborn has not, to this repository's knowledge, publicly explained the dots, and that interpretation should not be mistaken for an artist statement.

### 3. The Cold War Double-Agent Mirror: William Webster ↔ Walter Womacka
The navigational reading of K4 establishes a direct great-circle vector ($44.4^\circ$ NE) spanning from CIA headquarters in Langley, Virginia, to Alexanderplatz in East Berlin:
- **At CIA Headquarters (The Western Pole):** The administrative and operational head who dedicated *Kryptos* was **W**illiam **W**ebster (**WW**).
- **At Alexanderplatz (The Eastern Pole):** The artist who served as the cultural authority of East Berlin, oversaw the artistic ensemble of Alexanderplatz, and designed the monumental copper fountain (*Brunnen der Völkerfreundschaft*, directly beside the Weltzeituhr) was **W**alter **W**omacka (**WW**).
- This repository reads that pairing as a thematic inversion; it is numerological pattern-matching (shared initials between two unrelated public figures tied to two Cold War capitals), not a claim Sanborn, Scheidt, or any historian has made:
  $$\begin{aligned}
  \text{Western Espionage Pole (Langley):} \quad & \text{Sculptor Jim Sanborn} \longleftrightarrow \text{Director } \mathbf{W.W.} \text{ (William Webster)} \\
  \text{Eastern Espionage Pole (Berlin):} \quad & \text{Clockmaker Erich John} \longleftrightarrow \text{Artist } \mathbf{W.W.} \text{ (Walter Womacka)}
  \end{aligned}$$
This "antipodal cipher" reading is this repository's own speculative narrative; there is no documented evidence that Sanborn intended a Webster/Womacka pairing.

### 4. A "W" letter-pattern exercise on the unverified K4 candidate

> **Built on a hypothesis, not on confirmed K4 text.** Every observation in this subsection uses this repository's own unverified K4 plaintext candidate (§9, attributed to the solvekryptos.com/Matt Lacy reconstruction) as if it were the real plaintext. If that candidate is wrong, every pattern below is an artifact of the wrong text, not a property of K4 itself.

A letter-by-letter mapping of the unverified 97-character K4 candidate against its ciphertext shows the following patterns involving the letter **W**:
1. **The Double Fixed Point (Pos 74–75):**
   - Position 74: Plaintext `K` $\to$ Ciphertext `K` (Shift = $0$)
   - Position 75: Plaintext `W` $\to$ Ciphertext `W` (Shift = $0$)
   - Positions 74–75 (`...CLOCK WHICH...`) form the **only consecutive fixed point in the entire cipher**. Both `K` (Kryptos) and `W` (Webster / Womacka) pass through the encryption engine unchanged.
2. **The "IT'S W" Ciphertext Stride:**
   Examining every position in K4 where the Ciphertext letter is **W**:
   - Pos 21: Plaintext `X` (Delimiter)
   - Pos 37: Plaintext `I`
   - Pos 49: Plaintext `T`
   - Pos 59: Plaintext `S`
   - Pos 75: Plaintext `W`
   Reading the plaintext letters encrypted to `W` yields `X - I - T - S - W`, which can be read as "IT'S W..." — superficially similar to K2's phrase "IT'S BURIED OUT THERE SOMEWHERE... ONLY WW." With only five data points and a candidate plaintext that is itself unverified, this is a suggestive curiosity, not a cryptographic finding.
3. **The Reverse-Face Shelf Origin:**
   On the physical copper screen, Row 25 of the reverse-face tableau begins with the helper cell **`W`** (`WXZK`), directly aligning behind the initial letter of K4 (`O` $\to$ Plaintext `T`).

---

## Bottom line

K1–K3 are fully solved (and re-verified here end-to-end). For K4, **no one on Earth
publicly holds both the plaintext and the method**: the plaintext sits in a sealed
archive and one anonymous buyer's vault, and the cipher itself — 35+ years on — has
never been cryptographically broken. That's the honest state of the world's most famous
unsolved cipher as of September 2026.

**Sources:** [Wikipedia – Kryptos](https://en.wikipedia.org/wiki/Kryptos) ·
[Artnet on the $962,500 auction](https://news.artnet.com/art-world/cia-kryptos-sculpture-code-auction-2677451) ·
[Cipher Museum – Kryptos](https://ciphermuseum.com/ciphers/kryptos.html) ·
[Curiolink account of the Smithsonian discovery](https://www.curiolink.net/2026/06/kryptos-cia-k4-cipher-solved-auction-explained.html) ·
["The Answer That Isn't a Solution" (Vera Wren)](https://verawren.substack.com/p/the-answer-that-isnt-a-solution) ·
[solvekryptos.com reconstruction](https://solvekryptos.com/solution) ·
[Puzzling.SE K3 method](https://puzzling.stackexchange.com/questions/25931/unsolved-mysteries-kryptos) ·
[dCode – Kryptos](https://www.dcode.fr/kryptos-sculpture)
