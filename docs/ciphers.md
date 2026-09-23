# The cipher table

35 ciphers, codes and encodings behind one interface. Each entry has its own
attack — the interface exists so the engine can schedule, budget and report them
uniformly, not so they can share a brute-force loop.

`buttcrack ciphers --verbose` prints this table from the registry, so it can
never drift out of date; `buttcrack show <name>` prints one entry with a working
example and that cipher's own notes on what breaks it.

Cost is the search class the engine schedules by: **cheap** (a keyspace you can
walk, or a structural decode), **moderate** (a bounded search with a smart
reduction), **expensive** (a stochastic search that wants tens of seconds),
**brutal** (a stochastic search over a large structured keyspace that wants
minutes and still may not finish). Min text is the shortest ciphertext the cipher
will attempt — below it there is not enough evidence to distinguish keys.

### Shift and reciprocal alphabets

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `affine`<br>Affine | (a, b) pair<br>example `a=5, b=8` | 312 | cheap | 4 | Linear map x -> a*x + b mod 26. Caesar is the special case a=1. |
| `atbash`<br>Atbash | none<br>no key | 1 | cheap | 2 | Hebrew substitution cipher mapping the alphabet onto its reverse. |
| `caesar`<br>Caesar (ROT-N) | shift 0-25<br>example `7` | 26 | cheap | 2 | Each letter is shifted by a fixed number of places. ROT13 is shift 13. |
| `reverse`<br>Reverse | none<br>no key | 1 | cheap | 2 | The message reversed. Often layered under or over other ciphers. |
| `rot13`<br>ROT13 | none (fixed shift of 13)<br>no key | 1 | cheap | 2 | Caesar shift of 13. Applying it twice returns the original text. |
| `rot47`<br>ROT47 | shift 0-93<br>example `47` | 94 | cheap | 4 | Rotates printable ASCII (0x21-0x7e) by 47 places. Preserves case and digits. |

### Substitution

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `keyword_substitution`<br>Keyword substitution | keyword<br>example `CIPHER` | unbounded | expensive | 40 | Mixed alphabet built from a keyword, then the remaining letters in order. |
| `substitution`<br>Simple substitution | 26-letter mixed alphabet<br>example `QWERTYUIOPASDFGHJKLZXCVBNM` | unbounded | expensive | 40 | Every plaintext letter maps to a fixed ciphertext letter. Solved by quadgram hill climbing with restarts. |

### Polyalphabetic

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `autokey`<br>Autokey | primer word<br>example `QUEEN` | unbounded | moderate | 40 | Key = short primer followed by the plaintext itself. Solved by chain decomposition. |
| `beaufort`<br>Beaufort | keyword<br>example `LEMON` | unbounded | moderate | 24 | C = K - P. Reciprocal: encryption and decryption are the same operation. |
| `gronsfeld`<br>Gronsfeld | digits 0-9<br>example `31415` | unbounded | moderate | 24 | Vigenere restricted to a digit key, so each column has only 10 possible shifts. |
| `trithemius`<br>Trithemius / progressive key | (start, step)<br>example `start=0, step=1` | 676 | cheap | 16 | Shift increases by a constant step per letter: key[i] = (start + i*step) mod 26. |
| `variant_beaufort`<br>Variant Beaufort | keyword<br>example `LEMON` | unbounded | moderate | 24 | C = P - K: Vigenere encryption with the decryption rule. |
| `vigenere`<br>Vigenère | keyword<br>example `LEMON` | unbounded | moderate | 24 | Repeating-key addition. Cracked by period finding (IC + Kasiski) then per-column Caesar solving. |

### Transposition

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `columnar`<br>Columnar transposition | keyword or permutation<br>example `ZEBRA` | unbounded | expensive | 12 | Plaintext written into a grid by rows, read out by columns in key order. |
| `rail_fence`<br>Rail fence | rails + offset<br>example `3` | unbounded | cheap | 8 | Plaintext written along a zigzag of N rails, then read off rail by rail. |
| `route`<br>Route transposition | (columns, route)<br>example `cols=5, route=spiral_out_cw` | unbounded | moderate | 8 | Plaintext filled into a grid, read out along a fixed route. |
| `skip`<br>Skip / scytale | stride<br>example `5` | unbounded | cheap | 6 | ct = pt[::k] + pt[1::k] + ... + pt[k-1::k] |

