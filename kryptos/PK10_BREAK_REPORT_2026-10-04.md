# PK10 Break Report — 2026-10-04

## Result

PK10 is solved. The recovered construction reproduces all 504 official
ciphertext characters and decrypts back to the same 504-letter plaintext.
Run the independent verifier from the repository root:

```bash
python3 kryptos/verify_pk10_solution.py
```

The verifier is dependency-free and checks both directions, including the
plaintext SHA-256:

```text
a2db145f258ec21fbeab7afb4031e624d3184b93a3eb834d54026ba9b792e1d9
```

## Construction

The earlier 7/8/9-clock and 12×42 records were not the break. PK10 uses the
cumulative cipher pipeline from the preceding Paradigm Kryptos challenges,
followed by three final layers:

```text
Q3(PROVENANCE)
T(MARGINS)
Q3(ORDINATE)
Q3(PENTIMENTO)
T(UNDERLAY)
Q3(OCHRE)
Q3(VERDIGRIS)
T(TWOYEARS)
Q3(PK4 plaintext)
T(HANDIWORK)
T(SMITHWORK)
Q3(PORTAL)
Q3(ANNEAL)
H3(ALCHEMIST)
Q3(METE)
Q3(METER)
Q3(METIER)
Q3(MASTERY)
Q3(CLEPSYDRA)
Spiral(12)
T(BEAMWORK)
```

`Q3` is Quagmire III in the keyed alphabet
`KRYPTOSABCDEFGHIJLMNQUVWXZ`. `T(key)` fills a grid row-wise, permutes
columns by the alphabetical rank of the key letters, and reads columns from
top to bottom. `H3(ALCHEMIST)` uses the nine keyed-alphabet indices as a
row-major matrix modulo 26. The final spiral starts in the top-right cell and
moves down, left, up, and right. Every layer is reversible; the exact
conventions are implemented in `verify_pk10_solution.py`.

The `PK4 plaintext` running key is the 224-letter normalized PK4 message:

```text
TWOYEARSINTHENEEDLESTRAILLEDMETOACRAFTSMANNAMEDTHEWHITESMITHONTHEROADTOHISALPINEWORKSHOPIREREADHISPERFUNCTORYLETTERSHEMETMEATTHEGATESANDLEDMETOASTONEBARNSTACKEDWITHWINTERFODDERONEOFHISNEEDLESISHIDDENINTHEBARNIHAVEBEGUNTOWORK
```

## Plaintext

```text
IHAVENOTREADTHESTRANDTHENEEDLEWASASFINEASPROMISEDBUTMYHANDWASNOTFITTOWIELDITANDTHEKNOTREFUSEDTOYIELDPELLEGRINANDTHEWHITESMITHTRIEDTOTEACHMEBUTWHENTHETESTCAMEIFAILEDTHEMBOTHHADISTAYEDWITHTHEWHITESMITHANDLEARNEDTHEDISCIPLINEHETAUGHTTHOSEYEARSWOULDHAVESHAPEDMYHANDSINTOINSTRUMENTSWORTHYOFTHENEEDLEANDTHEKNOTANDATLASTGIVENMETHELOCATIONOFTHEARCHIVEPELLEGRINHIDITFORONLYSUCHASUCCESSORTHROUGHPATIENCEDISCIPLINEANDTRUECRAFTTOYOUWHOHAVEUNRAVELEDMYMESSAGESYOURHANDISTHENEEDLEIHAVEFINALLYFORGEDANDILEAVETHEKNOTTOYOU
```

With spaces restored, it reads:

> I have not read the strand. The needle was as fine as promised, but my hand
> was not fit to wield it, and the knot refused to yield. Pellegrin and the
> Whitesmith tried to teach me, but when the test came I failed them both. Had
> I stayed with the Whitesmith and learned the discipline he taught, those
> years would have shaped my hands into instruments worthy of the needle and
> the knot, and at last given me the location of the archive. Pellegrin hid it
> for only such a successor, through patience, discipline, and true craft. To
> you who have unraveled my messages, your hand is the needle I have finally
> forged, and I leave the knot to you.

## Provenance and verification boundary

The recovered text and pipeline were published in
[`TTFH/KRYPTOS`](https://github.com/TTFH/KRYPTOS), commit
`496976ebe008f9a5eaef8c52bb8ad06c3a4917f5`, `src/ctf/PK10.h`. This repository
independently reimplements the operations rather than importing that source.
The canonical ciphertext comes from `pk_all_ciphertexts.json`; the acceptance
criterion is an exact local encode/decode round trip, not a language score or
an attractive fragment.

The verified record is stored in `pk_verified_solutions.json` and the generated
submission manifest. PK9 is independently verified in
`verify_pk9_solution.py` as `Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)`; its
provenance and historical candidate record are in
`PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md`.
