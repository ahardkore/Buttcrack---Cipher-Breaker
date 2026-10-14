/* Solver-first UI: no automatic persistence; requests and snapshots have identities. */
'use strict';
const SAMPLES = {
  caesar: "Wkh frxqflo ri Yhqlfh kdv ghfuhhg wkdw doo phufkdqw yhvvhov pxvw sdb wkh qhz kduerxu wda ehiruh hqwhulqj wkh odjrrq",
  vigenere: "LTFPNK FWP NAGEHQGY GMIP AF SLWZ PYD NGTNS TGEDN LVMXWANAP SAAOIQG HIFW JOG QPCMJDE FWP EZTXY UH HAUITNS ISEDT",
  substitution: "Zit egxfeos gy Ctfoet iql rtekttr ziqz qss dtkeiqfz ctlltsl dxlz hqn zit ftv iqkwgxk zqb wtygkt tfztkofu zit squggf Dttz dt wtiofr zit gsr sowkqkn qyztk lxfltz qfr rg fgz ztss qfngft qwgxz ziol dtllqut xfrtk qfn eokexdlzqfetl",
  layered: "NDY3OTc5NjY2ODcwMjA3OTZkNmEyMDczNzQ3Nzc5NmQ2YTc3NzMyMDZjNjY3OTZhMjA2Njc5MjA2OTY2NjI3MzIwNjY3MzY5MjA2Nzc3NmU3MzZjMjA2YTYxNmE3NzY0MjA2NjYxNjY2ZTcxNjY2NzcxNmEyMDc4NzQ3MTY5NmU2YTc3MjA2MjZlNzk2ZDIwNjQ3NDdhMjA2NzZhNjg2NjdhNzg2YTIwNzk2ZDZhMjA2YTczNmE3MjY0MjA2ZTc4MjA2MjY2NmU3OTZlNzM2YzIwNzk2ZDZhNzc2YQ==",
  morse: ".... . .-.. .-.. --- / - .... . .-. . / .. / .- -- / .-- .- .. - .. -. --. / ..-. --- .-. / -.-- --- ..-",
  pk1: "MQRALWVSJIMSXGJSVWQPHJMDINKXGIMHNKYUTXTTGJCYIABTJUMQEOFBITNBMONGVWETDLAIJPQYMZIKBQVRXZHUIJVDJLTQHIQYHEQKFTPTJYCONAFXYWQIBONAYXGWJFFIQMVXNVQYQFMWKFEJQYZFBWKXBKDQLJRELWGWDKHECRSFBKOVQJCPYDNKXYHE",
  // The periodic family, each ciphertext produced by the reference Python
  // implementation (see build_pages.py: the worked examples and these demos
  // describe the same code the full solver runs).
  beaufort: "Otn uodqtga pocydj ztihrwpny kznqc rmzddhyktbo wdizxd bd hnpuad qdcdol bkd pjvhbktgzx nqmtjn ogokovrqd",
  variant_beaufort: "Ndn uaelebcn eyynwvrx bassu mqydlvyo njees pqirfxwh khvfa cve ecrnf sguunr pnmojplr zka hhr vwauef",
  porta: "Auy rppoppsl olbt ipgrrl ecfar ond jxpkwej oa u uxgnrk bwwa ah arqiyum rfbyx mtww shm peigowc yxamccc",
  gronsfeld: "Gjwqfwdl gwrn xij qpvumhsr pzwqsty wii stde vfrdjrt npqetxdcpf zqumm ykf wqwlok umdx eswlwit blul umh cmsiv",
  trithemius: "Rwwrfvmpiyk tqnk vbweumr jaa znuplpvn lnh ycqe so y umto fe mdzv sw wsknbr nknbh aoq oipqurhqq htz wcea",
  autokey: "Jbi uhpcgsc siyvg vcrh ckl msgkmlhqbuvrut delznvi lzbc a diu baht xitxy ogpi migsnviu miweej",
};