### Polygraphic

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `bifid`<br>Bifid | keyword + period<br>example `key=MONARCHY, period=7` | unbounded | brutal | 80 | Each letter becomes (row, column); the coordinates are recombined within a period. Experimental solver. |
| `playfair`<br>Playfair | keyword (5x5 grid)<br>example `MONARCHY` | unbounded | expensive | 50 | Digraph substitution on a 5x5 keyed grid. Solved by hill climbing the grid on quadgram fitness. |

### XOR (byte level)

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `xor_repeating`<br>Repeating-key XOR | byte string<br>example `KEY` | unbounded | moderate | 16 | XOR with a repeating byte key. Key length from normalised Hamming distance, then per-byte frequency analysis. |
| `xor_single`<br>Single-byte XOR | one byte<br>example `66` | 256 | cheap | 4 | Every byte XORed with the same key byte. Exhaustively solvable over 256 keys. |

### Codes

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `a1z26`<br>A1Z26 (numbered alphabet) | none<br>no key | 1 | cheap | 4 | Each letter replaced by its position in the alphabet, separated by spaces or dashes. |
| `bacon`<br>Bacon cipher | none<br>no key | 2 | cheap | 10 | Five symbols per letter over a two-letter alphabet. Both the 24-letter (I=J, U=V) and 26-letter tables are tried. |
| `bacon_case`<br>Bacon (letter case) | none<br>no key | 2 | cheap | 20 | Uppercase/lowercase of ordinary text encodes Bacon's five-bit letters. |
| `morse`<br>Morse code | none<br>no key | 1 | cheap | 4 | Dots and dashes per letter; spaces between letters, ' / ' between words. |
| `polybius`<br>Polybius square | keyword (optional)<br>example `MONARCHY` | 2 | cheap | 6 | 5x5 coordinate grid (I/J merged). Both digit pairs and tap-code style separators are accepted. |

### Encodings (peelable layers)

| cipher | key | keyspace | cost | min text | how it is attacked |
| --- | --- | --- | --- | --- | --- |
| `base16`<br>Hex / base16 | none<br>no key | 1 | cheap | 4 | 4 bits per hex digit. Requires an even number of digits and at least one a-f. |
| `base32`<br>Base32 | none<br>no key | 1 | cheap | 8 | 5 bits per character over A-Z2-7, padded to a multiple of 8. |
| `base58`<br>Base58 | none<br>no key | 1 | cheap | 10 | Big-integer base58 over the Bitcoin alphabet, leading '1's encode leading zero bytes. |
| `base64`<br>Base64 | none<br>no key | 1 | cheap | 4 | 6 bits per character over A-Za-z0-9+/ (or -_ for URLs), padded to a multiple of 4. |
| `base85`<br>ASCII85 / base85 | none<br>no key | 1 | cheap | 6 | 5 bytes per 5 characters over the printable ASCII range; ``<~ ~>`` delimiters optional. |
| `binary`<br>Binary ASCII | none<br>no key | 1 | cheap | 8 | Each byte as 8 bits, separated by spaces (or run together). |
| `decimal_ascii`<br>Decimal ASCII | none<br>no key | 1 | cheap | 4 | Byte values in decimal, separated by spaces or commas (0x.. and octal are also accepted). |
| `url`<br>URL encoding | none<br>no key | 1 | cheap | 3 | Bytes as %XX hex escapes. |

---

## Equivalences: two names, one plaintext

Several ciphers here can produce the *same* plaintext from the same ciphertext,
and the report picks the name a human would use rather than whichever attack
happened to finish first:

