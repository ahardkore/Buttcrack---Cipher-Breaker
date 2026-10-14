const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const E=require('../../ventures/cipher-solver-web/examples.js'),B=require('../../ventures/cipher-solver-web/browser-request.js'),S=require('../../ventures/cipher-solver-web/investigation-store.js'),core=require('../../ventures/cipher-solver-web/solver.js');
const text='Wkh frxqflo ri Yhqlfh kdv ghfuhhg wkdw doo phufkdqw yhvvhov pxvw sdb wkh qhz kduerxu wda ehiruh hqwhulqj wkh odjrrq';
function snapshot(){const r=B.run(text,{method:'auto',depth:0});return {created_at:'2026-10-13T12:00:00.000Z',text,...r,elapsed:.2};}

test('all 51 full wiki examples produce exactly their documented reading with explicit live/reference scope',()=>{
  assert.equal(Object.keys(E).length,51);let live=0,reference=0;
  for(const [id,e] of Object.entries(E)){const r=B.run(e.ciphertext,{method:id,key:e.key,exampleId:id,depth:0});assert.equal(r.result.plaintext,e.plaintext,id);assert.equal(r.result.cipher,id);assert.equal(r.candidates.length,1);r.result.exampleReference ? reference++ : live++;assert.ok(fs.readFileSync(`ventures/cipher-solver-web/${e.article}`,'utf8').includes(`index.html?cipher=${id}&amp;example=${id}#solver`));}
  assert.ok(live>=18);assert.ok(reference>0);
});
test('selected unsupported methods and changed examples never silently fall back to Caesar or an old reference',()=>{
  const e=E.playfair;
  for(const options of [{method:'playfair',key:''},{method:'playfair',key:e.key,exampleId:'playfair'}]){const r=B.run(text,options);assert.equal(r.result,null);assert.match(r.diagnostic.attempted[0],/Only the selected playfair/);}
  assert.equal(B.run(e.ciphertext,{method:'playfair',key:'OTHER',exampleId:'playfair'}).result,null);
});
test('supplied-key operations are live and reject malformed keys rather than guessing',()=>{
  assert.equal(B.run(E.caesar.ciphertext,{method:'caesar',key:E.caesar.key}).result.suppliedKey,true);
  assert.throws(()=>B.run(text,{method:'caesar',key:'26'}));assert.throws(()=>B.run(text,{method:'auto',key:'LEMON'}));assert.throws(()=>B.run(text,{method:'constructor'}));assert.throws(()=>B.run(text,{depth:4}));
  assert.notEqual(B.run(E.vigenere.ciphertext,{method:'vigenere',key:'WRONG'}).result.plaintext,E.vigenere.plaintext);
});
test('auto retains its legacy winner and collects real ordered candidates without cycles or fabrication',()=>{
  const r=B.run(text,{depth:0});assert.equal(r.result.plaintext,core.solve(text,0).plaintext);assert.equal(r.result.cipher,'caesar');assert.ok(r.candidates.length>1 && r.candidates.length<=10);assert.equal(r.candidates[0].plaintext,r.result.plaintext);
  assert.ok(r.candidates.every((c,i,arr)=>!i || c.ranked<=arr[i-1].ranked));JSON.stringify(r);
});
test('corpus lookup remains a single actual reference candidate',()=>{
  const {PARADIGM_KRYPTOS}=require('../../ventures/cipher-solver-web/paradigm.js');const r=B.run(PARADIGM_KRYPTOS[0].ciphertext);assert.equal(r.result.verified,true);assert.equal(r.candidates.length,1);
});
test('versioned history preserves exact submitted snapshots and discards trusted proof fields',()=>{
  const a=snapshot();a.result.verified=true;a.result.paradigm={id:'PK10'};const saved=S.attempt(a);assert.equal(saved.text,text);assert.deepEqual(saved.options,a.options);assert.equal(saved.result.verified,undefined);assert.equal(saved.result.paradigm,undefined);
  const book=S.book({schema:S.SCHEMA,investigations:[{id:'one',name:'First investigation',attempts:[saved]}]});assert.deepEqual(JSON.parse(JSON.stringify(book)),book);
});
test('malformed, oversize, duplicate-ID or future-schema history is rejected atomically',()=>{
  const a=snapshot(),i={id:'one',name:'Case',attempts:[a]};
  for(const b of [{schema:'future',investigations:[]},{schema:S.SCHEMA,investigations:[i,i]},{schema:S.SCHEMA,investigations:Array(13).fill(i)},{schema:S.SCHEMA,investigations:[{...i,attempts:Array(11).fill(a)}]}])assert.throws(()=>S.book(b));
  assert.throws(()=>S.attempt({...a,text:'A'.repeat(20001)}));assert.throws(()=>S.attempt({...a,candidates:[null]}));assert.throws(()=>S.attempt({...a,elapsed:Infinity}));
});
test('large worked examples are complete, not infobox previews',()=>{assert.ok(E.binary.ciphertext.length>240);assert.equal(E.binary.ciphertext.split(/\s+/).filter(Boolean).length,E.binary.source_plaintext.length);});
