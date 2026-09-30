/* Buttcrack Web — a fully client-side automatic cipher breaker.
 *
 * No server, no API keys, no build step. Everything runs in the visitor's
 * browser, which is what makes this thing free to host forever.
 *
 * Scoring is a bigram log-probability model over English, backed up by a
 * common-word hit rate. It is weaker than the quadgram model in the Python
 * package but small enough to ship inline and good enough to solve the
 * classical ciphers people actually paste into a web box.
 */

'use strict';

/* ---------------------------------------------------------------- scoring */

// model.js is loaded first (script tag / require) and provides the corpus.
const M = (typeof module !== 'undefined' && module.exports)
  ? require('./model.js')
  : { TRI_LO, TRI_HI, TRI_FLOOR, TRI_PACKED, TOP_WORDS };

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const B64I = {};
for (let i = 0; i < 64; i++) B64I[B64[i]] = i;

/** Unpack the quantised trigram table into a plain lookup object. */
const TRI = (() => {
  const out = Object.create(null);
  const p = M.TRI_PACKED;
  const span = M.TRI_HI - M.TRI_LO;
  for (let i = 0; i + 5 <= p.length; i += 5) {
    const q = (B64I[p[i + 3]] << 6) | B64I[p[i + 4]];
    out[p.slice(i, i + 3)] = M.TRI_LO + (q / 255) * span;
  }
  return out;
})();
const TRI_FLOOR_V = M.TRI_FLOOR;
const WORDSET = new Set(M.TOP_WORDS.split(' '));

// log10 P(letter) for English, index 0 = A. Used for chi-squared shift picking.
const UNI = [
  -1.086, -1.848, -1.638, -1.532, -0.900, -1.760, -1.700, -1.430, -1.140,
  -2.824, -2.161, -1.590, -1.597, -1.068, -1.079, -1.620, -3.033, -1.230,
  -1.077, -1.033, -1.400, -2.061, -1.799, -2.848, -1.845, -3.180,
];

function lettersOnly(s) {
  return s.toUpperCase().replace(/[^A-Z]/g, '');
}

/** Mean trigram log10 probability per character. Higher (closer to 0) is better. */
function score(text) {
  const t = lettersOnly(text);
  if (t.length < 3) return -99;
  let total = 0;
  for (let i = 0; i <= t.length - 3; i++) {
    const v = TRI[t.slice(i, i + 3)];
    total += v === undefined ? TRI_FLOOR_V : v;
  }
  return total / (t.length - 2);
}

/** Fraction of tokens that are known English words, weighted by token length
 *  so that matching "committee" counts for more than matching "a". */
function wordRate(text) {
  const toks = text.toLowerCase().match(/[a-z']+/g);
  if (!toks || !toks.length) return 0;
  let hit = 0, all = 0;
  for (const w of toks) {
    const weight = Math.min(w.length, 8);
    all += weight;
    if (WORDSET.has(w)) hit += weight;
  }
  return all ? hit / all : 0;
}

/** Combined 0..1 plausibility that a string is English plaintext. */
function plausibility(text) {
  const s = score(text);                       // ~-2.4 great .. ~-5.5 noise
  const norm = Math.max(0, Math.min(1, (s + 5.0) / 2.4));
  const wr = wordRate(text);
  const printable = text.length
    ? (text.match(/[\x20-\x7e\n\t]/g) || []).length / text.length
    : 0;
  // Short strings can look great by luck, so ramp confidence in with length.
  const n = lettersOnly(text).length;
  const lengthRamp = Math.min(1, 0.45 + n / 60);
  // English is mostly letters and spaces. A "solution" studded with digits and
  // punctuation is almost always a scoring artefact over a handful of letters,
  // so weight by how text-like the character mix is.
  const textish = (text.match(/[A-Za-z \n]/g) || []).length / text.length;
  const density = textish >= 0.78 ? 1 : Math.pow(textish / 0.78, 3);
  const base = wr > 0.15 ? (0.35 * norm + 0.65 * wr) : (0.7 * norm + 0.3 * wr);
  return Math.max(0, Math.min(1, base * printable * lengthRamp * density));
}

function indexOfCoincidence(text) {
  const t = lettersOnly(text);
  if (t.length < 2) return 0;
  const counts = new Array(26).fill(0);
  for (const ch of t) counts[ch.charCodeAt(0) - 65]++;
  let sum = 0;
  for (const c of counts) sum += c * (c - 1);
  return sum / (t.length * (t.length - 1));
}

function entropy(text) {
  if (!text.length) return 0;
  const freq = new Map();
  for (const ch of text) freq.set(ch, (freq.get(ch) || 0) + 1);
  let h = 0;
  for (const c of freq.values()) {
    const p = c / text.length;
    h -= p * Math.log2(p);
  }
  return h;
}

/* ---------------------------------------------------------------- ciphers */

function shiftText(text, k) {
  let out = '';
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) out += String.fromCharCode(((c - 65 - k + 26) % 26) + 65);
    else if (c >= 97 && c <= 122) out += String.fromCharCode(((c - 97 - k + 26) % 26) + 97);
    else out += ch;
  }
  return out;
}