| situation | reported as | why |
| --- | --- | --- |
| Atbash text, short | `affine` with `a=25, b=25` | Atbash *is* that affine map; the affine attack is exhaustive and gets there first. The notes say the two are equivalent. |
| Vigenère with a one-letter key | `caesar` | A repeating key of length 1 is a shift. |
| Vigenère whose key is all digits | `gronsfeld` | Gronsfeld is Vigenère restricted to ten shifts per column; the more specific name wins. |
| Beaufort / Variant Beaufort / Vigenère | `vigenere` first | Variant Beaufort with key K decrypts what Vigenère decrypts with key −K. `EQUIVALENT_CIPHER_RANK` orders them `vigenere` < `beaufort` < `variant_beaufort` < `gronsfeld`, and only ever breaks ties. |
| Caesar shift of 13 | `rot13` | The shift test names it directly. |
| Keyword alphabet recovered by the generic attack | `substitution` | The recovered mapping is the *inverse* of a keyword alphabet, which is not keyword-shaped, so the generic name is the honest one. Both are listed in `alternatives` when both attacks land. |

## Lossy by design

Some ciphers cannot give back exactly what went in, and pretending otherwise
would be worse than saying so. The report notes it, and the tests fold it away
before comparing:

| cipher | what is lost |
| --- | --- |
| `playfair` | pads to an even length with `X`, and splits doubled letters (`LL` → `LX LX`) |
| `bifid`, `polybius` | merge `I` and `J` in the grid |
| `bacon`, `bacon_case` | merge `U`/`V` and `I`/`J` in the 5-bit alphabet |
| transpositions | word boundaries — the letters come back in order, the spaces do not, so a dictionary respacing is offered separately |
| `rot47`, `reverse`, all encodings | the original letter layout — ROT47 works on bytes and reverse reorders, so neither can have the input's shape laid back over it |

## Peelable layers and chains

These are ciphers *and* layers: the solver can strip them off the outside of
anything, then re-identify what is underneath, to `--depth` (default 3).

`morse` · `bacon` · `bacon_case` · `a1z26` · `polybius` · `base64` · `base32` ·
`base16` · `base58` · `base85` · `url` · `binary` · `decimal_ascii`

A chain is reported outermost first — `base64 -> base16 -> xor_repeating` — and
the key shown is the key of the cipher that actually hid the message, not of the
encodings that wrapped it. Peeling decodes with latin-1 rather than UTF-8 so a
byte ≥ 0x80 survives as one byte; re-encoding it would shift every XOR key
alignment underneath.

## Adding a cipher

One class, one registration — nothing else in the codebase changes.

```python
class MyCipher(Cipher):
    info = CipherInfo(
        name="mycipher",            # the name the report and CLI use
        title="My Cipher",
        family=Family.SUBSTITUTION, # scheduling, layout rules, display
        key_type="keyword",
        keyspace=None,              # None means unbounded
        min_length=40,              # below this, do not attempt
        cost=EXPENSIVE,             # CHEAP | MODERATE | EXPENSIVE | BRUTAL
        description="One sentence on what it does.",
        example_key="SECRET",       # the CLI parses --key against this type
    )

    def encrypt(self, plaintext: str, key: Any = "SECRET") -> str: ...
    def decrypt(self, ciphertext: str, key: Any = "SECRET") -> str: ...

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        # Yield candidates; ctx.score() and ctx.candidate() do the scoring and
        # the evidence rules. Check ctx.expired() in any loop.
        ...

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        # 0..1 structural self-assessment, used by identify() as a fallback and
        # by the engine to decide whether to peel this as a layer.
        ...
```

The base class already provides: `keys()` for exhaustive keyspaces, a
`prescreen()` hook that ranks keys cheaply before full scoring (chi-squared plus
printable ratio for letter ciphers, quadgram fitness for ROT47), `prepare()`
normalisation, and `ctx.candidate(...)` which applies the confidence and evidence
rules so a new cipher cannot overclaim. `LayerCipher` adds `decodable()` and
`decode()` for things the peeler can strip.

Register it in `buttcrack/ciphers/__init__.py`, add a vector to
`tests/test_ciphers.py` and a break case to `buttcrack/selftest.py`, and the CLI,
the web UI, the reference table and the JSON API pick it up automatically.
