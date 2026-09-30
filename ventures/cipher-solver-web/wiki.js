/* Wiki chrome: search, random article, the main page's rotating boxes, and
 * the sidebar's behaviour on small screens. No framework, no dependencies —
 * the search index is generated at build time by build_pages.py into
 * wiki-index.js, so this file never guesses at page slugs.
 */
(function () {
  'use strict';

  var IDX = (window.WIKI_INDEX && window.WIKI_INDEX.pages) || [];
  var FEATURED = (window.WIKI_INDEX && window.WIKI_INDEX.featured) || [];
  var FACTS = (window.WIKI_INDEX && window.WIKI_INDEX.facts) || [];

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ------------------------------------------------------------- search */
  function score(page, q) {
    var t = page.t.toLowerCase();
    var f = (page.f || '').toLowerCase();
    var d = (page.d || '').toLowerCase();
    if (t === q) return 100;
    if (t.indexOf(q) === 0) return 70;
    if (t.indexOf(q) !== -1) return 50;
    if (f.indexOf(q) !== -1) return 20;
    if (d.indexOf(q) !== -1) return 10;
    return -1;
  }

  function search(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    var out = [];
    for (var i = 0; i < IDX.length; i++) {
      var s = score(IDX[i], q);
      if (s >= 0) out.push([s, IDX[i]]);
    }
    out.sort(function (a, b) { return b[0] - a[0] || a[1].t.localeCompare(b[1].t); });
    return out.slice(0, 8).map(function (pair) { return pair[1]; });
  }

  function render(box, results, q) {
    if (!results.length) {
      box.innerHTML = '<div class="wiki-search-empty">No article matches “' + esc(q) + '”.</div>';
      box.hidden = false;
      return;
    }
    var html = results.map(function (r, i) {
      return '<a class="wiki-search-hit' + (i === 0 ? ' first' : '') + '" href="' + esc(r.s) + '">' +
        '<span class="wiki-search-hit-title">' + esc(r.t) + '</span>' +
        (r.f ? '<span class="wiki-search-hit-family">' + esc(r.f) + '</span>' : '') +
        '</a>';
    }).join('');
    box.innerHTML = html;
    box.hidden = false;
  }

  document.querySelectorAll('.wiki-search').forEach(function (root) {
    var input = root.querySelector('.wiki-search-input');
    var box = root.querySelector('.wiki-search-results');
    var go = root.querySelector('.wiki-search-go');
    if (!input || !box) return;

    input.addEventListener('input', function () {
      var q = input.value;
      if (!q.trim()) { box.hidden = true; box.innerHTML = ''; return; }
      render(box, search(q), q);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var hits = search(input.value);
        if (hits.length) window.location.href = hits[0].s;
      } else if (e.key === 'Escape') {
        box.hidden = true;
      }
    });
    input.addEventListener('focus', function () {
      if (input.value.trim()) render(box, search(input.value), input.value);
    });
    document.addEventListener('click', function (e) {
      if (!root.contains(e.target)) box.hidden = true;
    });
    if (go) {
      go.addEventListener('click', function () {
        var hits = search(input.value);
        if (hits.length) window.location.href = hits[0].s;
        else input.focus();
      });
    }
  });

  /* ----------------------------------------------------- random article */
  document.querySelectorAll('.wiki-random').forEach(function (a) {
    a.addEventListener('click', function (e) {
      if (!IDX.length) return;
      var here = window.location.pathname.split('/').pop() || 'cipher-wiki.html';
      var pick = null;
      for (var tries = 0; tries < 12 && !pick; tries++) {
        var cand = IDX[Math.floor(Math.random() * IDX.length)];
        if (cand.s !== here && cand.s !== 'cipher-wiki.html') pick = cand;
      }
      if (pick) {
        e.preventDefault();
        window.location.href = pick.s;
      }
    });
  });

  /* -------------------------------------------- main page rotation boxes */
  function dayIndex() {
    var start = new Date(new Date().getFullYear(), 0, 0);
    return Math.floor((Date.now() - start.getTime()) / 86400000);
  }

  var feat = document.getElementById('mp-featured-slot');
  if (feat && FEATURED.length > 1) {
    var f = FEATURED[dayIndex() % FEATURED.length];
    feat.innerHTML =
      '<h3><a href="' + esc(f.s) + '">' + esc(f.t) + '</a></h3>' +
      '<p>' + f.d + '</p>' +
      '<p class="mp-readmore"><a href="' + esc(f.s) + '">Read the article →</a></p>';
  }

  var dyk = document.getElementById('mp-dyk-slot');
  if (dyk && FACTS.length > 1) {
    dyk.innerHTML = '<p>' + FACTS[dayIndex() % FACTS.length] + '</p>';
  }

  /* ------------------------------------------- small-screen side panels */
  function fitSidebar() {
    var narrow = window.innerWidth < 1080;
    document.querySelectorAll('.wiki-side .wiki-side-group').forEach(function (d) {
      if (narrow) d.removeAttribute('open');
    });
  }
  if (document.querySelector('.wiki-side')) {
    fitSidebar();
    var t;
    window.addEventListener('resize', function () {
      clearTimeout(t);
      t = setTimeout(fitSidebar, 150);
    });
  }
})();
