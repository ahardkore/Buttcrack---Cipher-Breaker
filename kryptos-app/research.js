/* Research notebook UI. Persistence is explicit; imported evidence is untrusted. */
(() => {
  'use strict';
  const R=KryptosResearch, catalog=PARADIGM_KRYPTOS;
  const STORAGE='kryptos.research.notebook.v1', NOTEBOOK='kryptos-research-notebook/v1';
  const $=id=>document.getElementById(id);
  const make=(tag, value, cls)=>{const n=document.createElement(tag);if(value!==undefined)n.textContent=value;if(cls)n.className=cls;return n;};
  const button=(label, action)=>{const n=make('button',label);n.type='button';n.addEventListener('click',action);return n;};
  let saved=[], evaluated=new Map(), loadedId=null, storageBlocked=false, rawBackup=null, lastSource='custom';
  const status=message=>{$('research-status').textContent=message;};
  const safely=action=>{try{return action();}catch(error){status(error.message);return null;}};
  const id=()=>window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  function blankResults() {
    $('research-verdict').replaceChildren();$('research-output').textContent='No current method executed.';
    $('research-reconstructed').textContent='Not checked.';
    $('research-intermediates').replaceChildren();
    for(const field of ['research-agreement','research-reference-agreement','research-constraints']) $(field).textContent='';
    $('research-verification-detail').textContent='Draft changed. Run the method again; previous evidence no longer applies.';
  }
  function dirty() {status('Unsaved draft changes. Run again to recompute evidence, and Save or Update explicitly to persist.');blankResults();sourceView();}
  function sourceView() {
    const raw=$('research-original').value, normalized=R.normalize(raw), record=catalog.find(r=>r.ciphertext===normalized);
    $('research-normalized').textContent=normalized;
    $('research-normalization').textContent=R.NORMALIZATION;
    const m=R.metrics(normalized);
    $('research-source-metrics').textContent=`${m.letters} normalized letters · IC ${m.ic===null ? 'not measurable' : m.ic.toFixed(5)} · letter entropy ${m.entropy===null ? 'not measurable' : m.entropy.toFixed(4)} bits / letter.`;
    $('research-corpus').replaceChildren(make('span',record ? `Verified corpus match · ${record.id}` : 'No verified corpus match',`research-badge ${record ? 'corpus' : 'hypothesis'}`));
    $('research-source-note').textContent=record ? 'Exact normalized PK reference association only. A proposed method/reading is checked separately; this is not a newly solved cipher.' : 'Custom / CIA research input is not an exact PK1–PK10 corpus match. That does not make it invalid, nor does it validate any proposed reading.';
    $('research-alphabet-view').replaceChildren();
    safely(()=>{
      [...R.alphabet($('research-alphabet').value)].forEach((letter,index)=>{
        const cell=make('span');cell.append(make('strong',letter),make('small',String(index)));$('research-alphabet-view').append(cell);
      });
    });
  }
  function stepRow(step={method:'vigenere',key:'',phase:0}) {
    const row=make('div',undefined,'research-step'), fields=make('div',undefined,'research-step-fields');
    const method=make('select');method.dataset.field='method';
    for(const [value,info] of Object.entries(R.METHODS)){const option=make('option',info.name);option.value=value;method.append(option);}
    method.value=step.method;
    const key=make('input');key.dataset.field='key';key.value=step.key || '';key.maxLength=512;key.spellcheck=false;
    const phase=make('input');phase.dataset.field='phase';phase.type='number';phase.min='0';phase.max='511';phase.value=String(step.phase || 0);
    for(const [title,input] of [['Transformation',method],['Key / width',key],['Key phase',phase]]){const label=make('label',title);label.append(input);fields.append(label);}
    const override=make('input');override.dataset.field='alphabet';override.maxLength=26;override.spellcheck=false;
    override.value=step.alphabet && step.alphabet!==$('research-alphabet').value ? step.alphabet : '';
    override.placeholder='Blank uses the current default alphabet';
    const overrideLabel=make('label','Optional per-step alphabet');overrideLabel.append(override);
    const hint=make('p',undefined,'research-hint');
    function describe(){hint.textContent=R.METHODS[method.value].convention;phase.disabled=!['vigenere','beaufort','variant_beaufort'].includes(method.value);if(phase.disabled)phase.value='0';key.disabled=['reverse','substitution'].includes(method.value);if(key.disabled)key.value='';}
    describe();method.addEventListener('change',()=>{describe();dirty();});
    const actions=make('div',undefined,'research-actions');
    actions.append(button('Move up',()=>{if(row.previousElementSibling){row.parentNode.insertBefore(row,row.previousElementSibling);dirty();}}),button('Move down',()=>{if(row.nextElementSibling){row.parentNode.insertBefore(row.nextElementSibling,row);dirty();}}),button('Remove step',()=>{row.remove();dirty();}));
    row.append(fields,overrideLabel,hint,actions);
    row.addEventListener('input',dirty);
    return row;
  }
  function draft() {
    return R.spec({name:$('research-name').value,original:$('research-original').value,proposed:$('research-proposed').value,alphabet:$('research-alphabet').value,
      steps:[...$('research-steps').children].map(row=>({method:row.querySelector('[data-field="method"]').value,key:row.querySelector('[data-field="key"]').value,
        phase:Number(row.querySelector('[data-field="phase"]').value),alphabet:row.querySelector('[data-field="alphabet"]').value || $('research-alphabet').value})),
      method_notes:$('research-method-notes').value,evidence:$('research-evidence').value,objections:$('research-objections').value});
  }
  function loadDraft(h, source='custom', savedId=null) {
    for(const [field,value] of Object.entries({name:h.name,original:h.original,proposed:h.proposed,alphabet:h.alphabet,'method-notes':h.method_notes,evidence:h.evidence,objections:h.objections})) $(`research-${field}`).value=value;
    $('research-source').value=source;lastSource=source;
    $('research-steps').replaceChildren(...h.steps.map(stepRow));
    loadedId=savedId;$('research-update').disabled=!loadedId;
    blankResults();sourceView();
  }
  function loadReference(source) {
    if(source==='custom') {loadDraft(R.spec({name:'Custom hypothesis',original:'PASTEYOURCIPHERTEXTHERE',proposed:'',alphabet:R.KRYPTOS,steps:[]}));$('research-original').value='';dirty();status('Custom draft ready. Existing saved hypotheses are unchanged.');return;}
    const reference=CIPHERS_DATA[source];
    if(!reference || reference.reference_complete===false) throw new Error('This is an incomplete legacy excerpt; use an authoritative full transcription as custom input.');
    const pk=catalog.find(r=>r.id===source);
    const steps=pk ? R.templates(source,catalog) : source==='K1' ? [{method:'vigenere',key:'PALIMPSEST',phase:0,alphabet:R.KRYPTOS}] : [];
    loadDraft(R.spec({name:`${source} · documented method`,original:reference.ciphertext,proposed:reference.plaintext || '',alphabet:R.KRYPTOS,steps,
      method_notes:pk ? `${pk.mechanism}. Source: ${reference.challengeUrl}. PK templates transcribed from this repository's independent construction verifiers; rerun to check all letters.` : reference.notes,
      evidence:pk ? 'Documented reference plaintext and construction; exact reproduction must still be checked.' : '',objections:'A source match or reproducible round trip is not proof of a new discovery or independent confirmation of a research proposal.'}),source);
    status(`${source} loaded as an unsaved draft. Run its documented method to check reproduction.`);
  }
  function fraction(check){return check ? `${check.matches} / ${check.compared} positions (${check.fraction===null ? 'not measurable' : (check.fraction*100).toFixed(2)+'%'})${check.first_mismatch===null ? '' : `; first mismatch ${check.first_mismatch}`}` : 'not checked';}
  function renderResult(result) {
    $('research-verdict').replaceChildren(make('span',result.verification.label,`research-badge ${result.verification.reproduced ? 'reproduced' : 'hypothesis'}`));
    $('research-verification-detail').textContent=result.verification.detail;
    $('research-agreement').textContent=`Generated vs proposed plaintext: ${fraction(result.verification.plaintext_agreement)}. Re-encrypted proposal vs ciphertext: ${fraction(result.verification.ciphertext_explanation)}. These are arithmetic agreements, not probabilities.`;
    const reference=catalog.find(r=>r.id===result.source.id);
    $('research-reference-agreement').textContent=reference ? `Proposed plaintext ${result.normalized_proposed===reference.plaintext ? 'equals' : 'does not equal'} the ${reference.id} catalog plaintext. Source recognition alone does not validate a different candidate.` : '';
    $('research-constraints').textContent=result.known_constraints.length ? `${result.constraint_note} ${result.known_constraints.map(item=>`${item.text} at ${item.start}–${item.start+item.text.length-1}: ${item.matches ? 'agrees' : 'does not agree / missing'}`).join('; ')}` : '';
    $('research-output').textContent=result.output ?? (result.failure ? `Not fully executed: ${result.failure}` : 'No executable method supplied.');
    $('research-reconstructed').textContent=result.reconstructed_ciphertext ?? 'Not checked.';
    $('research-intermediates').replaceChildren();
    for(const step of result.intermediates) {
      const section=make('details');section.append(make('summary',`${step.index}. ${R.METHODS[step.method].name} · ${step.family}`),make('p',`Key: ${step.key || '—'}; phase: ${step.phase}; alphabet: ${step.alphabet}`, 'research-hint'),make('p',step.convention,'research-hint'),make('h4','Input'),make('pre',step.input),make('h4','Output'),make('pre',step.output));$('research-intermediates').append(section);
    }
  }
  function run() {
    let value=draft(), result=R.evaluate(value,catalog);
    if(!value.proposed && result.output!==null) {
      $('research-proposed').value=result.output;
      result=R.evaluate(draft(),catalog);
    }
    renderResult(result);status('Method evaluated on all normalized letters. Derived statuses do not establish intended plaintext.');return result;
  }
  function notebook(entries=saved){return {schema:NOTEBOOK,engine_version:R.VERSION,entries};}
  function validateNotebook(value) {
    if(!value || value.schema!==NOTEBOOK || !Array.isArray(value.entries) || value.entries.length>24) throw new Error('Expected a v1 research notebook with at most 24 hypotheses.');
    const ids=new Set();
    return value.entries.map(entry=>{
      if(!entry || typeof entry.id!=='string' || entry.id.length>100 || !entry.id || ids.has(entry.id)) throw new Error('Notebook IDs must be nonempty and unique.');
      ids.add(entry.id);
      const now=new Date().toISOString();
      return {id:entry.id,hypothesis:R.spec(entry.hypothesis),created_at:typeof entry.created_at==='string' && entry.created_at.length<=80 ? entry.created_at : now,updated_at:typeof entry.updated_at==='string' && entry.updated_at.length<=80 ? entry.updated_at : now};
    });
  }
  function persist(next) {
    if(storageBlocked) throw new Error('Stored notebook could not be validated. Export a backup, then explicitly delete/reset or replace it before saving.');
    try {localStorage.setItem(STORAGE,JSON.stringify(notebook(next)));}
    catch(_error){throw new Error('Browser storage is unavailable or full. No saved data was replaced; export the current report as a backup.');}
    saved=next;rawBackup=null;renderSaved();
  }
  function save(update=false) {
    const h=draft();R.evaluate(h,catalog);
    if(!update && saved.length>=24) throw new Error('Notebook limit is 24 hypotheses. Export a backup or delete an entry before adding another.');
    const now=new Date().toISOString(), existing=update ? saved.find(entry=>entry.id===loadedId) : null;
    if(update && !existing) throw new Error('Load a saved hypothesis before updating it.');
    const entry={id:existing?.id || id(),hypothesis:h,created_at:existing?.created_at || now,updated_at:now};
    persist(update ? saved.map(item=>item.id===entry.id ? entry : item) : [...saved,entry]);
    loadedId=entry.id;$('research-update').disabled=false;
    renderResult(R.evaluate(h,catalog));status('Hypothesis inputs saved in this browser. Verification is recomputed, never stored as a trusted claim.');
  }
  function renderSaved() {
    evaluated=new Map();$('research-saved').replaceChildren();
    const previousA=$('research-compare-a').value, previousB=$('research-compare-b').value;
    for(const field of ['research-compare-a','research-compare-b']) $(field).replaceChildren();
    for(const entry of saved) {
      const result=R.evaluate(entry.hypothesis,catalog);evaluated.set(entry.id,result);
      const row=make('tr'), title=make('td');title.append(make('strong',entry.hypothesis.name),make('p',[...new Set(entry.hypothesis.steps.map(step=>R.METHODS[step.method].family))].join(' → ') || 'Description only','research-hint'));
      const actions=make('td');actions.append(button('Load',()=>{loadDraft(entry.hypothesis,'custom',entry.id);renderResult(result);status('Saved inputs loaded. Editing invalidates the displayed method result.');}),button('Export',()=>safely(()=>download(`${entry.id}.json`,R.report(entry.hypothesis,catalog)))),button('Delete',()=>safely(()=>{
        if(!window.confirm(`Delete saved hypothesis “${entry.hypothesis.name}”?`))return;
        persist(saved.filter(item=>item.id!==entry.id));
        if(loadedId===entry.id){loadedId=null;$('research-update').disabled=true;}status('Saved hypothesis deleted.');
      })));
      row.append(title,make('td',result.source.id ? `Verified corpus match · ${result.source.id}` : 'No verified corpus match'),make('td',result.verification.label),make('td',fraction(result.verification.ciphertext_explanation)),actions);$('research-saved').append(row);
      for(const field of ['research-compare-a','research-compare-b']){const option=make('option',entry.hypothesis.name);option.value=entry.id;$(field).append(option);}
    }
    if(!saved.length){const row=make('tr'), cell=make('td','No hypotheses saved. Drafts are not persisted automatically.');cell.colSpan=5;row.append(cell);$('research-saved').append(row);}
    if(evaluated.has(previousA))$('research-compare-a').value=previousA;
    if(evaluated.has(previousB) && (previousB!==$('research-compare-a').value || saved.length<2))$('research-compare-b').value=previousB;
    else if(saved.length>1)$('research-compare-b').value=saved.find(entry=>entry.id!==$('research-compare-a').value).id;
    clearComparison();
  }
  function clearComparison(){for(const field of ['research-compare-summary','research-comparison','research-shared'])$(field).replaceChildren();$('research-compare-note').textContent='Choose saved hypotheses to compare families, source, arithmetic explanation and repeated sequences.';}
  function compare() {
    const a=evaluated.get($('research-compare-a').value),b=evaluated.get($('research-compare-b').value);
    if(!a || !b)throw new Error('Save at least one hypothesis, then choose A and B (two distinct hypotheses are recommended).');
    const offset=Number($('research-compare-offset').value),start=Number($('research-compare-start').value), data=R.compare(a,b,offset,start);
    $('research-compare-note').textContent=(data.same_ciphertext ? 'Same normalized ciphertext. ' : 'Different normalized ciphertexts: do not directly compare explanation percentages. ')+data.detail;
    $('research-compare-summary').replaceChildren();
    for(const [label,result] of [['A',a],['B',b]]){
      const card=make('div');card.append(make('h4',`${label} · ${result.hypothesis.name}`),make('p',`${result.verification.label}; ${result.source.label}${result.source.id ? ' · '+result.source.id : ''}`,'research-hint'),make('p',`Explained ciphertext: ${fraction(result.verification.ciphertext_explanation)}`,'research-hint'),make('p',`Proposed plaintext: ${result.plaintext_metrics.letters} letters; IC ${result.plaintext_metrics.ic?.toFixed(5) ?? 'not measurable'}; entropy ${result.plaintext_metrics.entropy?.toFixed(3) ?? 'not measurable'} bits / letter.`,'research-hint'),make('p',result.known_constraints.length ? `Repository-listed K4 clue constraints: ${result.known_constraints.filter(item=>item.matches).length} / ${result.known_constraints.length} agree (not proof).` : 'No built-in clue constraints for this source.','research-hint'),make('h4','Evidence'),make('p',result.hypothesis.evidence || 'No supporting evidence recorded.'),make('h4','Reasons it might be wrong'),make('p',result.hypothesis.objections || 'No objections recorded; this does not imply none exist.'));$('research-compare-summary').append(card);
    }
    $('research-comparison').replaceChildren();
    for(let offset=0;offset<data.rows.length;offset+=30){const block=data.rows.slice(offset,offset+30),row=make('tr');row.append(make('td',`A ${block[0].a_position}–${block.at(-1).a_position} / B ${block[0].b_position}–${block.at(-1).b_position}`));for(const field of ['a','b']){const cell=make('td',undefined,'research-align');for(const item of block){const char=make('span',item[field] || '·',item.matches===false ? 'research-disagree' : '');char.title=`A ${item.a_position}, B ${item.b_position}: ${item.matches===null ? 'missing letter' : item.matches ? 'same letter, not proof' : 'different letters'}`;cell.append(char);}row.append(cell);}$('research-comparison').append(row);}
    $('research-shared').replaceChildren();
    for(const item of data.shared_sequences){const row=make('tr'),action=make('td');action.append(button(`Align offset ${item.suggested_offset}`,()=>safely(()=>{$('research-compare-offset').value=String(item.suggested_offset);$('research-compare-start').value=String(item.a_positions[0]);compare();})));row.append(make('td',item.pattern),make('td',item.a_positions.join(', ')),make('td',item.b_positions.join(', ')),action);$('research-shared').append(row);}
    if(!data.shared_sequences.length){const row=make('tr'),cell=make('td','No shared repeated 3–5-letter sequences in these readings.');cell.colSpan=4;row.append(cell);$('research-shared').append(row);}
  }
  function download(name,value) {
    const content=typeof value==='string' ? value : JSON.stringify(value,null,2);
    const url=URL.createObjectURL(new Blob([content],{type:'application/json'})),link=make('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function readFile(input, apply) {
    const file=input.files[0];if(!file)return;
    try {if(file.size>4*1024*1024)throw new Error('Import limit is 4 MB.');const value=JSON.parse(await file.text());apply(value);}
    catch(error){status(`Import rejected: ${error.message}. Existing notebook and draft are unchanged.`);}
    finally{input.value='';}
  }
  document.addEventListener('DOMContentLoaded',()=>{
    for(const [source,reference] of Object.entries(CIPHERS_DATA)){const option=make('option',`${reference.title}${reference.reference_complete===false ? ' (incomplete excerpt — unavailable)' : ''}`);option.value=source;option.disabled=reference.reference_complete===false;$('research-source').append(option);}
    $('research-source').addEventListener('change',()=>{const next=$('research-source').value;if(!window.confirm('Replace the current unsaved draft with this source? Saved hypotheses will remain unchanged.')){$('research-source').value=lastSource;return;}if(safely(()=>loadReference(next))===null)$('research-source').value=lastSource;});
    $('research-original').addEventListener('input',()=>{$('research-source').value='custom';lastSource='custom';dirty();});
    for(const field of ['research-proposed','research-name','research-alphabet','research-method-notes','research-evidence','research-objections'])$(field).addEventListener('input',dirty);
    $('research-build-alphabet').addEventListener('click',()=>safely(()=>{$('research-alphabet').value=R.keyedAlphabet($('research-prefix').value);dirty();}));
    $('research-standard-alphabet').addEventListener('click',()=>{$('research-alphabet').value=R.STANDARD;dirty();});
    $('research-add-step').addEventListener('click',()=>safely(()=>{if($('research-steps').children.length>=32)throw new Error('Maximum 32 transformations.');$('research-steps').append(stepRow());dirty();}));
    $('research-run').addEventListener('click',()=>safely(run));$('research-save').addEventListener('click',()=>safely(()=>save()));$('research-update').addEventListener('click',()=>safely(()=>save(true)));
    $('research-export').addEventListener('click',()=>safely(()=>{const report=R.report(draft(),catalog);renderResult(report);download('kryptos-research-report.json',report);status('Exported current inputs and recomputed evidence, including keys and plaintext.');}));
    $('research-import').addEventListener('change',()=>readFile($('research-import'),value=>{const h=R.importReport(value);if(!window.confirm('Replace the unsaved draft with this report? Imported verification claims will be discarded.'))return;loadDraft(h);renderResult(R.evaluate(h,catalog));status('Report imported; all statuses and intermediate outputs recomputed locally.');}));
    $('research-export-notebook').addEventListener('click',()=>safely(()=>download('kryptos-research-notebook.json',rawBackup || notebook())));
    $('research-import-notebook').addEventListener('change',()=>readFile($('research-import-notebook'),value=>{const next=validateNotebook(value);if(!window.confirm('Replace this browser’s saved notebook with this backup? Export a backup first.'))return;const blocked=storageBlocked;storageBlocked=false;try{persist(next);}catch(error){storageBlocked=blocked;throw error;}loadedId=null;$('research-update').disabled=true;status('Notebook replaced; statuses recomputed from inputs, not imported claims.');}));
    $('research-clear-saved').addEventListener('click',()=>safely(()=>{if(!window.confirm('Delete all saved research hypotheses in this browser? This cannot be undone without an exported backup.'))return;localStorage.removeItem(STORAGE);storageBlocked=false;rawBackup=null;saved=[];loadedId=null;$('research-update').disabled=true;renderSaved();status('Saved notebook deleted. The current unsaved draft remains available to export.');}));
    $('research-compare').addEventListener('click',()=>safely(compare));
    for(const field of ['research-compare-a','research-compare-b','research-compare-offset','research-compare-start'])$(field).addEventListener('change',clearComparison);
    $('research-open-reference').addEventListener('click',()=>safely(()=>{if(!window.confirm('Replace the unsaved research draft with this reference?'))return;loadReference(currentCipherId);document.querySelector('[data-target="research-mode"]').click();}));
    const updates=$('research-update-dialog'), newsKey='kryptos.research.notes.version';
    const showUpdates=()=>{if(updates.open)return;if(typeof updates.showModal==='function')updates.showModal();else updates.setAttribute('open','');};
    const acknowledgeUpdates=()=>{try{sessionStorage.setItem(newsKey,R.VERSION);}catch(_error){/* Version-only preference is optional. */}};
    $('research-whats-new').addEventListener('click',showUpdates);
    updates.addEventListener('close',acknowledgeUpdates);
    $('research-close-updates').addEventListener('click',()=>{if(typeof updates.close==='function')updates.close();else{updates.removeAttribute('open');acknowledgeUpdates();}});
    let warning=null;
    try {const raw=localStorage.getItem(STORAGE);if(raw){rawBackup=raw;saved=validateNotebook(JSON.parse(raw));rawBackup=null;}}
    catch(error){storageBlocked=true;warning=`Saved notebook was not loaded: ${error.message}. Export its raw backup before deleting/resetting. Nothing has been overwritten.`;}
    renderSaved();loadReference('PK1');if(warning)status(warning);
    try{if(sessionStorage.getItem(newsKey)!==R.VERSION)showUpdates();}catch(_error){showUpdates();}
  });
})();