function caesar(text) {
  let best = null;
  for (let k = 0; k < 26; k++) {
    const pt = shiftText(text, k);
    const sc = score(pt);
    if (!best || sc > best.score) best = { score: sc, plaintext: pt, key: String(k) };
  }
  return best && {
    cipher: 'caesar', key: best.key, plaintext: best.plaintext,
    confidence: plausibility(best.plaintext),
    method: 'exhaustive keyspace (26 shifts)',
  };
}

function atbash(text) {
  let out = '';
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) out += String.fromCharCode(90 - (c - 65));
    else if (c >= 97 && c <= 122) out += String.fromCharCode(122 - (c - 97));
    else out += ch;
  }
  return {
    cipher: 'atbash', key: '-', plaintext: out,
    confidence: plausibility(out), method: 'fixed involution',
  };
}

function rot13(text) {
  const out = shiftText(text, 13);
  return {
    cipher: 'rot13', key: '13', plaintext: out,
    confidence: plausibility(out), method: 'fixed rotation',
  };
}

function egcd(a, m) {
  for (let x = 1; x < m; x++) if ((a * x) % m === 1) return x;
  return null;
}

function affine(text) {
  let best = null;
  for (let a = 1; a < 26; a += 2) {
    if (a === 13) continue;
    const inv = egcd(a, 26);
    if (inv === null) continue;
    for (let b = 0; b < 26; b++) {
      let out = '';
      for (const ch of text) {
        const c = ch.charCodeAt(0);
        if (c >= 65 && c <= 90) out += String.fromCharCode(((inv * (c - 65 - b) % 26 + 26) % 26) + 65);
        else if (c >= 97 && c <= 122) out += String.fromCharCode(((inv * (c - 97 - b) % 26 + 26) % 26) + 97);
        else out += ch;
      }
      const sc = score(out);
      if (!best || sc > best.sc) best = { sc, out, a, b };
    }
  }
  return best && {
    cipher: 'affine', key: `a=${best.a}, b=${best.b}`, plaintext: best.out,
    confidence: plausibility(best.out), method: 'exhaustive 312-key search',
  };
}

/* --------------------------------------------------------------- periodic */
/* The periodic family: every cipher whose key repeats with a fixed period,
 * so each column of the ciphertext is a monoalphabetic substitution and the
 * coset index of coincidence finds the period for all of them alike. Only
 * the rule that combines a key letter with a ciphertext letter differs, so
 * one attack parameterised by that rule covers Vigenere, Beaufort, Variant
 * Beaufort, Porta and Gronsfeld -- the same coset work is shared, and the
 * variants compete on score so the cipher is identified by being broken. */
const PERIODIC = [
  {
    name: 'vigenere', keys: 26,
    dec: (c, k) => (c - k + 26) % 26,
    keyChar: k => String.fromCharCode(65 + k),
    method: 'coset index-of-coincidence + chi-squared seed + trigram refinement',
  },
  {
    name: 'beaufort', keys: 26,
    dec: (c, k) => (k - c + 26) % 26,
    keyChar: k => String.fromCharCode(65 + k),
    method: 'coset IC + chi-squared seed (Beaufort rule K-C) + trigram refinement',
  },
  {
    name: 'variant_beaufort', keys: 26,
    dec: (c, k) => (c + k) % 26,
    keyChar: k => String.fromCharCode(65 + k),
    method: 'coset IC + chi-squared seed (variant rule C+K) + trigram refinement',
  },
  {
    // Porta's tableau is reciprocal and keyed by letter pairs (A,B), (C,D)...,
    // so thirteen alphabets cover the whole keyspace. The reported key shows
    // the first member of each pair, matching the reference solver.
    name: 'porta', keys: 13,
    dec: (c, k) => (c < 13 ? (c + k) % 13 + 13 : (((c - 13 - k) % 13) + 13) % 13),
    keyChar: k => String.fromCharCode(65 + 2 * k),
    method: "coset IC + chi-squared over Porta's 13 reciprocal tables + refinement",
  },
  {
    name: 'gronsfeld', keys: 10,
    dec: (c, k) => (c - k + 26) % 26,
    keyChar: k => String(k),
    method: 'coset IC + chi-squared over digit shifts + trigram refinement',
  },
];

/** Decrypt `text` under a numeric key array and the variant rule `dec`.
 *  Layout is preserved; only letters advance the key position. */
