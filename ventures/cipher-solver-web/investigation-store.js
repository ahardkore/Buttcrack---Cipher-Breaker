/* Versioned, bounded snapshots. No storage side effects and no trusted proof flags. */
(function(root,factory){if(typeof module==='object' && module.exports)module.exports=factory(require('./examples.js'));else root.InvestigationStore=factory(CIPHER_EXAMPLES);})(typeof globalThis==='object' ? globalThis : this,function(examples){
  'use strict';
  const KEY='buttcrack.browser.investigations.v1',SCHEMA='browser-investigations/v1';
  function str(value,name,max){if(typeof value!=='string' || value.length>max)throw new Error(`${name}: invalid text or limit exceeded (${max}).`);return value;}
  function num(value,name,max){if(typeof value!=='number' || !Number.isFinite(value) || value<0 || value>max)throw new Error(`${name}: invalid measurement.`);return value;}
  function candidate(r){
    if(r===null)return null;
    if(!r || typeof r!=='object')throw new Error('Invalid candidate.');
    const confidence=num(r.confidence ?? 0,'Score',1),chain=r.chain || [];
    if(!Array.isArray(chain) || chain.length>8)throw new Error('Invalid chain.');
    return {cipher:str(r.cipher,'Cipher',100),key:str(String(r.key ?? ''),'Reported key',4096),plaintext:str(r.plaintext,'Plaintext',20000),method:str(r.method || '', 'Method',2000),confidence,
      ranked:r.ranked===undefined ? confidence : num(r.ranked,'Rank value',2),chain:chain.map(x=>str(x,'Layer',100)),exampleReference:!!r.exampleReference,suppliedKey:!!r.suppliedKey};
    // verified/paradigm fields are deliberately dropped. Restore derives a
    // canonical badge only from the shipped catalog and exact text/key/cipher.
  }
  function attempt(a){
    if(!a || typeof a!=='object')throw new Error('Invalid attempt.');
    const options=a.options;
    if(!options || (options.method!=='auto' && !Object.hasOwn(examples,options.method)) || typeof options.compare!=='boolean' || !Number.isInteger(options.depth) || options.depth<0 || options.depth>3)throw new Error('Invalid saved settings.');
    const key=str(options.key,'Supplied key',512),text=str(a.text,'Ciphertext',20000);
    if(!text.trim())throw new Error('Empty saved ciphertext.');
    const created=str(a.created_at,'Timestamp',80);if(!Number.isFinite(Date.parse(created)))throw new Error('Invalid timestamp.');
    if(!Array.isArray(a.candidates) || a.candidates.length>10)throw new Error('Invalid candidate count.');
    const diagnostic=a.diagnostic || {},list=(items,name)=>{if(!Array.isArray(items) || items.length>40)throw new Error(`Invalid ${name}.`);return items.map(x=>str(typeof x==='string' ? x : x.text,name,2000));};
    const info=a.info ? {ic:num(a.info.ic,'IC',1),entropy:num(a.info.entropy,'Entropy',32),guesses:[]} : null;
    if(info){if(!Array.isArray(a.info.guesses) || a.info.guesses.length>30)throw new Error('Invalid guesses.');info.guesses=a.info.guesses.map(g=>[str(g[0],'Guess',200),num(g[1],'Guess weight',1)]);}
    return {created_at:created,text,options:{method:options.method,key,depth:options.depth,compare:options.compare,exampleId:typeof options.exampleId==='string' && Object.hasOwn(examples,options.exampleId) ? options.exampleId : null},
      result:candidate(a.result),candidates:a.candidates.map(r=>{if(!r)throw new Error('Invalid ranked candidate.');return candidate(r);}),info,diagnostic:{reasons:list(diagnostic.reasons || [],'Reason'),nextSteps:list(diagnostic.nextSteps || [],'Next step'),attempted:list(diagnostic.attempted || [],'Coverage')},elapsed:num(a.elapsed,'Elapsed',3600)};
  }
  function book(value){
    if(!value || value.schema!==SCHEMA || !Array.isArray(value.investigations) || value.investigations.length>12)throw new Error('Expected browser-investigations/v1 with at most 12 investigations.');
    const ids=new Set();
    return {schema:SCHEMA,investigations:value.investigations.map(item=>{
      const id=str(item.id,'ID',100);if(!id || ids.has(id))throw new Error('Duplicate or empty investigation ID.');ids.add(id);
      const name=str(item.name,'Name',100);if(!name.trim())throw new Error('Give each investigation a name.');
      if(!Array.isArray(item.attempts) || item.attempts.length>10)throw new Error('At most 10 attempts per investigation.');
      return {id,name,attempts:item.attempts.map(attempt)};
    })};
  }
  return {KEY,SCHEMA,attempt,book};
});
