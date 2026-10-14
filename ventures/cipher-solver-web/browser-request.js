/* Strict method routing, supplied-key arithmetic and honest example references. */
(function(root,factory){
  if(typeof module==='object' && module.exports)module.exports=factory(require('./solver.js'),require('./examples.js'));
  else root.BrowserRequest=factory({solve,diagnose,identify,plausibility,periodic,PERIODIC,shiftText,caesar,atbash,rot13,affine,trithemius,railfence,xorSingle,autokey,substitution,quagmire3,periodicDecrypt,autokeyDecryptStream,quagmire3Decrypt,DECODERS},CIPHER_EXAMPLES);
})(typeof globalThis==='object' ? globalThis : this,function(S,examples){
  'use strict';
  const decoderNames={base16:'base16 (hex)',decimal_ascii:'decimal bytes',reverse:'reversed text'};
  const attacks={caesar:S.caesar,atbash:S.atbash,rot13:S.rot13,affine:S.affine,trithemius:S.trithemius,railfence:S.railfence,rail_fence:S.railfence,autokey:S.autokey,quagmire3:S.quagmire3,
    substitution:text=>text.replace(/[^a-zA-Z]/g,'').length>=60 ? S.substitution(text) : null,
    xor_single:text=>text.length>=8 && text.length<4000 ? S.xorSingle([...text].map(c=>c.charCodeAt(0)&255)) : null};
  function settings(value={}) {
    const method=value.method ?? 'auto',key=value.key ?? '',depth=value.depth ?? 3;
    if(typeof method!=='string' || (method!=='auto' && !Object.hasOwn(examples,method)))throw new Error('Choose a listed method.');
    if(typeof key!=='string' || key.length>512)throw new Error('Key limit is 512 characters.');
    if(!Number.isInteger(depth) || depth<0 || depth>3)throw new Error('Encoding depth must be 0–3.');
    if(value.compare!==undefined && typeof value.compare!=='boolean')throw new Error('Comparison must be a boolean.');
    if(method==='auto' && key)throw new Error('Select a specific method before supplying a key.');
    return {method,key,depth,compare:method==='auto' && !!value.compare,exampleId:typeof value.exampleId==='string' ? value.exampleId : null};
  }
  function supplied(text,method,key) {
    let plaintext;
    if(method==='caesar'){
      if(!/^\d+$/.test(key) || Number(key)>25)throw new Error('Caesar shift must be 0–25.');
      plaintext=S.shiftText(text,Number(key));
    } else if(method==='affine'){
      const match=/^(?:a=)?([0-9]+),\s*(?:b=)?([0-9]+)$/.exec(key.replace(/ /g,''));
      if(!match || Number(match[1])>25 || Number(match[2])>25)throw new Error('Affine key must be a=5,b=8 (both 0–25).');
      const a=Number(match[1]),b=Number(match[2]),inv=Array.from({length:26},(_,i)=>i).find(i=>(i*a)%26===1);
      if(inv===undefined)throw new Error('Affine multiplier must be coprime to 26.');
      plaintext=[...text].map(c=>{if(!/^[a-zA-Z]$/.test(c))return c;const base=c===c.toUpperCase()?65:97;return String.fromCharCode(((inv*(c.charCodeAt(0)-base-b)%26)+26)%26+base);}).join('');
    } else if(method==='trithemius'){
      const match=/^start=([0-9]+),\s*step=([0-9]+)$/.exec(key);
      if(!match || Number(match[1])>25 || Number(match[2])>25)throw new Error('Trithemius key must be start=0, step=1 (0–25).');
      let index=0;plaintext=[...text].map(c=>{if(!/^[a-zA-Z]$/.test(c))return c;const base=c===c.toUpperCase()?65:97,shift=(Number(match[1])+index++*Number(match[2]))%26;return String.fromCharCode((c.charCodeAt(0)-base-shift+26)%26+base);}).join('');
    } else if(S.PERIODIC.some(v=>v.name===method)){
      const variant=S.PERIODIC.find(v=>v.name===method);
      if(!(method==='gronsfeld' ? /^[0-9]+$/ : /^[A-Za-z]+$/).test(key))throw new Error('Use ASCII letters for the key, or decimal digits for Gronsfeld.');
      const values=[...key.toUpperCase()].map(c=>method==='gronsfeld' ? Number(c) : method==='porta' ? Math.floor((c.charCodeAt(0)-65)/2) : c.charCodeAt(0)-65);
      plaintext=S.periodicDecrypt(text,values,variant.dec);
    } else if(method==='autokey' || method==='quagmire3'){
      if(!/^[A-Za-z]+$/.test(key))throw new Error('Use an ASCII letter key.');
      const alphabet=method==='quagmire3' ? 'KRYPTOSABCDEFGHIJLMNQUVWXZ' : 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      const values=[...key.toUpperCase()].map(c=>alphabet.indexOf(c));
      plaintext=method==='autokey' ? S.autokeyDecryptStream(text,values) : S.quagmire3Decrypt(text,values);
    } else return null;
    return {cipher:method,key,plaintext,confidence:S.plausibility(plaintext),chain:[],suppliedKey:true,method:'Live supplied-key decryption; not key recovery or independent proof.'};
  }
  function run(text,value={}) {
    if(typeof text!=='string' || !text.trim() || text.length>20000)throw new Error('Use 1–20,000 ciphertext characters.');
    const options=settings(value), info=S.identify(text);
    let result=null,candidates=[];
    if(options.method==='auto')result=S.solve(text,options.depth,[],{compare:options.compare,collect:items=>{candidates=items;}});
    else {
      const method=options.method,example=examples[method];
      if(options.key)result=supplied(text,method,options.key);
      if(!result && !options.key){
        if(Object.hasOwn(attacks,method))result=attacks[method](text);
        else if(S.PERIODIC.some(v=>v.name===method))result=S.periodic(text,20,method);
        else {const decoder=S.DECODERS.find(d=>d.name===(decoderNames[method] || method));if(decoder && decoder.test(text)){const plaintext=decoder.run(text);result={cipher:method,key:'—',plaintext,confidence:S.plausibility(plaintext),chain:[],method:'Live selected encoding decoder.'};}}
      }
      if(!result && options.exampleId===method && text===example.ciphertext && options.key===example.key){
        result={cipher:method,key:options.key || '—',plaintext:example.plaintext,confidence:S.plausibility(example.plaintext),chain:[],exampleReference:true,
          method:'Exact worked-example reference generated from the Python cipher at build time. This browser did not recover its key or execute this method/key operation.'};
      }
      if(result)candidates=[result];
    }
    const diagnostic=S.diagnose(text,info,result);
    if(options.method!=='auto'){
      diagnostic.attempted=[`Only the selected ${options.method} method${options.key ? ' with a supplied key' : ''} was requested. No fallback to other cipher families.`];
      if(!result){diagnostic.reasons=[{text:'The selected method/key operation is unavailable in this browser or yielded no candidate. Unsupported methods do not fall back to Caesar.'}];diagnostic.nextSteps=['Use the unchanged worked example as a labelled reference demonstration, select Auto-detect for implemented attacks, or use the full version for additional methods.'];}
    }
    return {result,candidates,info,diagnostic,options};
  }
  return {run,settings};
});