function periodicDecrypt(text, key, dec) {
  let out = '', i = 0;
  const span = key.length;
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) {
      out += String.fromCharCode(dec(c - 65, key[i % span]) + 65); i++;
    } else if (c >= 97 && c <= 122) {
      out += String.fromCharCode(dec(c - 97, key[i % span]) + 97); i++;
    } else out += ch;
  }
  return out;
}

function periodic(text, maxLen = 20) {
  const t = lettersOnly(text);
  if (t.length < 20) return null;
  const n = Math.min(t.length, 2000);
  const sample = t.slice(0, n);

  // Seeded candidates. Coset IC is variant-independent, so it is computed
  // once per key length and shared. Which periods to seed mirrors the
  // reference solver: on short texts IC and Kasiski are unreliable (with a
  // dozen letters per column the true period loses the ranking as often as
  // it wins -- measured here: a 104-letter Beaufort, key length 7, gated out
  // entirely), so every admissible period is seeded and the *recovered
  // plaintext* picks the winner. On long texts the IC gate holds and only
  // periods above it (plus the best two below) are worth seeding.
  const byLength = [];
  for (let len = 1; len <= Math.min(maxLen, Math.floor(n / 3)); len++) {
    const cosets = [];
    let icSum = 0;
    for (let off = 0; off < len; off++) {
      let coset = '';
      for (let i = off; i < n; i += len) coset += sample[i];
      cosets.push(coset);
      icSum += indexOfCoincidence(coset);
    }
    byLength.push({ len, cosets, avgIc: icSum / len });
  }

  const shortText = n <= 400;
  const admissible = shortText
    ? byLength
    : (() => {
        const sorted = [...byLength].sort((a, b) => b.avgIc - a.avgIc);
        const kept = [];
        let belowGate = 0;
        for (const e of sorted) {
          if (e.len > 1 && e.avgIc < 0.050) {
            if (belowGate >= 2) continue;
            belowGate++;
          }
          kept.push(e);
        }
        return kept;
      })();

  const seeded = [];
  for (const { len, cosets } of admissible) {
    for (let v = 0; v < PERIODIC.length; v++) {
      const variant = PERIODIC[v];
      const key = [];
      for (const coset of cosets) {
        let bestK = 0, bestScore = -Infinity;
        for (let k = 0; k < variant.keys; k++) {
          let s = 0;
          for (const ch of coset) s += UNI[variant.dec(ch.charCodeAt(0) - 65, k)];
          if (s > bestScore) { bestScore = s; bestK = k; }
        }
        key.push(bestK);
      }
      seeded.push({ v, len, key });
    }
  }
  if (!seeded.length) return null;

  // Stage 1: one trigram sweep per candidate -- chi-squared judges each coset
  // in isolation and gets sparse columns wrong. A single coordinate pass is
  // cheap and separates real readings from seeded noise.
  const swept = [];
  for (const cand of seeded) {
    const variant = PERIODIC[cand.v];
    const keyArr = cand.key.slice();
    const decrypt = k => periodicDecrypt(sample, k, variant.dec);
    let cur = score(decrypt(keyArr));
    for (let p = 0; p < cand.len; p++) {
      const orig = keyArr[p];
      let bestVal = orig;
      for (let k = 0; k < variant.keys; k++) {
        if (k === orig) continue;
        keyArr[p] = k;
        const s = score(decrypt(keyArr));
        if (s > cur) { cur = s; bestVal = k; }
      }
      keyArr[p] = bestVal;
    }
    swept.push({ sc: cur, v: cand.v, key: keyArr });
  }
  swept.sort((a, b) => b.sc - a.sc);

  // Stage 2: full multi-pass refinement for the genuine contenders, then
  // pair moves for the leaders. One sweep pass is not always enough -- a pair
  // of wrong adjacent key positions can hold each other in place (measured:
  // HARBOPE -> HARBOUR needed the U and R re-picked together).
  const NOISE_FLOOR = -4.6;
  const contenders = swept.filter(c => c.sc >= NOISE_FLOOR).slice(0, 14);
  for (const c of swept) {
    if (contenders.length >= 6) break;
    if (!contenders.includes(c)) contenders.push(c);
  }

  // Rank on the objective the final answer is judged by: trigrams *and* real
  // words. The word term must be computed on a decryption of the original
  // text -- the letters-only sample has no spaces, so no words -- and it is
  // what keeps an overfitted long key (manufactured trigram patches that
  // spell nothing) below a stalled-but-honest short period.
  const rankOf = c => {
    const variant = PERIODIC[c.v];
    const plain = periodicDecrypt(text, c.key, variant.dec);
    return score(plain) + 2.5 * wordRate(plain) - 0.012 * c.key.length;
  };

  const makeTools = cand => {
    const variant = PERIODIC[cand.v];
    const keyArr = cand.key;
    const decrypt = k => periodicDecrypt(sample, k, variant.dec);
    let cur = score(decrypt(keyArr));
    const sweep = () => {
      let changed = false;
      for (let p = 0; p < keyArr.length; p++) {
        const orig = keyArr[p];
        let bestVal = orig;
        for (let k = 0; k < variant.keys; k++) {
          if (k === orig) continue;
          keyArr[p] = k;
          const s = score(decrypt(keyArr));
          if (s > cur) { cur = s; bestVal = k; changed = true; }
        }
        keyArr[p] = bestVal;
      }
      return changed;
    };
    return { variant, keyArr, decrypt, sweep, get cur() { return cur; }, set cur(v) { cur = v; } };
  };

  // Sweep every contender to convergence (cheap: strict-improvement moves
  // on a finite space), then rank.
  for (const cand of contenders) {
    const t = makeTools(cand);
    while (t.sweep()) { /* converge */ }
    cand.rank = rankOf(cand);
  }
  contenders.sort((a, b) => b.rank - a.rank);

  // Pair moves, only for the leaders: jointly re-pick adjacent key pairs.
  // Single-coordinate sweeps cannot escape two mutually-wrong neighbours
  // (measured: HARBOPE -> HARBOUR needed U and R re-picked together), and on
  // short texts the extra freedom of a long key otherwise lets overfitted
  // trigram patches out-score the stalled true period. Bounded to periods
  // short enough that a pair of columns still holds real evidence.
  for (const cand of contenders.slice(0, 5)) {
    if (!shortText || cand.key.length < 2 || cand.key.length > 14) continue;
    const t = makeTools(cand);
    for (let pass = 0; pass < 2; pass++) {
      let changed = false;
      for (let p = 0; p < t.keyArr.length; p++) {
        const q = (p + 1) % t.keyArr.length;
        if (q === p) break;
        const origP = t.keyArr[p], origQ = t.keyArr[q];
        let keepP = origP, keepQ = origQ;
        for (let a = 0; a < t.variant.keys; a++) {
          for (let b = 0; b < t.variant.keys; b++) {
            if (a === origP && b === origQ) continue;
            t.keyArr[p] = a; t.keyArr[q] = b;
            const s = score(t.decrypt(t.keyArr));
            if (s > t.cur) { t.cur = s; keepP = a; keepQ = b; changed = true; }
          }
        }
        t.keyArr[p] = keepP; t.keyArr[q] = keepQ;
      }
      if (!changed) break;
      while (t.sweep()) { /* converge after unlocking */ }
    }
    cand.rank = rankOf(cand);
  }
  contenders.sort((a, b) => b.rank - a.rank);

  let best = contenders[0];

  const variant = PERIODIC[best.v];
  // One last sweep on the winner judged by trigrams *and* word hits. Sparse
  // cosets (long key, short text) leave single letters wrong and only real
  // words can distinguish the alternatives.
  {
    const keyArr = best.key.slice();
    const obj = k => {
      const plain = periodicDecrypt(text, k, variant.dec);
      return score(plain) + 2.5 * wordRate(plain);
    };
    let cur = obj(keyArr);
    for (let pass = 0; pass < 3; pass++) {
      let changed = false;
      for (let p = 0; p < keyArr.length; p++) {
        const orig = keyArr[p];
        let bestVal = orig;
        for (let k = 0; k < variant.keys; k++) {
          if (k === orig) continue;
          keyArr[p] = k;
          const s = obj(keyArr);
          if (s > cur) { cur = s; bestVal = k; changed = true; }
        }
        keyArr[p] = bestVal;
      }
      if (!changed) break;
    }
    best.key = keyArr;
  }

  // Shortest equivalent key: a period that is a multiple of the true one can
  // fit the text as well, and the scoring penalty does not always settle it,
  // so collapse a repeated key (KEMOMKEMOM -> KEMOM) explicitly.
  for (let d = 1; d < best.key.length; d++) {
    if (best.key.length % d) continue;
    let same = true;
    for (let i = 0; i < best.key.length; i++) {
      if (best.key[i] !== best.key[i % d]) { same = false; break; }
    }
    if (same) { best.key = best.key.slice(0, d); break; }
  }

  const pt = periodicDecrypt(text, best.key, variant.dec);
  return {
    cipher: variant.name, key: best.key.map(variant.keyChar).join(''),
    plaintext: pt, confidence: plausibility(pt), method: variant.method,
  };
}

