/* UI glue. Everything heavy happens in worker.js; this file only renders. */
'use strict';

const $ = sel => document.querySelector(sel);
const input = $('#ciphertext');
const output = $('#output');
const goBtn = $('#go');

let worker = null;

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

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function renderIdentify(info, text) {
  const guesses = info.guesses.slice(0, 3)
    .map(g => `${esc(g[0])} (${Math.round(g[1] * 100)}%)`).join(' · ');
  return `<div class="card">
    <div class="stats">
      <span><b>${text.length}</b> characters</span>
      <span>IC <b>${info.ic.toFixed(4)}</b></span>
      <span>entropy <b>${info.entropy.toFixed(2)}</b></span>
    </div>
    <div class="stats" style="margin-top:10px">
      <span>identified <b>${guesses}</b></span>
    </div>
  </div>`;
}

function listItems(items) {
  return items.map(item => `<li>${esc(typeof item === 'string' ? item : item.text)}</li>`).join('');
}

function fallbackDiagnostic(result) {
  const score = result && Number.isFinite(result.confidence) ? result.confidence : 0;
  return {
    candidateStatus: result && score >= 0.70 ? 'high-confidence' : result && score >= 0.45 ? 'tentative' : 'no-high-confidence',
    reasons: [{
      text: result
        ? `The best attempted candidate scored ${score.toFixed(2)} on the English-likeness scale, below the 0.45 display threshold.`
        : 'No implemented attack produced a non-empty candidate to rank.',
    }],
    nextSteps: ['Check the cipher type, key material, transcription, and whether the plaintext is English.'],
    attempted: [],
  };
}

function renderDiagnostic(diagnostic) {
  const reasons = diagnostic.reasons && diagnostic.reasons.length
    ? `<ul>${listItems(diagnostic.reasons)}</ul>`
    : '';
  const steps = diagnostic.nextSteps && diagnostic.nextSteps.length
    ? `<h4>Useful next checks</h4><ul>${listItems(diagnostic.nextSteps)}</ul>`
    : '';
  const attempted = diagnostic.attempted && diagnostic.attempted.length
    ? `<details class="diagnostic-coverage"><summary>What this browser considered</summary><ul>${listItems(diagnostic.attempted)}</ul></details>`
    : '';

  return `<section class="card diagnostic-card" aria-label="Why there is no high-confidence answer">
    <div class="solved-head">
      <span class="label low">NO HIGH-CONFIDENCE ANSWER</span>
    </div>
    <p class="diagnostic-intro">These are evidence-based observations about this input and this browser solver’s coverage. They do not prove one exact reason the message resisted decryption.</p>
    ${reasons}
    ${steps}
    ${attempted}
  </section>`;
}

function renderUnverifiedCandidate(result, elapsed) {
  if (!result) return '';
  const pct = Math.max(0, Math.min(100, Math.round(result.confidence * 100)));
  const chain = result.chain && result.chain.length
    ? `<tr><td>decode chain</td><td><code>${esc(result.chain.join(' → '))} → ${esc(result.cipher)}</code></td></tr>`
    : '';
  return `<details class="card unverified-candidate">
    <summary>Inspect the best statistical candidate — not a decryption</summary>
    <p class="candidate-note">It scored ${result.confidence.toFixed(2)} for English-likeness after ${elapsed.toFixed(2)}s, below this page’s threshold. Treat it as a lead to test, not recovered plaintext.</p>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <p class="result-kicker">UNVERIFIED CANDIDATE TEXT</p>
    <div class="plaintext">${esc(result.plaintext)}</div>
    <table class="evidence">
      <tr><td>cipher tried</td><td><code>${esc(result.cipher)}</code></td></tr>
      <tr><td>key tried</td><td><code>${esc(result.key)}</code></td></tr>
      ${chain}
      <tr><td>method</td><td>${esc(result.method)}</td></tr>
    </table>
    <div class="controls" style="margin-top:14px">
      <button class="ghost" id="copy">Copy candidate text</button>
    </div>
  </details>`;
}

