/* Web Worker: solving takes a few seconds of tight loops, so it runs off the
 * main thread and the page stays responsive. */
'use strict';

importScripts('model.js', 'solver.js');

self.onmessage = e => {
  const { text, depth } = e.data;
  const started = Date.now();
  try {
    const info = identify(text);
    self.postMessage({ type: 'identified', info });
    const result = solve(text, depth == null ? 3 : depth);
    self.postMessage({ type: 'done', result, elapsed: (Date.now() - started) / 1000 });
  } catch (err) {
    self.postMessage({ type: 'error', message: String(err && err.message || err) });
  }
};
