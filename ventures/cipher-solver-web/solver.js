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

function vigenereDecrypt(text, key) {
  let out = '', i = 0;
  for (const ch of text) {
    const c = ch.charCodeAt(0);
    const k = key.charCodeAt(i % key.length) - 65;
    if (c >= 65 && c <= 90) { out += String.fromCharCode(((c - 65 - k + 26) % 26) + 65); i++; }
    else if (c >= 97 && c <= 122) { out += String.fromCharCode(((c - 97 - k + 26) % 26) + 97); i++; }
    else out += ch;
  }
  return out;
}

function vigenere(text, maxLen = 20) {
  const t = lettersOnly(text);
  if (t.length < 20) return null;
  let best = null;

  for (let len = 1; len <= Math.min(maxLen, Math.floor(t.length / 3)); len++) {
    // Average coset IC tells us whether this period is plausible. Keep weak
    // candidates too: a wrong-but-close period is cheap to reject after
    // refinement, and multiples of the true period score well here.
    let icSum = 0;
    for (let off = 0; off < len; off++) {
      let coset = '';
      for (let i = off; i < t.length; i += len) coset += t[i];
      icSum += indexOfCoincidence(coset);
    }
    const avgIc = icSum / len;
    if (len > 1 && avgIc < 0.050) continue;

    // Seed each position with the chi-squared best shift...
    let key = '';
    for (let off = 0; off < len; off++) {
      let coset = '';
      for (let i = off; i < t.length; i += len) coset += t[i];
      let bestShift = 0, bestScore = -Infinity;
      for (let k = 0; k < 26; k++) {
        let s = 0;
        for (const ch of coset) s += UNI[(ch.charCodeAt(0) - 65 - k + 26) % 26];
        if (s > bestScore) { bestScore = s; bestShift = k; }
      }
      key += String.fromCharCode(65 + bestShift);
    }

    // ...then refine: chi-squared judges each coset in isolation and gets
    // sparse positions wrong, so re-pick every key letter against the trigram
    // score of the *whole* decryption, sweeping until nothing improves.
    let keyArr = [...key];
    let cur = score(vigenereDecrypt(t, keyArr.join('')));
    for (let pass = 0; pass < 4; pass++) {
      let changed = false;
      for (let p = 0; p < len; p++) {
        const orig = keyArr[p];
        let bestCh = orig;
        for (let k = 0; k < 26; k++) {
          keyArr[p] = String.fromCharCode(65 + k);
          const s = score(vigenereDecrypt(t, keyArr.join('')));
          if (s > cur) { cur = s; bestCh = keyArr[p]; changed = true; }
        }
        keyArr[p] = bestCh;
      }
      if (!changed) break;
    }
    key = keyArr.join('');

    const pt = vigenereDecrypt(text, key);
    // Penalise longer keys: any period that is a multiple of the true one can
    // fit equally well, and we want the shortest explanation.
    const sc = score(pt) - 0.012 * len;
    if (!best || sc > best.sc) best = { sc, pt, key };
  }
  if (!best) return null;

  // One last sweep on the winner judged by trigrams *and* word hits. Sparse
  // cosets (long key, short text) leave single letters wrong and only real
  // words can distinguish the alternatives.
  {
    let keyArr = [...best.key];
    // Decryption dominates this polish pass.  Keep the one plaintext for both
    // scoring terms instead of decrypting it twice for every candidate letter.
    const obj = k => {
      const plain = vigenereDecrypt(text, k);
      return score(plain) + 2.5 * wordRate(plain);
    };
    let cur = obj(keyArr.join(''));
    for (let pass = 0; pass < 3; pass++) {
      let changed = false;
      for (let p = 0; p < keyArr.length; p++) {
        const orig = keyArr[p];
        let bestCh = orig;
        for (let k = 0; k < 26; k++) {
          keyArr[p] = String.fromCharCode(65 + k);
          const s = obj(keyArr.join(''));
          if (s > cur) { cur = s; bestCh = keyArr[p]; changed = true; }
        }
        keyArr[p] = bestCh;
      }
      if (!changed) break;
    }
    best = { key: keyArr.join(''), pt: vigenereDecrypt(text, keyArr.join('')) };
  }

  return {
    cipher: 'vigenere', key: best.key, plaintext: best.pt,
    confidence: plausibility(best.pt),
    method: 'coset index-of-coincidence + chi-squared seed + trigram refinement',
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
    test: s => /^[A-Za-z0-9+/=\s]+$/.test(s) && s.replace(/\s/g, '').length % 4 === 0
      && s.replace(/\s/g, '').length >= 8,
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
  push(railfence(text));

  const bytes = [...text].map(c => c.charCodeAt(0) & 0xff);
  if (bytes.length >= 8 && bytes.length < 4000) push(xorSingle(bytes));

  // Vigenere is much cheaper than a mixed-alphabet search, but it is still a
  // whole-key refinement loop.  Do not pay for it when a deterministic attack
  // already explains the input.
  if (bestConfidence() < FAST_ANSWER_CONFIDENCE) push(vigenere(text));

  for (const r of results) r.chain = chain.slice();

  if (depth > 0) {
    // Decoding a clearly shaped layer is cheaper and more informative than a
    // substitution climb over the wrapper.  Keep reverse for last: every long
    // string has a reverse, so trying it early doubles the search tree.
    const decoders = DECODERS.filter(dec => dec.name !== 'reversed text');
    for (const dec of decoders) {
      if (!dec.test(text)) continue;
      let inner;
      try { inner = dec.run(text); } catch { continue; }
      if (!inner || inner.length < 4 || inner === text) continue;

      // A decoded layer that is already readable is itself an answer.
      const direct = plausibility(inner);
      if (direct > 0.35) {
        results.push({
          cipher: dec.name, key: '-', plaintext: inner, confidence: direct,
          method: 'encoding layer decoded', chain: chain.concat(dec.name),
        });
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
    else if (ic > 0.045) guesses.push(['vigenere (short key)', 0.6]);
    else guesses.push(['vigenere / polyalphabetic', 0.65]);
  }
  if (!guesses.length) guesses.push(['unknown', 0.2]);
  guesses.sort((a, b) => b[1] - a[1]);
  return { ic, entropy: entropy(text), guesses };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { solve, identify, plausibility, score, wordRate, indexOfCoincidence, entropy };
}