/* ------------------------------------------------------- trithemius */
/** Progressive-key: shift = (start + i*step) mod 26. 650 keys, no period to
 *  find, so a monogram sweep refined by trigrams settles it outright. */
function trithemius(text) {
  const t = lettersOnly(text);
  if (t.length < 16) return null;
  const sample = t.slice(0, 600);
  const sweep = [];
  for (let start = 0; start < 26; start++) {
    // step 0 is a Caesar shift, which the Caesar sweep already reports.
    for (let step = 1; step < 26; step++) {
      let s = 0;
      for (let i = 0; i < sample.length; i++) {
        const k = (start + i * step) % 26;
        s += UNI[(sample.charCodeAt(i) - 65 - k + 26) % 26];
      }
      sweep.push([s, start, step]);
    }
  }
  sweep.sort((a, b) => b[0] - a[0]);
  let best = null;
  for (const [, start, step] of sweep.slice(0, 6)) {
    let plain = '';
    for (let i = 0; i < sample.length; i++) {
      const k = (start + i * step) % 26;
      plain += String.fromCharCode((sample.charCodeAt(i) - 65 - k + 26) % 26 + 65);
    }
    const sc = score(plain);
    if (!best || sc > best.sc) best = { sc, start, step };
  }
  if (!best) return null;

  let pt = '', i = 0;
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    const k = (best.start + i * best.step) % 26;
    if (c >= 65 && c <= 90) { pt += String.fromCharCode((c - 65 - k + 26) % 26 + 65); i++; }
    else if (c >= 97 && c <= 122) { pt += String.fromCharCode((c - 97 - k + 26) % 26 + 97); i++; }
    else pt += ch;
  }
  return {
    cipher: 'trithemius', key: `start=${best.start}, step=${best.step}`,
    plaintext: pt, confidence: plausibility(pt),
    method: 'exhaustive 650-key progressive sweep',
  };
}

