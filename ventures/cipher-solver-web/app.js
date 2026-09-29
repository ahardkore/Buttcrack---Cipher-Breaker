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

function renderResult(result, elapsed) {
  if (!result) {
    return `<div class="card">
      <div class="solved-head"><span class="label low">NO CONFIDENT SOLUTION</span></div>
      <p style="margin:0;color:var(--muted)">
        Nothing scored well enough to call a solution. This usually means the text is
        too short, is not English, or uses a cipher outside this tool's set — try the
        full <a href="https://github.com/ahardkore/Buttcrack---Cipher-Breaker">command-line
        version</a>, which searches a much larger space.
      </p></div>`;
  }
  const pct = Math.round(result.confidence * 100);
  const low = result.confidence < 0.45;
  const chain = result.chain && result.chain.length
    ? `<tr><td>decode chain</td><td><code>${esc(result.chain.join(' → '))} → ${esc(result.cipher)}</code></td></tr>`
    : '';
  return `<div class="card">
    <div class="solved-head">
      <span class="label ${low ? 'low' : ''}">${low ? 'BEST GUESS' : 'SOLVED'}</span>
      <span class="meta">confidence ${result.confidence.toFixed(2)} · ${elapsed.toFixed(2)}s</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <p style="margin:16px 0 6px;font-size:13px;color:var(--muted)">PLAINTEXT</p>
    <div class="plaintext">${esc(result.plaintext)}</div>
    <table class="evidence">
      <tr><td>cipher</td><td><code>${esc(result.cipher)}</code></td></tr>
      <tr><td>key</td><td><code>${esc(result.key)}</code></td></tr>
      ${chain}
      <tr><td>method</td><td>${esc(result.method)}</td></tr>
    </table>
    <div class="controls" style="margin-top:14px">
      <button class="ghost" id="copy">Copy plaintext</button>
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
      output.innerHTML = head + renderResult(m.result, m.elapsed);
      goBtn.disabled = false;
      const copy = $('#copy');
      if (copy) {
        copy.onclick = () => {
          navigator.clipboard.writeText(m.result.plaintext);
          copy.textContent = 'Copied';
          setTimeout(() => { copy.textContent = 'Copy plaintext'; }, 1500);
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