function renderResult(result, diagnostic, elapsed) {
  const report = diagnostic || fallbackDiagnostic(result);
  if (!result || report.candidateStatus === 'no-high-confidence') {
    return renderDiagnostic(report) + renderUnverifiedCandidate(result, elapsed);
  }

  const verified = Boolean(result.verified && result.paradigm);
  const high = verified || report.candidateStatus === 'high-confidence';
  const pct = Math.max(0, Math.min(100, Math.round(result.confidence * 100)));
  const label = verified ? 'VERIFIED CANONICAL MATCH' : (high ? 'HIGH-CONFIDENCE CANDIDATE' : 'TENTATIVE CANDIDATE');
  const chain = result.chain && result.chain.length
    ? `<tr><td>decode chain</td><td><code>${esc(result.chain.join(' → '))} → ${esc(result.cipher)}</code></td></tr>`
    : '';
  const verification = verified ? `
      <tr><td>corpus record</td><td><code>${esc(result.paradigm.id)} — ${esc(result.paradigm.title)}</code></td></tr>
      <tr><td>construction</td><td>${esc(result.paradigm.mechanism)}</td></tr>
      <tr><td>plaintext SHA-256</td><td><code>${esc(result.paradigm.plaintext_sha256)}</code></td></tr>
      <tr><td>verification</td><td>${esc(result.verification || result.paradigm.verification)}</td></tr>` : '';
  const note = verified
    ? 'This result is an exact normalized equality with a recovered PK1–PK10 canonical ciphertext and carries its stored plaintext digest. It is not a statistical identification of similar text.'
    : 'This score ranks output under an English language model; it is evidence, not independent proof. Verify the full method, key, and source context before relying on it.';
  return `<div class="card">
    <div class="solved-head">
      <span class="label ${high ? '' : 'low'}">${label}</span>
      <span class="meta">${verified ? `Exact local corpus lookup · ${elapsed.toFixed(2)}s` : `English-likeness score ${result.confidence.toFixed(2)} · ${elapsed.toFixed(2)}s`}</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <p class="candidate-note">${esc(note)}</p>
    <p class="result-kicker">${verified ? 'VERIFIED PLAINTEXT' : 'CANDIDATE PLAINTEXT'}</p>
    <div class="plaintext">${esc(result.plaintext)}</div>
    <table class="evidence">
      <tr><td>cipher</td><td><code>${esc(result.cipher)}</code></td></tr>
      <tr><td>key</td><td><code>${esc(result.key)}</code></td></tr>
      ${result.alphabet ? `<tr><td>alphabet</td><td><code>${esc(result.alphabet)}</code></td></tr>` : ''}
      ${chain}
      <tr><td>method</td><td>${esc(result.method)}</td></tr>${verification}
    </table>
    <div class="controls" style="margin-top:14px">
      <button class="ghost" id="copy">Copy candidate text</button>
    </div>
  </div>`;
}

function crack() {
  const text = input.value.trim();
  if (!text) {
    output.innerHTML = '<div class="card"><p style="margin:0;color:var(--muted)">Paste some ciphertext first.</p></div>';
    return;
  }
  if (text.length > 20000) {
    output.innerHTML = '<div class="card"><p style="margin:0;color:var(--warn)">That is over 20,000 characters — trim it down so your browser stays responsive.</p></div>';
    return;
  }

  if (worker) worker.terminate();
  worker = new Worker('worker.js');

  goBtn.disabled = true;
  output.innerHTML = '<div class="card"><span class="spinner"></span>Analysing…</div>';
  let head = '';

  worker.onmessage = e => {
    const m = e.data;
    if (m.type === 'identified') {
      head = renderIdentify(m.info, text);
      output.innerHTML = head + '<div class="card"><span class="spinner"></span>Searching keyspaces…</div>';
    } else if (m.type === 'done') {
      output.innerHTML = head + renderResult(m.result, m.diagnostic, m.elapsed);
      goBtn.disabled = false;
      const copy = $('#copy');
      if (copy) {
        copy.onclick = () => {
          navigator.clipboard.writeText(m.result.plaintext);
          copy.textContent = 'Copied';
          setTimeout(() => { copy.textContent = 'Copy candidate text'; }, 1500);
        };
      }
      worker.terminate();
      worker = null;
    } else if (m.type === 'error') {
      output.innerHTML = `<div class="card"><p style="margin:0;color:var(--warn)">Something broke: ${esc(m.message)}</p></div>`;
      goBtn.disabled = false;
    }
  };

  worker.onerror = () => {
    output.innerHTML = '<div class="card"><p style="margin:0;color:var(--warn)">The solver failed to start. If you opened this file directly from disk, workers are blocked — run a local web server instead.</p></div>';
    goBtn.disabled = false;
  };

  worker.postMessage({ text, depth: 3 });
}

goBtn.addEventListener('click', crack);

input.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') crack();
});

const clearBtn = $('#clear');
if (clearBtn) {
  clearBtn.addEventListener('click', () => {
    input.value = '';
    output.innerHTML = '';
    input.focus();
  });
}

document.querySelectorAll('[data-sample]').forEach(btn => {
  btn.addEventListener('click', () => {
    input.value = SAMPLES[btn.dataset.sample] || '';
    crack();
  });
});

// A tool page can preload its own example via <body data-preset="...">.
const preset = document.body.dataset.preset;
if (preset && SAMPLES[preset]) input.placeholder = SAMPLES[preset];