/* ------------------------------------------------------------ autokey */
/** Autokey: the key is a short primer followed by the plaintext itself, so
 *  once the primer length m is guessed the message splits into m independent
 *  chains, each fully determined by a single primer letter. Chain
 *  decomposition (chi-squared per chain) + coordinate ascent on the primer --
 *  the reference solver's attack, ported. */
function autokeyDecryptStream(text, primer) {
  let out = '', pos = 0;
  const plain = [];
  const m = primer.length;
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90 || c >= 97 && c <= 122) {
      const idx = c >= 97 ? c - 97 : c - 65;
      const shift = pos < m ? primer[pos] : plain[pos - m];
      const v = (idx - shift + 26) % 26;
      plain.push(v);
      const letter = String.fromCharCode(v + 65);
      out += c >= 97 ? letter.toLowerCase() : letter;
      pos++;
    } else out += ch;
  }
  return out;
}

function autokey(text) {
  const t = lettersOnly(text);
  if (t.length < 40) return null;
  const n = Math.min(t.length, 400);
  const sample = t.slice(0, n);
  const maxPrimer = Math.min(14, Math.floor(n / 8));
  let best = null;

  for (let m = 1; m <= maxPrimer; m++) {
    // Chain j holds letter positions j, j+m, j+2m, ...: each is keyed by the
    // plaintext letter m positions earlier, so one primer letter determines
    // the whole chain. Seed each chain by monogram fit.
    const primer = [];
    for (let j = 0; j < m; j++) {
      let bestStart = 0, bestS = -Infinity;
      for (let s = 0; s < 26; s++) {
        let sum = 0, prev = s, k = 0;
        for (let i = j; i < n; i += m, k++) {
          const c = sample.charCodeAt(i) - 65;
          const p = (c - (k === 0 ? s : prev) + 26) % 26;
          sum += UNI[p];
          prev = p;
        }
        if (sum > bestS) { bestS = sum; bestStart = s; }
      }
      primer.push(bestStart);
    }

    // Coordinate ascent over the primer using whole-text trigram fitness.
    const decrypt = k => autokeyDecryptStream(sample, k).toUpperCase();
    let fit = score(decrypt(primer));
    for (let pass = 0; pass < 4; pass++) {
      let improved = false;
      for (let pos = 0; pos < m; pos++) {
        const orig = primer[pos];
        let keep = orig;
        for (let cand = 0; cand < 26; cand++) {
          if (cand === orig) continue;
          primer[pos] = cand;
          const f = score(decrypt(primer));
          if (f > fit) { fit = f; keep = cand; improved = true; }
        }
        primer[pos] = keep;
      }
      if (!improved) break;
    }
    if (!best || fit > best.fit) best = { fit, primer: primer.slice() };
  }
  if (!best) return null;

  const pt = autokeyDecryptStream(text, best.primer);
  return {
    cipher: 'autokey',
    key: best.primer.map(k => String.fromCharCode(65 + k)).join(''),
    plaintext: pt, confidence: plausibility(pt),
    method: 'chain decomposition + trigram ascent on the primer',
  };
}

