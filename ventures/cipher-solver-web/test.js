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
console.log(`\n${pass}/${CASES.length} passed in ${Date.now() - t0}ms`);
process.exit(pass === CASES.length ? 0 : 1);
