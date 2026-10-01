/* Accuracy harness for the browser solver:  node ventures/cipher-solver-web/test.js
 * Each case asserts that the recovered plaintext matches, ignoring case and
 * non-letters, since ciphers vary in how they preserve formatting.
 */
'use strict';

if (typeof atob === 'undefined') {
  global.atob = s => Buffer.from(s, 'base64').toString('binary');
}
const S = require('./solver.js');

const PT1 = 'The council of Venice has decreed that all merchant vessels must pay the new harbour tax before entering the lagoon';
const PT2 = 'Attack the northern gate at dawn and bring every available soldier with you because the enemy is waiting there';
const PT3 = 'Meet me behind the old library after sunset and do not tell anyone about this message under any circumstances';

const norm = s => s.toUpperCase().replace(/[^A-Z]/g, '');

function shift(t, k) {
  return [...t].map(ch => {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) return String.fromCharCode(((c - 65 + k) % 26) + 65);
    if (c >= 97 && c <= 122) return String.fromCharCode(((c - 97 + k) % 26) + 97);
    return ch;
  }).join('');
}
function vigEnc(p, key) {
  let out = '', i = 0;
  for (const ch of p) {
    const u = ch.toUpperCase();
    if (u >= 'A' && u <= 'Z') {
      out += String.fromCharCode((u.charCodeAt(0) - 65 + key.charCodeAt(i % key.length) - 65) % 26 + 65);
      i++;
    } else out += ch;
  }
  return out;
}
function atbashEnc(p) {
  return [...p].map(ch => {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) return String.fromCharCode(90 - (c - 65));
    if (c >= 97 && c <= 122) return String.fromCharCode(122 - (c - 97));
    return ch;
  }).join('');
}
function subEnc(p, key) {
  return [...p].map(ch => {
    const c = ch.charCodeAt(0);
    if (c >= 65 && c <= 90) return key[c - 65];
    if (c >= 97 && c <= 122) return key[c - 97].toLowerCase();
    return ch;
  }).join('');
}
function railEnc(p, rails) {
  const rows = Array.from({ length: rails }, () => []);
  let r = 0, d = 1;
  for (const ch of p) {
    rows[r].push(ch);
    if (r === 0) d = 1; else if (r === rails - 1) d = -1;
    r += d;
  }
  return rows.flat().join('');
}
/* Periodic-family encoders: the rule that combines key value k (0..25, or a
 * digit for Gronsfeld) with plaintext letter p, over letters only, layout
 * preserved — the same convention as vigEnc above. */
function periodicEnc(p, key, rule) {
  let out = '', i = 0;
  for (const ch of p) {
    const u = ch.toUpperCase();
    if (u >= 'A' && u <= 'Z') {
      out += String.fromCharCode(rule(u.charCodeAt(0) - 65, key[i % key.length]) % 26 + 65);
      i++;
    } else out += ch;
  }
  return out;
}
const beaufortEnc = (p, key) => periodicEnc(p, [...key].map(c => c.charCodeAt(0) - 65),
  (p, k) => (k - p + 26) % 26);
const variantBeaufortEnc = (p, key) => periodicEnc(p, [...key].map(c => c.charCodeAt(0) - 65),
  (p, k) => (p - k + 26) % 26);
const portaEnc = (p, key) => periodicEnc(p, [...key].map(c => (c.charCodeAt(0) - 65) >> 1),
  (p, half) => p < 13 ? (p + half) % 13 + 13 : (((p - 13 - half) % 13) + 13) % 13);
const gronsfeldEnc = (p, digits) => periodicEnc(p, [...digits].map(Number),
  (p, k) => (p + k) % 26);
function trithemiusEnc(p, start, step) {
  let out = '', i = 0;
  for (const ch of p) {
    const u = ch.toUpperCase();
    if (u >= 'A' && u <= 'Z') {
      out += String.fromCharCode((u.charCodeAt(0) - 65 + ((start + i * step) % 26)) % 26 + 65);
      i++;
    } else out += ch;
  }
  return out;
}
function autokeyEnc(p, primer) {
  let out = '';
  const plain = [];
  for (const ch of p) {
    const u = ch.toUpperCase();
    if (u >= 'A' && u <= 'Z') {
      const i = plain.length;
      const k = i < primer.length ? primer.charCodeAt(i) - 65 : plain[i - primer.length];
      const c = (u.charCodeAt(0) - 65 + k) % 26;
      plain.push(u.charCodeAt(0) - 65);
      out += String.fromCharCode(c + 65);
    } else out += ch;
  }
  return out;
}
const b64 = s => Buffer.from(s, 'binary').toString('base64');
const hex = s => [...s].map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
const xor1 = (s, k) => [...s].map(c => String.fromCharCode(c.charCodeAt(0) ^ k)).join('');