function substitution(text) {
  const t = lettersOnly(text);
  if (t.length < 40) return null;

  const apply = (src, key) => {
    let out = '';
    for (const ch of src) {
      const c = ch.charCodeAt(0);
      if (c >= 65 && c <= 90) out += key[c - 65];
      else if (c >= 97 && c <= 122) out += key[c - 97].toLowerCase();
      else out += ch;
    }
    return out;
  };

  // Seed from frequency order, then hill-climb with random transpositions.
  const counts = new Array(26).fill(0);
  for (const ch of t) counts[ch.charCodeAt(0) - 65]++;
  const byFreq = counts.map((c, i) => [c, i]).sort((a, b) => b[0] - a[0]).map(p => p[1]);
  const english = 'ETAOINSHRDLCUMWFGYPBVKJXQZ';
  let key = new Array(26).fill('A');
  byFreq.forEach((letterIdx, rank) => { key[letterIdx] = english[rank]; });

  let bestKey = key.slice();
  let bestScore = score(apply(t, bestKey));

  // Each restart climbs from a perturbation of the best key so far, which
  // escapes the letter-pair local optima that plain frequency seeding hits.
  const restarts = t.length > 400 ? 12 : 25;
  for (let restart = 0; restart < restarts; restart++) {
    let cur = bestKey.slice();
    if (restart > 0) {
      for (let s = 0; s < 3 + (restart % 5); s++) {
        const i = (Math.random() * 26) | 0, j = (Math.random() * 26) | 0;
        [cur[i], cur[j]] = [cur[j], cur[i]];
      }
    }
    let curScore = score(apply(t, cur));
    let improved = true;
    while (improved) {                 // exhaustive pairwise swaps until stable
      improved = false;
      for (let i = 0; i < 25; i++) {
        for (let j = i + 1; j < 26; j++) {
          [cur[i], cur[j]] = [cur[j], cur[i]];
          const s = score(apply(t, cur));
          if (s > curScore) { curScore = s; improved = true; }
          else [cur[i], cur[j]] = [cur[j], cur[i]];
        }
      }
    }
    if (curScore > bestScore) { bestScore = curScore; bestKey = cur.slice(); }
  }

  // Trigram score alone confuses rare letters (b/v/m all fit similar contexts).
  // A final pass judged partly on real word hits breaks those ties.
  const objective = k => {
    const sample = text.slice(0, 800);
    const out = apply(sample, k);
    // Use the same decryption for both signals.  This is the polishing hot
    // path, and the old version applied the full substitution twice per swap.
    return score(t.length > 600 ? out.slice(0, 600) : out) + 2.5 * wordRate(out);
  };
  let polished = bestKey.slice();
  let polishedScore = objective(polished);
  let moved = true;
  while (moved) {
    moved = false;
    for (let i = 0; i < 25; i++) {
      for (let j = i + 1; j < 26; j++) {
        [polished[i], polished[j]] = [polished[j], polished[i]];
        const s = objective(polished);
        if (s > polishedScore) { polishedScore = s; moved = true; }
        else [polished[i], polished[j]] = [polished[j], polished[i]];
      }
    }
  }
  bestKey = polished;

  const pt = apply(text, bestKey);
  return {
    cipher: 'substitution', key: bestKey.join(''), plaintext: pt,
    confidence: plausibility(pt) * 0.95,
    method: 'frequency seed + hill-climbing (8 restarts)',
  };
}

function railfence(text) {
  let best = null;
  for (let rails = 2; rails <= Math.min(10, text.length - 1); rails++) {
    const pattern = [];
    let r = 0, dir = 1;
    for (let i = 0; i < text.length; i++) {
      pattern.push(r);
      if (r === 0) dir = 1; else if (r === rails - 1) dir = -1;
      r += dir;
    }
    const out = new Array(text.length);
    let idx = 0;
    for (let row = 0; row < rails; row++) {
      for (let i = 0; i < text.length; i++) if (pattern[i] === row) out[i] = text[idx++];
    }
    const pt = out.join('');
    const sc = score(pt);
    if (!best || sc > best.sc) best = { sc, pt, rails };
  }
  return best && {
    cipher: 'railfence', key: `${best.rails} rails`, plaintext: best.pt,
    confidence: plausibility(best.pt), method: 'exhaustive rail count 2-10',
  };
}

const MORSE = {
  '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
  '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
  '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
  '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
  '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
  '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
  '---..': '8', '----.': '9',
};

/* --------------------------------------------------------------- decoders */
/* These unwrap an encoding layer; the result is fed back through the whole
   solver, which is how multi-layer puzzles get peeled apart. */

