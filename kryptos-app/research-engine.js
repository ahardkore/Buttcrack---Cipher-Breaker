/* Deterministic research operations. No solver confidence, network, or eval. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.KryptosResearch = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const STANDARD = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const KRYPTOS = 'KRYPTOSABCDEFGHIJLMNQUVWXZ';
  const K4 = 'OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR';
  const ANCHORS = [{text:'EAST',start:21},{text:'NORTHEAST',start:25},{text:'BERLIN',start:63},{text:'CLOCK',start:69}];
  const VERSION = 'kryptos-research/1';
  const SCHEMA = 'kryptos-research-report/v1';
  const NORMALIZATION = 'ASCII A–Z only, case folded; layout, punctuation, digits and non-ASCII letters removed. Positions are zero-based normalized letters. No silent truncation.';
  const METHODS = Object.freeze({
    vigenere: {name: 'Vigenère / additive Quagmire III', family: 'Polyalphabetic', convention: 'Both text and key index the selected alphabet; encryption C=P+K mod 26.'},
    beaufort: {name: 'Beaufort', family: 'Polyalphabetic', convention: 'Selected alphabet indices; C=K−P mod 26.'},
    variant_beaufort: {name: 'Variant Beaufort', family: 'Polyalphabetic', convention: 'Selected alphabet indices; C=P−K mod 26.'},
    caesar: {name: 'Caesar', family: 'Shift', convention: 'Shift 0–25 in the selected alphabet.'},
    columnar: {name: 'Complete columnar', family: 'Transposition', convention: 'Row-wise fill, columns read in stable ASCII keyword order. Complete rectangle only; no padding.'},
    spiral: {name: 'Top-right spiral', family: 'Transposition', convention: 'Row-wise rectangle; read from top-right down, left, up, right. Key is the width; no padding.'},
    hill3: {name: 'Hill 3×3', family: 'Matrix', convention: 'Nine key letters in selected-alphabet indices, row-major matrix times column-vector triples mod 26; invertible matrix required.'},
    substitution: {name: 'Alphabet substitution', family: 'Substitution', convention: 'Encryption maps standard A–Z to the selected alphabet; decryption reverses it.'},
    reverse: {name: 'Reverse', family: 'Transposition', convention: 'Reverse all normalized letters.'},
    manual: {name: 'Unimplemented / description only', family: 'Unclassified', convention: 'Not executable; stays a research hypothesis. Describe the method in the notes.'},
  });
  const mod = n => (n % 26 + 26) % 26;
  function text(value, name, limit) {
    if (typeof value !== 'string' || value.length > limit) throw new Error(`${name} must be text of at most ${limit} characters.`);
    return value;
  }
  function normalize(value) { return value.replace(/[^a-zA-Z]/g, '').toUpperCase(); }
  function alphabet(value) {
    const out = text(value, 'Alphabet', 26).toUpperCase();
    if (out.length !== 26 || !/^[A-Z]+$/.test(out) || new Set(out).size !== 26) throw new Error('Alphabet must contain each A–Z letter exactly once.');
    return out;
  }
  function keyedAlphabet(prefix) { return [...new Set(normalize(text(prefix, 'Alphabet prefix', 128)) + STANDARD)].join(''); }
  function integer(value, name, low, high) {
    if (!Number.isInteger(value) || value < low || value > high) throw new Error(`${name} must be an integer from ${low} to ${high}.`);
    return value;
  }
  function spec(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Hypothesis must be an object.');
    const original = text(value.original, 'Original ciphertext', 16000);
    const proposed = text(value.proposed ?? '', 'Proposed plaintext', 16000);
    if (!normalize(original).length || normalize(original).length > 8000 || normalize(proposed).length > 8000) throw new Error('Use 1–8,000 ciphertext letters and at most 8,000 proposed plaintext letters.');
    const a = alphabet(value.alphabet ?? STANDARD);
    if (!Array.isArray(value.steps) || value.steps.length > 32) throw new Error('Use at most 32 decryption steps.');
    const steps = value.steps.map(step => {
      if (!step || !Object.hasOwn(METHODS, step.method)) throw new Error('Unknown transformation method.');
      const key = text(step.key ?? '', 'Step key', 512);
      const phase = integer(step.phase ?? 0, 'Key phase', 0, 511);
      if (['reverse','substitution'].includes(step.method) && key) throw new Error('Reverse and alphabet substitution use no key; leave the key empty.');
      if (!['vigenere', 'beaufort', 'variant_beaufort'].includes(step.method) && phase) throw new Error('Key phase applies only to repeated-key polyalphabetic steps.');
      return {method: step.method, key, phase, alphabet: alphabet(step.alphabet || a)};
    });
    return {name: text(value.name ?? 'Untitled hypothesis', 'Name', 120), original, proposed, alphabet: a, steps,
      method_notes: text(value.method_notes ?? '', 'Method notes', 4000), evidence: text(value.evidence ?? '', 'Evidence', 4000),
      objections: text(value.objections ?? '', 'Reasons it might be wrong', 4000)};
  }
  function keyword(key, limit = 512) {
    if (!/^[A-Za-z]+$/.test(key) || key.length > limit) throw new Error(`Key must be 1–${limit} ASCII letters (without annotations or spaces).`);
    return key.toUpperCase();
  }
  function hillMatrix(key, a, decrypt) {
    if (keyword(key).length !== 9) throw new Error('Hill 3×3 requires nine key letters.');
    const m = [...key.toUpperCase()].map(c => a.indexOf(c));
    const det = m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6]);
    const inv = Array.from({length: 26}, (_, i) => i).find(i => mod(i*det) === 1);
    if (inv === undefined) throw new Error('Hill matrix is not invertible modulo 26.');
    if (!decrypt) return m;
    const out = [];
    for (let r=0; r<3; r++) for (let c=0; c<3; c++) {
      const rows = [0,1,2].filter(i => i !== c), cols = [0,1,2].filter(i => i !== r);
      const minor = m[rows[0]*3+cols[0]]*m[rows[1]*3+cols[1]]-m[rows[0]*3+cols[1]]*m[rows[1]*3+cols[0]];
      out.push(mod(inv * ((r+c)%2 ? -minor : minor)));
    }
    return out;
  }
  function transform(input, step, decrypt = true) {
    const a = alphabet(step.alphabet || STANDARD);
    const method = step.method, key = step.key || '', phase = step.phase || 0;
    if (method === 'manual') throw new Error('Description-only step has not been executed.');
    if (method === 'reverse') return [...input].reverse().join('');
    if (method === 'substitution') return [...input].map(c => decrypt ? STANDARD[a.indexOf(c)] : a[STANDARD.indexOf(c)]).join('');
    if (method === 'columnar' || method === 'spiral') {
      let order, width;
      if (method === 'columnar') {
        const k = keyword(key, 128); width = k.length;
        order = [...k].map((c,i) => i).sort((i,j) => k.charCodeAt(i)-k.charCodeAt(j) || i-j);
      } else {
        if (!/^[0-9]+$/.test(key)) throw new Error('Spiral key must be an integer width.');
        width = integer(Number(key), 'Spiral width', 1, 256);
      }
      if (input.length % width) throw new Error('Complete grid width must divide the text length; no padding is added.');
      const height = input.length / width;
      const positions = [];
      if (method === 'columnar') for (const c of order) for (let r=0; r<height; r++) positions.push(r*width+c);
      else {
        const moves = [[1,0],[0,-1],[-1,0],[0,1]], seen = new Set();
        let r=0, c=width-1, direction=0;
        for (let i=0; i<input.length; i++) {
          positions.push(r*width+c); seen.add(r*width+c);
          let nr=r+moves[direction][0], nc=c+moves[direction][1];
          if (nr<0 || nr>=height || nc<0 || nc>=width || seen.has(nr*width+nc)) {
            direction=(direction+1)%4; nr=r+moves[direction][0]; nc=c+moves[direction][1];
          }
          r=nr; c=nc;
        }
      }
      if (!decrypt) return positions.map(i => input[i]).join('');
      const result = Array(input.length);
      positions.forEach((position, i) => { result[position] = input[i]; });
      return result.join('');
    }
    if (method === 'hill3') {
      if (input.length % 3) throw new Error('Hill requires complete triples; no padding is added.');
      const m = hillMatrix(key, a, decrypt), result = [];
      for (let i=0; i<input.length; i+=3) for (let r=0; r<3; r++) result.push(a[mod(m[r*3]*a.indexOf(input[i])+m[r*3+1]*a.indexOf(input[i+1])+m[r*3+2]*a.indexOf(input[i+2]))]);
      return result.join('');
    }
    let shifts;
    if (method === 'caesar') {
      if (!/^[0-9]+$/.test(key)) throw new Error('Caesar key must be a decimal shift.');
      shifts = [integer(Number(key), 'Caesar shift', 0, 25)];
    } else if (['vigenere', 'beaufort', 'variant_beaufort'].includes(method)) shifts = [...keyword(key)].map(c => a.indexOf(c));
    else throw new Error('Unknown transformation method.');
    return [...input].map((c,i) => {
      const x=a.indexOf(c), k=shifts[(i+phase)%shifts.length];
      if (method === 'beaufort') return a[mod(k-x)];
      const sign = (method === 'variant_beaufort') === decrypt ? 1 : -1;
      return a[mod(x+sign*k)];
    }).join('');
  }
  function metrics(value) {
    const t=normalize(value), counts=Array(26).fill(0);
    for (const c of t) counts[STANDARD.indexOf(c)]++;
    return {letters:t.length, ic:t.length<2 ? null : counts.reduce((s,n)=>s+n*(n-1),0)/(t.length*(t.length-1)),
      entropy:t.length ? Math.max(0,-counts.filter(Boolean).reduce((s,n)=>s+(n/t.length)*Math.log2(n/t.length),0)) : null};
  }
  function agreement(a, b) {
    let matches=0, first=null;
    const positions=[];
    for (let i=0; i<Math.max(a.length,b.length); i++) {
      if (a[i] === b[i]) matches++;
      else { if(first === null) first=i; if(positions.length<20) positions.push(i); }
    }
    return {exact:a===b, matches, compared:Math.max(a.length,b.length), fraction:Math.max(a.length,b.length) ? matches/Math.max(a.length,b.length) : null,
      first_mismatch:first, mismatch_positions:positions, lengths_match:a.length===b.length};
  }
  function evaluate(value, catalog = []) {
    const h=spec(value), normalized=normalize(h.original), proposed=normalize(h.proposed);
    const record=catalog.find(r=>r.ciphertext===normalized);
    const source={label:record ? 'Verified corpus match' : 'No verified corpus match', id:record?.id || null,
      detail:record ? 'Normalized ciphertext equals a documented PK reference. This verifies source association, not this hypothesis or a new discovery.' : 'No exact normalized PK1–PK10 reference match. Similarity and length are not verification.',
      reference:record ? {title:record.title, ciphertext_sha256:record.ciphertext_sha256 || null, plaintext_sha256:record.plaintext_sha256, verification:record.verification} : null};
    const intermediates=[];
    let output=normalized, reconstructed=null, failure=null;
    try {
      for (let i=0; i<h.steps.length; i++) {
        const step=h.steps[i], before=output;
        output=transform(before,step,true);
        intermediates.push({index:i+1, ...step, family:METHODS[step.method].family, convention:METHODS[step.method].convention, input:before, output});
      }
      if (h.steps.length && proposed) {
        reconstructed=proposed;
        for (const step of [...h.steps].reverse()) reconstructed=transform(reconstructed,step,false);
      }
    } catch(error) { failure=error.message; }
    const reproduced=!failure && h.steps.length>0 && !!proposed && output===proposed && reconstructed===normalized;
    return {hypothesis:h, normalized, normalized_proposed:proposed, source,
      verification:{label:reproduced ? 'Reproduced decryption' : 'Research hypothesis', reproduced,
        independent_verification:false, intended_plaintext_proven:false,
        detail:reproduced ? 'The listed decryption regenerates the proposed plaintext and its inverse regenerates every normalized ciphertext letter. Reproducibility is not independent confirmation or proof of the intended message.' : failure || (!h.steps.length ? 'No executable method supplied.' : !proposed ? 'Supply a proposed plaintext to check reproduction.' : 'The proposed reading does not reproduce under the listed method/key.'),
        plaintext_agreement:h.steps.length && !failure && proposed ? agreement(output,proposed) : null,
        ciphertext_explanation:reconstructed !== null && !failure ? agreement(normalized,reconstructed) : null},
      output:failure ? null : h.steps.length ? output : null, reconstructed_ciphertext:failure ? null : reconstructed,
      failure, intermediates, ciphertext_metrics:metrics(normalized), plaintext_metrics:metrics(proposed),
      known_constraints:normalized===K4 ? ANCHORS.map(anchor=>({...anchor,proposed:proposed.slice(anchor.start,anchor.start+anchor.text.length),matches:proposed.slice(anchor.start,anchor.start+anchor.text.length)===anchor.text})) : [],
      constraint_note:normalized===K4 ? 'K4 clue positions recorded in this repository, converted to zero-based normalized letters. Constraint agreement is not verification of a full solution or fresh independent confirmation of the clues.' : null};
  }
  function templates(id, catalog) {
    const q=key=>({method:'vigenere',key}), t=key=>({method:'columnar',key});
    const pk4=catalog.find(r=>r.id==='PK4')?.plaintext;
    const forward={PK1:[q('PROVENANCE')],PK2:[t('MARGINS')],PK3:[q('ORDINATE'),q('PENTIMENTO')],
      PK4:[t('UNDERLAY'),q('OCHRE'),q('VERDIGRIS')],PK5:[t('TWOYEARS'),q(pk4)],
      PK6:[t('HANDIWORK'),t('SMITHWORK'),q('PORTAL')],PK7:[q('ANNEAL'),{method:'hill3',key:'ALCHEMIST'}],
      PK8:['METE','METER','METIER','MASTERY'].map(q),PK9:[q('CLEPSYDRA'),{method:'spiral',key:'12'},t('BEAMWORK')]};
    forward.PK10=[...forward.PK1,...forward.PK2,...forward.PK3,...forward.PK4,...forward.PK5,...forward.PK6,...forward.PK7,...forward.PK8,...forward.PK9];
    return (forward[id] || []).slice().reverse().map(step=>({...step,phase:0,alphabet:KRYPTOS}));
  }
  function report(value, catalog, created = new Date().toISOString()) {
    const result=evaluate(value,catalog);
    return {schema:SCHEMA, engine_version:VERSION, created_at:created, normalization:NORMALIZATION, decryption_order:'first-to-last; re-encryption uses inverses in reverse order',
      original_text:result.hypothesis.original, normalized_text:result.normalized, ...result,
      caveat:'Corpus association, reproducible arithmetic and independent verification are different claims. No language score or successful round-trip establishes intended plaintext.'};
  }
  function importReport(value) {
    if (!value || value.schema !== SCHEMA || !value.hypothesis) throw new Error('Expected a kryptos-research-report/v1 JSON report.');
    return spec(value.hypothesis); // Never trust imported statuses, traces, or source badges.
  }
  function sharedSequences(a,b) {
    function grams(t) {
      const out=new Map();
      for(let size=3;size<=5;size++) for(let i=0;i<=t.length-size;i++) {
        const gram=t.slice(i,i+size);
        if(!out.has(gram)) out.set(gram,[]);
        if(out.get(gram).length<20) out.get(gram).push(i);
      }
      return out;
    }
    const ga=grams(a), gb=grams(b), rows=[];
    for(const [pattern, positions] of ga) if(gb.has(pattern) && (positions.length>1 || gb.get(pattern).length>1)) rows.push({pattern,a_positions:positions,b_positions:gb.get(pattern),suggested_offset:gb.get(pattern)[0]-positions[0]});
    return rows.sort((x,y)=>y.pattern.length-x.pattern.length || y.a_positions.length-x.a_positions.length).slice(0,20);
  }
  function compare(a,b,offset=0,start=0) {
    integer(offset,'Comparison offset',-8000,8000);integer(start,'Comparison start',0,8000);
    const pa=a.normalized_proposed, pb=b.normalized_proposed, rows=[];
    for(let i=start;i<Math.min(start+120,Math.max(pa.length,pb.length-offset));i++) {
      const j=i+offset, left=pa[i] || '', right=j>=0 ? pb[j] || '' : '';
      rows.push({a_position:i,b_position:j,a:left,b:right,matches:!!left && !!right ? left===right : null});
    }
    return {same_ciphertext:a.normalized===b.normalized, offset, rows, shared_sequences:sharedSequences(pa,pb),
      detail:'Offsets align normalized plaintext positions only, not transposition routes. Shared sequences and matching letters can occur by chance; overlapping n-grams are not independent evidence.'};
  }
  return {STANDARD,KRYPTOS,VERSION,SCHEMA,NORMALIZATION,METHODS,normalize,alphabet,keyedAlphabet,spec,transform,metrics,evaluate,templates,report,importReport,compare};
});