const CASES = [
  ['caesar +3', shift(PT1, 3), PT1],
  ['caesar +7', shift(PT2, 7), PT2],
  ['caesar +19', shift(PT3, 19), PT3],
  ['rot13', shift(PT1, 13), PT1],
  ['atbash', atbashEnc(PT2), PT2],
  ['vigenere LAMP', vigEnc(PT1, 'LAMP'), PT1],
  ['vigenere SECRET', vigEnc(PT2, 'SECRET'), PT2],
  ['vigenere CIPHERKEY', vigEnc(PT3, 'CIPHERKEY'), PT3],
  ['substitution', subEnc(PT1 + ' ' + PT2, 'QWERTYUIOPASDFGHJKLZXCVBNM'), PT1 + ' ' + PT2],
  ['railfence 4', railEnc(norm(PT2), 4), PT2],
  ['base64', b64(PT1), PT1],
  ['hex', hex(PT2), PT2],
  ['binary', [...PT3].map(c => c.charCodeAt(0).toString(2).padStart(8, '0')).join(' '), PT3],
  ['xor single 0x2a', xor1(PT1, 0x2a), PT1],
  ['b64 -> hex -> caesar', b64(hex(shift(PT2, 5))), PT2],
  ['b64 -> xor', b64(xor1(PT3, 0x5f)), PT3],
  ['hex -> vigenere', hex(vigEnc(PT1, 'LAMP')), PT1],
  ['reversed', [...PT2].reverse().join(''), PT2],
  ['morse', '.... . .-.. .-.. --- / - .... . .-. . / .. / .- -- / .-- .- .. - .. -. --. / ..-. --- .-. / -.-- --- ..-',
    'hello there i am waiting for you'],
  // The periodic family. Beaufort, Porta, Trithemius and autokey are reported
  // under their own names; Gronsfeld and Variant Beaufort are Vigenere with a
  // restricted (digits) or negated key, so identical ciphertexts mean the
  // solver legitimately reports vigenere with the equivalent key — the
  // plaintext assertion is the contract.
  ['beaufort LEMON', beaufortEnc(PT1, 'LEMON'), PT1],
  ['beaufort TRIANGULAR', beaufortEnc(PT3, 'TRIANGULAR'), PT3],
  ['variant beaufort LAMP', variantBeaufortEnc(PT2, 'LAMP'), PT2],
  ['porta LEMON', portaEnc(PT1, 'LEMON'), PT1],
  ['porta PRINTER', portaEnc(PT3, 'PRINTER'), PT3],
  ['gronsfeld 31415', gronsfeldEnc(PT2, '31415'), PT2],
  ['trithemius 2,3', trithemiusEnc(PT1, 2, 3), PT1],
  ['trithemius 9,7', trithemiusEnc(PT3, 9, 7), PT3],
  ['autokey QUEEN', autokeyEnc(PT1, 'QUEEN'), PT1],
  ['autokey BRAVE', autokeyEnc(PT3, 'BRAVE'), PT3],
  ['hex -> beaufort', hex(beaufortEnc(PT2, 'HARBOR')), PT2],
];

let pass = 0;
const t0 = Date.now();
for (const [name, ct, expected] of CASES) {
  const started = Date.now();
  let r = null;
  try { r = S.solve(ct); } catch (e) { r = null; }
  const got = r ? norm(r.plaintext) : '';
  const ok = got === norm(expected);
  if (ok) pass++;
  const ms = Date.now() - started;
  console.log(
    `${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(24)} ${String(ms).padStart(5)}ms  ` +
    `${r ? r.cipher + ' key=' + r.key + ' conf=' + r.confidence.toFixed(2) : 'no result'}`
  );
  if (!ok && r) console.log(`      got: ${r.plaintext.slice(0, 70)}`);
}
const DIAGNOSTIC_CASES = [
  {
    name: 'diagnostic: short text',
    report: S.diagnose('QXJ', S.identify('QXJ'), null),
    status: 'no-high-confidence',
    code: 'short-text',
  },
  {
    name: 'diagnostic: non-ASCII symbols',
    report: S.diagnose('ЖЯ☿⚚', S.identify('ЖЯ☿⚚'), null),
    status: 'no-high-confidence',
    code: 'non-ascii',
  },
  {
    name: 'diagnostic: encoded shape',
    report: S.diagnose('SGVsbG8gdGhlcmU=', S.identify('SGVsbG8gdGhlcmU='), null),
    status: 'no-high-confidence',
    code: 'wrapper-shape',
  },
  {
    name: 'diagnostic: high candidate is not failure',
    report: S.diagnose(PT1, S.identify(PT1), { confidence: 0.85 }),
    status: 'high-confidence',
    code: null,
  },
];

let diagnosticPass = 0;
for (const test of DIAGNOSTIC_CASES) {
  const codes = test.report.reasons.map(reason => reason.code);
  const ok = test.report.candidateStatus === test.status && (!test.code || codes.includes(test.code));
  if (ok) diagnosticPass++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${test.name}`);
  if (!ok) console.log(`      status=${test.report.candidateStatus}; reasons=${codes.join(', ')}`);
}

console.log(`\n${pass}/${CASES.length} solver cases and ${diagnosticPass}/${DIAGNOSTIC_CASES.length} diagnostic cases passed in ${Date.now() - t0}ms`);
process.exit(pass === CASES.length && diagnosticPass === DIAGNOSTIC_CASES.length ? 0 : 1);