const DECODERS = [
  {
    name: 'base64',
    // The [0-9+/=] guard matches the identifier's heuristic: real base64
    // of text almost always carries digits or padding, while pure letters
    // whose length happens to be a multiple of four do not -- peeling those
    // as a layer pays for a full solver pass on garbage.
    test: s => /^[A-Za-z0-9+/=\s]+$/.test(s) && /[0-9+/=]/.test(s)
      && s.replace(/\s/g, '').length % 4 === 0 && s.replace(/\s/g, '').length >= 8,
    run: s => { try { return atob(s.replace(/\s/g, '')); } catch { return null; } },
  },
  {
    name: 'base16 (hex)',
    test: s => /^[0-9a-fA-F\s]+$/.test(s) && s.replace(/\s/g, '').length % 2 === 0
      && s.replace(/\s/g, '').length >= 8,
    run: s => {
      const h = s.replace(/\s/g, '');
      let out = '';
      for (let i = 0; i < h.length; i += 2) out += String.fromCharCode(parseInt(h.substr(i, 2), 16));
      return out;
    },
  },
  {
    name: 'binary',
    test: s => /^[01\s]+$/.test(s) && s.replace(/\s/g, '').length >= 16,
    run: s => {
      const b = s.replace(/\s/g, '');
      let out = '';
      for (let i = 0; i + 8 <= b.length; i += 8) out += String.fromCharCode(parseInt(b.substr(i, 8), 2));
      return out;
    },
  },
  {
    name: 'decimal bytes',
    test: s => /^[\d\s,]+$/.test(s) && (s.match(/\d+/g) || []).length >= 4,
    run: s => (s.match(/\d+/g) || []).map(n => String.fromCharCode(+n)).join(''),
  },
  {
    name: 'morse',
    test: s => /^[.\-\s/|]+$/.test(s) && s.includes('.') && s.includes('-'),
    run: s => s.trim().split(/\s*[/|]\s*|\s{2,}/).map(
      w => w.trim().split(/\s+/).map(c => MORSE[c] || '').join('')
    ).join(' ').trim(),
  },
  {
    name: 'reversed text',
    test: s => s.length >= 12,
    run: s => [...s].reverse().join(''),
  },
];

/** Single-byte XOR — the classic CTF warm-up. */
function xorSingle(bytes) {
  let best = null;
  for (let k = 1; k < 256; k++) {
    let out = '';
    for (const b of bytes) out += String.fromCharCode(b ^ k);
    if (!/^[\x09\x0a\x0d\x20-\x7e]*$/.test(out)) continue;
    const sc = score(out);
    if (!best || sc > best.sc) best = { sc, out, k };
  }
  return best && {
    cipher: 'xor_single', key: `0x${best.k.toString(16).padStart(2, '0')}`,
    plaintext: best.out, confidence: plausibility(best.out),
    method: 'exhaustive 255-key byte search',
  };
}

/* ------------------------------------------------------------------ solve */

/**
 * Try every direct cipher on `text`, then recursively peel encoding layers.
 * Returns the highest-confidence report found within `depth` layers.
 */
// A result above this mark is good enough that another statistical search is
// more likely to manufacture a competing reading than improve the answer.  It
// is deliberately below the UI's "SOLVED" threshold: Caesar and Vigenere
// samples with uncommon proper nouns still get to skip an unnecessary 25-restart
// substitution climb.
const FAST_ANSWER_CONFIDENCE = 0.58;