const $=selector=>document.querySelector(selector),input=$('#ciphertext'),output=$('#output'),go=$('#go');
let worker=null,revision=0,lastAttempt=null,activeExample=null;
const esc=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const status=text=>{$('#solver-status').textContent=text;};
function notifyAttempt(attempt){lastAttempt=attempt;window.dispatchEvent(new CustomEvent('browser-solver-attempt',{detail:attempt}));}
function controls(){return {method:$('#solver-method').value,key:$('#solver-key').value,depth:Number($('#solver-depth').value),compare:$('#solver-compare').checked,exampleId:activeExample};}
function stop(message='Search stopped. No partial result was saved.') {
  revision++;if(worker)worker.terminate();worker=null;go.disabled=false;$('#stop').hidden=true;
  if(message)status(message);
}
function diagnosticHTML(d){return `<details class="card"><summary>Limitations & next checks for this input</summary><p>Observations are not proof of why this ciphertext resisted decryption.</p><ul>${(d.reasons || []).map(r=>`<li>${esc(typeof r==='string' ? r : r.text)}</li>`).join('')}</ul><ul>${(d.nextSteps || []).map(r=>`<li>${esc(r)}</li>`).join('')}</ul><h4>Coverage actually requested</h4><ul>${(d.attempted || []).map(r=>`<li>${esc(r)}</li>`).join('')}</ul></details>`;}
function canonicalFor(attempt,result){
  const known=knownParadigmResult(attempt.text);
  return known && result && !result.chain?.length && known.cipher===result.cipher && known.key===result.key && known.plaintext===result.plaintext ? known : null;
}
function candidateHTML(result,attempt,index=0){
  const canonical=canonicalFor(attempt,result),example=result.exampleReference && attempt.options.exampleId===attempt.options.method && CIPHER_EXAMPLES[attempt.options.method];
  const exactExample=example && result.key===(example.key || '—') && result.cipher===attempt.options.method && attempt.text===example.ciphertext && result.plaintext===example.plaintext && attempt.options.key===example.key;
  const label=canonical ? 'Verified corpus match' : exactExample ? 'Worked example reference — not a new solve' : result.suppliedKey ? 'Supplied-key reading — not independently verified' : 'Statistical candidate — not proven';
  return `<section class="card candidate-result" aria-label="Candidate ${index+1}"><div class="solved-head"><span class="label ${canonical ? '' : 'low'}">${esc(label)}</span><span>${esc(result.cipher)} · key ${esc(result.key)}</span></div>
    <p class="candidate-note">${canonical ? 'Exact normalized association with '+esc(canonical.paradigm.id)+'. Not a new cryptanalytic discovery.' : exactExample ? 'This is the unchanged, build-time worked example. The browser did not execute this method/key operation or recover its key.' : 'A readable output or passing arithmetic is not proof of the intended plaintext. Compare method, key and source context.'}</p>
    <div class="plaintext">${esc(result.plaintext)}</div>
    <details class="candidate-details"><summary>Key, method, ranking &amp; evidence</summary><table class="evidence"><tr><th>Cipher</th><td>${esc(result.cipher)}</td></tr><tr><th>Key</th><td><code>${esc(result.key)}</code></td></tr><tr><th>Family</th><td>${esc(CIPHER_EXAMPLES[result.cipher]?.family || 'Encoding / construction / unclassified')}</td></tr><tr><th>Method</th><td>${esc(result.method)}</td></tr><tr><th>Decode chain</th><td>${esc([...(result.chain || []),result.cipher].join(' → '))}</td></tr><tr><th>English-likeness</th><td>${Number(result.confidence || 0).toFixed(3)} — not a probability</td></tr><tr><th>Rank value</th><td>${Number(result.ranked ?? result.confidence ?? 0).toFixed(3)} — bounded-search heuristic</td></tr>${canonical ? `<tr><th>Corpus evidence</th><td>${esc(canonical.paradigm.verification)}</td></tr>` : ''}</table></details></section>`;
}
function display(attempt,historical=false){
  output.replaceChildren();const result=attempt.result;
  if(historical){const banner=make('p',`Restored local snapshot from ${attempt.created_at}. No new solve or independent verification was run.`,'restored-notice');output.append(banner);}
  const primary=make('div');
  primary.innerHTML=result ? candidateHTML(result,attempt) : '<section class="card"><h3>No candidate returned</h3><p>The requested operation may be unsupported or lack enough evidence. Expand the next checks below.</p></section>';
  output.append(primary);
  if(result){const copy=make('button','Copy candidate text','ghost');copy.type='button';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(result.plaintext);copy.textContent='Copied';}catch(_error){status('Clipboard unavailable. Select and copy the candidate text instead.');}});primary.querySelector('.candidate-result').append(copy);}
  const info=attempt.info;
  if(info){const stats=make('details',undefined,'card');stats.append(make('summary','Input statistics & identification'));stats.append(make('p',`${attempt.text.length} characters · IC ${Number(info.ic).toFixed(4)} · entropy ${Number(info.entropy).toFixed(3)}. Heuristic guesses, not probabilities: ${(info.guesses || []).slice(0,3).map(g=>g[0]).join(', ')}`));output.append(stats);}
  const rankings=make('details',undefined,'card candidate-rankings');rankings.append(make('summary',`Candidate rankings (${attempt.candidates.length} returned)`));
  rankings.append(make('p','Actual candidates from this bounded search, ordered by confidence with family priors. Attacks may internally shortlist; this is not exhaustive. Equivalent methods can yield the same plaintext. Scores and close competitors are not proof.'));
  const count=make('select');count.setAttribute('aria-label','Number of candidate readings');for(const n of [5,10]){const option=make('option',`Top ${n}`);option.value=String(n);count.append(option);}count.value='5';
  const cards=make('div');const renderRanks=()=>{cards.innerHTML=attempt.candidates.slice(0,Number(count.value)).map((r,i)=>`<h4>Rank #${i+1}${i && Math.abs((attempt.candidates[0].ranked ?? attempt.candidates[0].confidence)-(r.ranked ?? r.confidence))<=.03 ? ' · close to leader (heuristic)' : ''}</h4>${candidateHTML(r,attempt,i)}`).join('');};count.addEventListener('change',renderRanks);renderRanks();rankings.append(count,cards);output.append(rankings);
  const checks=make('div');checks.innerHTML=diagnosticHTML(attempt.diagnostic);output.append(checks);
  const submitted=make('details',undefined,'card');submitted.append(make('summary','Submitted text & settings for this result'),make('pre',attempt.text),make('p',`Method: ${attempt.options.method}; supplied key: ${attempt.options.key || 'none'}; encoding depth: ${attempt.options.depth}; explore families: ${attempt.options.compare ? 'yes' : 'no'}. ${attempt.elapsed.toFixed(2)} seconds.`));output.append(submitted);
}
function crack(){
  const text=input.value,options=controls();
  if(!text.trim()){status('Paste ciphertext first.');input.focus();return;}
  if(text.length>20000){status('Input limit is 20,000 characters.');return;}
  stop(null);const current=revision;notifyAttempt(null);go.disabled=true;$('#stop').hidden=false;status('Analysing on this device…');output.innerHTML='<section class="card" role="status">Searching… use Stop to cancel.</section>';
  try{
    const job=new Worker('worker.js');worker=job;
    const finish=()=>{job.terminate();if(worker===job)worker=null;go.disabled=false;$('#stop').hidden=true;};
    job.onmessage=e=>{
      if(current!==revision || worker!==job)return;
      const m=e.data;
      if(m.type==='identified'){status('Input measured. Searching the requested methods…');return;}
      if(m.type==='error'){finish();output.replaceChildren();status(`Operation unavailable: ${m.message}`);return;}
      if(m.type!=='done')return;
      finish();
      const attempt={created_at:new Date().toISOString(),text,options:m.options || options,result:m.result || null,candidates:m.candidates || (m.result ? [m.result] : []),info:m.info,diagnostic:m.diagnostic || {reasons:[],nextSteps:[],attempted:[]},elapsed:m.elapsed || 0};
      display(attempt);notifyAttempt(attempt);
      status(input.value===text ? 'Result ready. Statistical readings are not proven; saving is optional.' : 'Result ready for the submitted text; the input has since changed. Saving records the submitted snapshot, not your edited draft.');
      const reduce=window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      output.scrollIntoView({block:'start',behavior:reduce ? 'auto' : 'smooth'});output.focus({preventScroll:true});
    };
    job.onerror=()=>{if(current!==revision)return;finish();output.replaceChildren();status('Worker unavailable. Serve this site locally rather than opening an HTML file directly.');};
    job.postMessage({text,options});
  }catch(error){stop(`Solver could not start: ${error.message}`);output.replaceChildren();}
}
function loadExample(name){
  if(!Object.hasOwn(CIPHER_EXAMPLES,name)){status('Unknown example. Choose a listed method.');return;}
  stop(null);notifyAttempt(null);output.replaceChildren();const example=CIPHER_EXAMPLES[name];activeExample=name;input.value=example.ciphertext;$('#solver-method').value=name;$('#solver-key').value=example.key;$('#solver-compare').checked=false;$('#solver-compare').disabled=true;
  $('#example-notice').hidden=false;$('#example-notice').textContent=`${example.title} worked example loaded with its documented key. Press Solve to run supported supplied-key operations or inspect an explicitly labelled reference demonstration.`;
  status('Worked example loaded; no search has run and nothing has been saved.');
}
for(const [name,example] of Object.entries(CIPHER_EXAMPLES)){const option=make('option',example.title);option.value=name;$('#solver-method').append(option);}
go.addEventListener('click',crack);$('#stop').addEventListener('click',()=>{stop();output.replaceChildren();notifyAttempt(null);});
input.addEventListener('keydown',e=>{if((e.ctrlKey || e.metaKey) && e.key==='Enter'){e.preventDefault();crack();}});
$('#clear').addEventListener('click',()=>{stop(null);input.value='';$('#solver-method').value='auto';$('#solver-key').value='';$('#solver-depth').value='3';$('#solver-compare').checked=false;$('#solver-compare').disabled=false;output.replaceChildren();activeExample=null;$('#example-notice').hidden=true;notifyAttempt(null);status('Current input, settings and result cleared. Saved investigations remain unchanged.');input.focus();});
$('#load-sample').addEventListener('click',()=>{stop(null);activeExample=null;$('#example-notice').hidden=true;$('#solver-method').value='auto';$('#solver-key').value='';$('#solver-compare').disabled=false;input.value=SAMPLES[$('#sample-select').value] || '';output.replaceChildren();notifyAttempt(null);status('Example loaded. Press Solve; no automatic search or save.');});
$('#solver-method').addEventListener('change',()=>{activeExample=null;$('#example-notice').hidden=true;$('#solver-compare').disabled=$('#solver-method').value!=='auto';if($('#solver-compare').disabled)$('#solver-compare').checked=false;if($('#solver-method').value==='auto')$('#solver-key').value='';status('Method changed. Press Solve to create a new result. Existing results retain their submitted settings.');});
window.addEventListener('browser-solver-restore',e=>{
  const attempt=e.detail;stop(null);input.value=attempt.text;$('#solver-method').value=attempt.options.method;$('#solver-key').value=attempt.options.key;$('#solver-depth').value=String(attempt.options.depth);$('#solver-compare').checked=attempt.options.compare;$('#solver-compare').disabled=attempt.options.method!=='auto';activeExample=attempt.options.exampleId;$('#example-notice').hidden=true;display(attempt,true);notifyAttempt(attempt);status('Local snapshot restored without a new search. Original settings are available in Advanced.');output.scrollIntoView({block:'start',behavior:'auto'});
});
const params=new URLSearchParams(location.search),method=params.get('cipher'),example=params.get('example');
if(method && Object.hasOwn(CIPHER_EXAMPLES,method)){$('#solver-method').value=method;$('#solver-compare').disabled=true;}
if(example && example===method && Object.hasOwn(CIPHER_EXAMPLES,example))loadExample(example);
const preset=document.body.dataset.preset;if(!example && SAMPLES[preset])input.placeholder=SAMPLES[preset];

// On-demand improvements popup: never interrupts the simple paste/solve flow.
const improvements=$('#web-improvements');
$('#show-web-improvements').addEventListener('click',()=>{if(improvements.open)return;if(typeof improvements.showModal==='function')improvements.showModal();else improvements.setAttribute('open','');});
$('#close-web-improvements').addEventListener('click',()=>{if(typeof improvements.close==='function')improvements.close();else improvements.removeAttribute('open');});
