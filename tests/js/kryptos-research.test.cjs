const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const R=require('../../kryptos-app/research-engine.js');
const {PARADIGM_KRYPTOS:catalog}=require('../../kryptos-app/paradigm.js');
const hypothesis=(extra={})=>({name:'Proposal',original:'LXFOPVEFRNHR',proposed:'ATTACKATDAWN',alphabet:R.STANDARD,steps:[{method:'vigenere',key:'LEMON'}],evidence:'A test vector',objections:'Round-trip is not intention',...extra});

test('all ten corpus methods decrypt AND independently implemented inverses re-encrypt exactly',()=>{
  for(const record of catalog){
    const h=hypothesis({original:record.ciphertext,proposed:record.plaintext,alphabet:R.KRYPTOS,steps:R.templates(record.id,catalog)}),r=R.evaluate(h,catalog);
    assert.equal(r.source.label,'Verified corpus match',record.id);
    assert.equal(r.verification.label,'Reproduced decryption',record.id);
    assert.equal(r.output,record.plaintext,record.id);
    assert.equal(r.reconstructed_ciphertext,record.ciphertext,record.id);
    assert.equal(r.verification.independent_verification,false);
    assert.equal(r.verification.intended_plaintext_proven,false);
    assert.equal(r.intermediates.length,h.steps.length);
  }
});
test('source association does not verify a competing plaintext or a missing method',()=>{
  const rec=catalog[0];
  const wrong=R.evaluate(hypothesis({original:rec.ciphertext,proposed:'WRONGPLAINTEXT',alphabet:R.KRYPTOS,steps:R.templates(rec.id,catalog)}),catalog);
  assert.equal(wrong.source.label,'Verified corpus match');assert.equal(wrong.verification.label,'Research hypothesis');
  const missing=R.evaluate(hypothesis({original:rec.ciphertext,proposed:rec.plaintext,steps:[]}),catalog);
  assert.equal(missing.verification.reproduced,false);
  const changed=R.evaluate(hypothesis({original:'Z'+rec.ciphertext.slice(1),proposed:rec.plaintext,alphabet:R.KRYPTOS,steps:R.templates(rec.id,catalog)}),catalog);
  assert.equal(changed.source.id,null);assert.equal(changed.verification.reproduced,false);
});
test('reproducing an arbitrary key does not prove the plaintext or earn a corpus badge',()=>{
  const r=R.evaluate(hypothesis(),catalog);assert.equal(r.verification.reproduced,true);assert.equal(r.source.id,null);
  assert.match(r.verification.detail,/not independent/);
  assert.equal(R.evaluate(hypothesis({steps:[{method:'vigenere',key:'WRONG'}]}),catalog).verification.reproduced,false);
});
test('ASCII normalization preserves original transcription and does not expand Unicode',()=>{
  const r=R.report(hypothesis({original:'lxf opv\nefrnhrß?',proposed:'Attack at dawn!'}),catalog,'fixed');
  assert.equal(r.original_text,'lxf opv\nefrnhrß?');assert.equal(r.normalized_text,'LXFOPVEFRNHR');assert.equal(r.normalized_proposed,'ATTACKATDAWN');
  assert.equal(r.created_at,'fixed');assert.match(r.normalization,/ASCII/);assert.equal(r.verification.reproduced,true);
});
test('alphabet permutations, phase and variant conventions are explicit',()=>{
  assert.equal(R.keyedAlphabet('KRYPTOS'),R.KRYPTOS);
  assert.throws(()=>R.alphabet('A'.repeat(26)));assert.throws(()=>R.alphabet(R.STANDARD+'!'));
  const plain='ATTACKATDAWN';
  for(const method of ['vigenere','beaufort','variant_beaufort','caesar','substitution','reverse']){
    const step={method,key:method==='caesar' ? '7' : 'LEMON',phase:0,alphabet:R.KRYPTOS};
    const cipher=R.transform(plain,step,false);assert.equal(R.transform(cipher,step,true),plain,method);
  }
  const step={method:'vigenere',key:'LEMON',phase:2,alphabet:R.STANDARD};
  assert.equal(R.transform(R.transform(plain,step,false),step),plain);
  assert.notEqual(R.transform('LXFOPVEFRNHR',step),'ATTACKATDAWN');
});
test('stable repeated keyword letters and rectangular routes invert without padding',()=>{
  for(const step of [{method:'columnar',key:'BALLOON'},{method:'spiral',key:'7'},{method:'spiral',key:'1'}]){
    const plain='ABCDEFG'.repeat(5),cipher=R.transform(plain,step,false);
    assert.equal(R.transform(cipher,step),plain);
  }
  assert.throws(()=>R.transform('ABC',{method:'columnar',key:'KEYS'}),/divide/);
  assert.throws(()=>R.transform('ABC',{method:'spiral',key:'2'}),/divide/);
});
test('noninvertible matrices, incomplete triples and invalid numeric keys remain unexecuted',()=>{
  for(const step of [{method:'hill3',key:'AAAAAAAAA'},{method:'hill3',key:'ALCHEMIST'},{method:'caesar',key:'26'},{method:'spiral',key:'0'},{method:'vigenere',key:''}]){
    const r=R.evaluate(hypothesis({original:'AB',proposed:'AB',steps:[step]}),catalog);
    assert.equal(r.verification.label,'Research hypothesis');assert.ok(r.failure);assert.equal(r.output,null);
  }
});
test('manual steps preserve honest partial traces without inventing a decryption',()=>{
  const r=R.evaluate(hypothesis({steps:[{method:'reverse',key:''},{method:'manual',key:'Undocumented device'}]}),catalog);
  assert.equal(r.intermediates.length,1);assert.equal(r.output,null);assert.equal(r.verification.reproduced,false);
  assert.match(r.failure,/not been executed/);
});
test('reports are re-importable and all derived claims are ignored',()=>{
  const report=R.report(hypothesis(),catalog);assert.equal(report.schema,R.SCHEMA);
  assert.equal(report.intermediates[0].input,report.normalized_text);assert.equal(report.intermediates[0].output,'ATTACKATDAWN');
  assert.deepEqual(R.importReport(JSON.parse(JSON.stringify(report))),report.hypothesis);
  report.hypothesis.proposed='FORGED';report.verification={label:'Verified corpus match',reproduced:true};report.source={id:'PK10'};report.intermediates=[{output:'FORGED'}];
  const r=R.evaluate(R.importReport(report),catalog);assert.equal(r.source.id,null);assert.equal(r.verification.reproduced,false);assert.notEqual(r.output,'FORGED');
  assert.throws(()=>R.importReport({schema:'other',hypothesis:hypothesis()}));
});
test('comparison exposes different source texts and bounded repeated-sequence offsets',()=>{
  const a=R.evaluate(hypothesis({proposed:'ABCABCABC',steps:[]}),catalog),b=R.evaluate(hypothesis({original:'OTHER',proposed:'XXABCABCABC',steps:[]}),catalog);
  const comparison=R.compare(a,b,2);
  assert.equal(comparison.same_ciphertext,false);assert.equal(comparison.rows[0].b_position,2);assert.equal(comparison.rows[0].matches,true);
  assert.ok(comparison.shared_sequences.some(row=>row.pattern==='ABC' && row.suggested_offset===2));
  assert.ok(comparison.shared_sequences.length<=20);
  assert.throws(()=>R.compare(a,b,8001));assert.throws(()=>R.compare(a,b,0,-1));
});
test('no silent clipping, oversized pipelines, or executable method injection',()=>{
  for(const h of [hypothesis({original:'A'.repeat(16001)}),hypothesis({original:'A'.repeat(8001)}),hypothesis({steps:Array(33).fill({method:'reverse'})}),hypothesis({steps:[{method:'constructor'}]}),hypothesis({steps:[{method:'vigenere',key:'LEMON',phase:-1}]}),hypothesis({steps:[{method:'columnar',key:'KEY',phase:1}]}),hypothesis({original:12})]) assert.throws(()=>R.evaluate(h,catalog));
});
test('empty IC and entropy are unmeasurable; unequal lengths are penalized',()=>{
  assert.equal(R.metrics('').ic,null);assert.equal(R.metrics('A').ic,null);assert.equal(R.metrics('').entropy,null);
  assert.equal(R.metrics('AAAA').entropy,0);
  const r=R.evaluate(hypothesis({proposed:'ATTACK'}),catalog);assert.equal(r.verification.ciphertext_explanation.compared,12);assert.equal(r.verification.ciphertext_explanation.matches,6);assert.equal(r.verification.ciphertext_explanation.fraction,.5);
});
test('the explorer uses canonical PK text and explicitly excludes incomplete legacy excerpts',()=>{
  const data=vm.runInNewContext(fs.readFileSync('kryptos-app/paradigm.js','utf8')+'\n'+fs.readFileSync('kryptos-app/data.js','utf8')+'; CIPHERS_DATA');
  for(const rec of catalog){assert.equal(data[rec.id].ciphertext,rec.ciphertext);assert.equal(data[rec.id].plaintext,rec.plaintext);}
  assert.equal(data.K2.reference_complete,false);assert.equal(data.K3.reference_complete,false);assert.equal(data.K4.plaintext,'');
  const k1=R.evaluate(hypothesis({original:data.K1.ciphertext,proposed:data.K1.plaintext,alphabet:R.KRYPTOS,steps:[{method:'vigenere',key:'PALIMPSEST'}]}),catalog);
  assert.equal(k1.verification.reproduced,true);assert.equal(k1.source.id,null);
});
test('K4 anchor constraints check fixed positions without claiming a full solution',()=>{
  const cipher='OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR';
  const chars=Array(97).fill('A');
  for(const [start,word] of [[21,'EAST'],[25,'NORTHEAST'],[63,'BERLIN'],[69,'CLOCK']]) [...word].forEach((c,i)=>{chars[start+i]=c;});
  const r=R.evaluate(hypothesis({original:cipher,proposed:chars.join(''),steps:[]}),catalog);
  assert.equal(r.known_constraints.length,4);assert.ok(r.known_constraints.every(item=>item.matches));
  assert.equal(r.source.id,null);assert.equal(r.verification.label,'Research hypothesis');assert.match(r.constraint_note,/not verification/);
  const displaced=R.evaluate(hypothesis({original:cipher,proposed:'A'+chars.join(''),steps:[]}),catalog);
  assert.ok(displaced.known_constraints.some(item=>!item.matches));
});