function solve(text, depth = 3, chain = []) {
  const results = [];
  const push = r => { if (r && r.plaintext && r.plaintext.trim()) results.push(r); };
  const bestConfidence = () => results.reduce((best, r) => Math.max(best, r.confidence || 0), 0);

  // Run the tiny, deterministic keyspaces first.  This used to start every
  // request with Vigenere and substitution too, even after a Caesar sweep had
  // already recovered a readable message.  On an ordinary Caesar ciphertext
  // that meant thousands of redundant trigram evaluations on the worker.
  push(caesar(text));
  push(atbash(text));
  push(rot13(text));
  push(affine(text));
  push(trithemius(text));
  push(railfence(text));

  const bytes = [...text].map(c => c.charCodeAt(0) & 0xff);
  if (bytes.length >= 8 && bytes.length < 4000) push(xorSingle(bytes));

  // The periodic family (Vigenere, Beaufort, Variant Beaufort, Porta,
  // Gronsfeld) shares one coset search and is still far cheaper than a
  // mixed-alphabet climb.  Autokey's chain search costs about the same.
  // Do not pay for either when a deterministic attack already explains
  // the input.
  if (bestConfidence() < FAST_ANSWER_CONFIDENCE) {
    push(periodic(text));
    push(autokey(text));
  }

  for (const r of results) r.chain = chain.slice();

  if (depth > 0) {
    // Decoding a clearly shaped layer is cheaper and more informative than a
    // substitution climb over the wrapper.  Keep reverse for last: every long
    // string has a reverse, so trying it early doubles the search tree.
    let decoders = DECODERS.filter(dec => dec.name !== 'reversed text');
    // A string of nothing but 0s, 1s and whitespace is binary -- yet the
    // base64, hex and decimal decoders all match it too, and each would pay
    // for a full recursive solve on garbage before the real decoder ran.
    // One guard removes three dead branches.
    if (/^[01\s]+$/.test(text)) decoders = decoders.filter(dec => dec.name === 'binary');
    for (const dec of decoders) {
      if (!dec.test(text)) continue;
      let inner;
      try { inner = dec.run(text); } catch { continue; }
      if (!inner || inner.length < 4 || inner === text) continue;

      // A decoded layer that is already readable is itself an answer, and no
      // other decoder (or deeper search) can beat a readable decoding of the
      // right shape -- stop this branch here.
      const direct = plausibility(inner);
      if (direct > 0.35) {
        results.push({
          cipher: dec.name, key: '-', plaintext: inner, confidence: direct,
          method: 'encoding layer decoded', chain: chain.concat(dec.name),
        });
        break;
      }
      const sub = solve(inner, depth - 1, chain.concat(dec.name));
      // A layer that had to be unwrapped is a stronger explanation than a
      // direct read of encoded-looking text, so nudge nested hits upward.
      if (sub) { sub.confidence = Math.min(1, sub.confidence * 1.05); results.push(sub); }
    }
  }

  // The mixed-alphabet climber is the expensive last resort.  It cannot improve
  // a convincing direct or decoded answer, and skipping it in those cases keeps
  // the browser responsive for the overwhelmingly common Caesar/base64 inputs.
  if (lettersOnly(text).length >= 60 && bestConfidence() < FAST_ANSWER_CONFIDENCE) {
    push(substitution(text));
  }

  // Reverse is intentionally deferred until after the real cipher attacks.  It
  // remains part of the general layered search, without making each branch pay
  // for a second copy of the full solver.
  if (depth > 0 && bestConfidence() < FAST_ANSWER_CONFIDENCE) {
    const reverse = DECODERS.find(dec => dec.name === 'reversed text');
    if (reverse && reverse.test(text)) {
      let inner;
      try { inner = reverse.run(text); } catch { inner = null; }
      if (inner && inner.length >= 4 && inner !== text) {
        const direct = plausibility(inner);
        if (direct > 0.35) {
          results.push({
            cipher: reverse.name, key: '-', plaintext: inner, confidence: direct,
            method: 'encoding layer decoded', chain: chain.concat(reverse.name),
          });
        }
        const sub = solve(inner, depth - 1, chain.concat(reverse.name));
        if (sub) { sub.confidence = Math.min(1, sub.confidence * 1.05); results.push(sub); }
      }
    }
  }

  if (!results.length) return null;
  // Priors: the hill-climber can manufacture plausible-looking garbage, so a
  // simple cipher that explains the text as well wins the tie.
  const PRIOR = { substitution: 0.80, railfence: 0.88, affine: 0.95, xor_single: 0.95 };
  for (const r of results) r.ranked = r.confidence * (PRIOR[r.cipher] || 1);
  results.sort((a, b) => b.ranked - a.ranked);
  return results[0];
}

/** Identify likely cipher families without solving — the fast first pass. */
function identify(text) {
  const ic = indexOfCoincidence(text);
  const t = lettersOnly(text);
  const guesses = [];
  const clean = text.replace(/\s/g, '');

  if (/^[01\s]+$/.test(text) && clean.length >= 16) guesses.push(['binary', 0.9]);
  else if (/^[.\-\s/|]+$/.test(text)) guesses.push(['morse', 0.9]);
  else if (/^[0-9a-fA-F\s]+$/.test(text) && clean.length >= 8) guesses.push(['base16', 0.8]);
  else if (/^[A-Za-z0-9+/=\s]+$/.test(text) && clean.length % 4 === 0 && /[0-9+/=]/.test(text)) {
    guesses.push(['base64', 0.75]);
  }

  if (t.length >= 20) {
    if (ic > 0.06) { guesses.push(['caesar / substitution', 0.7]); guesses.push(['transposition', 0.4]); }
    else if (ic > 0.045) guesses.push(['periodic (short key)', 0.6]);
    else guesses.push(['vigenere / beaufort / periodic', 0.65]);
  }
  if (!guesses.length) guesses.push(['unknown', 0.2]);
  guesses.sort((a, b) => b[1] - a[1]);
  return { ic, entropy: entropy(text), guesses };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { solve, identify, plausibility, score, wordRate, indexOfCoincidence, entropy };
}
