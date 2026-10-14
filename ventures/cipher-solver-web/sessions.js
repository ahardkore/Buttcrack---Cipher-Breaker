/* Explicit local history; never writes on typing, solving, restoration or load. */
(() => {
  'use strict';
  const S=InvestigationStore,$=id=>document.getElementById(id);
  const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  const action=(text,fn)=>{const b=make('button',text);b.type='button';b.className='ghost';b.addEventListener('click',()=>safe(fn));return b;};
  const message=text=>{$('history-status').textContent=text;};
  const safe=fn=>{try{fn();}catch(error){message(error.message);}};
  let saved={schema:S.SCHEMA,investigations:[]},current=null,blocked=false,rawBackup=null;
  const selected=()=>saved.investigations.find(i=>i.id===$('investigation-select').value);
  function persist(next){
    if(blocked)throw new Error('Stored history could not be validated. Export its raw backup, then explicitly delete/reset it before saving.');
    const value=S.book(next),serialized=JSON.stringify(value);
    if(serialized.length>2000000)throw new Error('Local history size limit reached. Export a backup and delete old investigations.');
    try{localStorage.setItem(S.KEY,serialized);}catch(_error){throw new Error('Device storage is unavailable or full. Existing history was not replaced; export a backup or copy your result.');}
    saved=value;rawBackup=null;render();
  }
  function render(){
    const previous=$('investigation-select').value;
    $('investigation-select').replaceChildren(make('option','New investigation'));$('investigation-select').firstChild.value='';
    for(const item of saved.investigations){const option=make('option',`${item.name} (${item.attempts.length} attempts)`);option.value=item.id;$('investigation-select').append(option);}
    if(saved.investigations.some(i=>i.id===previous))$('investigation-select').value=previous;
    renderAttempts();
  }
  function renderAttempts(){
    const item=selected();$('delete-investigation').disabled=!item;$('investigation-attempts').replaceChildren();$('attempt-a').replaceChildren();$('attempt-b').replaceChildren();$('attempt-comparison').replaceChildren();
    if(!item){$('investigation-attempts').append(make('p','Choose an investigation to inspect saved attempts.'));return;}
    item.attempts.forEach((attempt,index)=>{
      const row=make('div');row.className='saved-attempt';row.append(make('strong',`#${index+1} · ${attempt.options.method} · ${attempt.created_at}`),make('p',attempt.result ? `Reported cipher: ${attempt.result.cipher}; key: ${attempt.result.key}; score: ${attempt.result.confidence.toFixed(3)} (not a probability).` : 'No candidate returned.'));
      row.append(action('Restore text, settings & result',()=>{window.dispatchEvent(new CustomEvent('browser-solver-restore',{detail:attempt}));message('Saved snapshot restored. This is not a new search or independent verification.');}));row.append(action('Delete attempt',()=>{if(!confirm(`Delete saved attempt #${index+1}? The current result stays available.`))return;persist({schema:S.SCHEMA,investigations:saved.investigations.map(i=>i.id===item.id ? {...i,attempts:i.attempts.filter((_,j)=>j!==index)} : i)});message('Saved attempt deleted. The current result was not cleared.');}));$('investigation-attempts').append(row);
      for(const id of ['attempt-a','attempt-b']){const option=make('option',`#${index+1} · ${attempt.options.method} · ${attempt.created_at}`);option.value=String(index);$(id).append(option);}
    });
    if(item.attempts.length>1)$('attempt-b').value='1';
  }
  window.addEventListener('browser-solver-attempt',event=>{current=event.detail;$('save-attempt').disabled=!current;$('export-current-attempt').disabled=!current;});
  $('investigation-select').addEventListener('change',()=>{const item=selected();$('investigation-name').value=item ? item.name : '';renderAttempts();});
  $('save-attempt').addEventListener('click',()=>safe(()=>{
    if(!current)throw new Error('Solve or restore a result before saving.');
    const name=$('investigation-name').value.trim();if(!name || name.length>100)throw new Error('Enter an investigation name (1–100 characters).');
    const existing=selected(),snapshot=S.attempt(current);
    if(existing && existing.attempts.length>=10)throw new Error('This investigation has 10 attempts. Start another named investigation or export/delete old history.');
    if(!existing && saved.investigations.length>=12)throw new Error('At most 12 investigations; export/delete an old one first.');
    const item={id:existing?.id || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),name,attempts:[...(existing?.attempts || []),snapshot]};
    persist({schema:S.SCHEMA,investigations:existing ? saved.investigations.map(i=>i.id===item.id ? item : i) : [...saved.investigations,item]});
    $('investigation-select').value=item.id;renderAttempts();message('Saved explicitly on this device. No data was uploaded. Each result retains its submitted text/settings.');
  }));
  $('delete-investigation').addEventListener('click',()=>safe(()=>{const item=selected();if(!item || !confirm(`Delete “${item.name}” and its saved attempts?`))return;persist({schema:S.SCHEMA,investigations:saved.investigations.filter(i=>i.id!==item.id)});message('Investigation deleted. Current input/result was not cleared.');}));
  $('clear-investigations').addEventListener('click',()=>safe(()=>{if(!confirm('Delete all saved investigations on this device? Export a backup first.'))return;localStorage.removeItem(S.KEY);saved={schema:S.SCHEMA,investigations:[]};blocked=false;rawBackup=null;render();message('Saved history deleted. Current input/result remains available.');}));
  function download(name,value){const url=URL.createObjectURL(new Blob([typeof value==='string' ? value : JSON.stringify(value,null,2)],{type:'application/json'})),a=make('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('export-investigations').addEventListener('click',()=>safe(()=>{download('cipher-investigations.json',rawBackup || saved);message('Exported device-local backup. It includes plaintext, ciphertext and keys.');}));
  $('export-current-attempt').addEventListener('click',()=>safe(()=>{if(!current)throw new Error('No current attempt.');download('cipher-attempt.json',{schema:'browser-attempt/v1',attempt:S.attempt(current)});message('Current submitted result exported without saving it to browser storage.');}));
  $('import-investigations').addEventListener('change',async()=>{
    const file=$('import-investigations').files[0];if(!file)return;
    try{if(file.size>4*1024*1024)throw new Error('Import limit is 4 MB.');const next=S.book(JSON.parse(await file.text()));if(!confirm('Replace this device’s saved investigations with this backup? Export a backup first.'))return;
      const oldBlocked=blocked;blocked=false;try{persist(next);}catch(error){blocked=oldBlocked;throw error;}message('Local backup imported. Stored proof flags were discarded; restored snapshots are not new verification.');
    }catch(error){message(`Import rejected: ${error.message} Existing history was not replaced.`);}finally{$('import-investigations').value='';}
  });
  $('compare-attempts').addEventListener('click',()=>safe(()=>{
    const item=selected(),a=item?.attempts[Number($('attempt-a').value)],b=item?.attempts[Number($('attempt-b').value)];if(!a || !b)throw new Error('Choose saved attempts to compare.');
    const same=a.text===b.text;$('attempt-comparison').replaceChildren(make('p',same ? 'Same original input. Scores are ranking heuristics, not probabilities or independent verification.' : 'Different original inputs: score comparisons are not directly meaningful.'));
    const columns=make('div');columns.className='attempt-columns';
    for(const [label,attempt] of [['A',a],['B',b]]){const card=make('section');card.append(make('h4',`Attempt ${label}`),make('p',`Requested: ${attempt.options.method}; supplied key: ${attempt.options.key || 'none'}; depth: ${attempt.options.depth}.`),make('p',attempt.result ? `Reported: ${attempt.result.cipher}; key ${attempt.result.key}; language score ${attempt.result.confidence.toFixed(3)} (not proof).` : 'No candidate returned.'),make('pre',attempt.result?.plaintext || 'No plaintext candidate.'));columns.append(card);}$('attempt-comparison').append(columns);
  }));
  let warning=null;
  try{const raw=localStorage.getItem(S.KEY);if(raw){rawBackup=raw;if(raw.length>2000000)throw new Error('Stored history exceeds the size limit.');saved=S.book(JSON.parse(raw));rawBackup=null;}}
  catch(error){blocked=true;warning=`History was not loaded: ${error.message} Nothing was overwritten. Export the raw backup before resetting.`;}
  render();if(warning)message(warning);
})();
