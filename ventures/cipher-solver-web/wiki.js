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

    /* Arrow keys walk the results, Enter follows the highlighted one, Escape
       closes — the combobox pattern keyboard users expect from a search box.
       The highlighted row gets .is-active rather than reusing .first, because
       .first is what mouse users see on a fresh query. */
    var active = -1;

    function rows() {
      return box.querySelectorAll('.wiki-search-hit');
    }

    function setActive(n) {
      var r = rows();
      if (!r.length) { active = -1; return; }
      active = (n + r.length) % r.length;
      for (var i = 0; i < r.length; i++) {
        r[i].classList.toggle('is-active', i === active);
      }
    }

    function hideBox() {
      box.hidden = true;
      box.innerHTML = '';
      active = -1;
      input.setAttribute('aria-expanded', 'false');
    }

    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-autocomplete', 'list');
    if (!box.id) box.id = 'wiki-search-results-' + Math.floor(Math.random() * 1e6).toString(36);
    input.setAttribute('aria-controls', box.id);

    input.addEventListener('input', function () {
      var q = input.value;
      if (!q.trim()) { hideBox(); return; }
      render(box, search(q), q);
      input.setAttribute('aria-expanded', 'true');
      active = -1;
    });
    input.addEventListener('keydown', function (e) {
      var r = rows();
      if (e.key === 'ArrowDown' && r.length) {
        e.preventDefault();
        setActive(active + 1);
      } else if (e.key === 'ArrowUp' && r.length) {
        e.preventDefault();
        setActive(active - 1);
      } else if (e.key === 'Enter') {
        var all = search(input.value);
        if (active >= 0 && r[active]) window.location.href = r[active].getAttribute('href');
        else if (all.length) window.location.href = all[0].s;
      } else if (e.key === 'Escape') {
        hideBox();
      }
    });
    input.addEventListener('blur', function () {
      /* A click on a result fires blur first; give the click a beat. */
      setTimeout(function () { hideBox(); }, 150);
    });
    input.addEventListener('focus', function () {
      if (input.value.trim()) {
        render(box, search(input.value), input.value);
        input.setAttribute('aria-expanded', 'true');
      }
    });
    box.addEventListener('mousedown', function (e) { e.preventDefault(); });
    document.addEventListener('click', function (e) {
      if (!root.contains(e.target)) hideBox();
    });
    if (go) {
      go.addEventListener('click', function () {
        var found = search(input.value);
        if (found.length) window.location.href = found[0].s;
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

  /* Study aid: copy code examples without changing the article text. */
  document.querySelectorAll('.wiki-article pre').forEach(function (pre) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy-code';
    button.textContent = 'Copy example';
    button.addEventListener('click', function () {
      var text = pre.innerText || pre.textContent || '';
      if (!navigator.clipboard) { button.textContent = 'Select to copy'; return; }
      navigator.clipboard.writeText(text).then(function () {
        button.textContent = 'Copied';
        window.setTimeout(function () { button.textContent = 'Copy example'; }, 1400);
      });
    });
    pre.parentNode.insertBefore(button, pre);
  });

  (function studyControls() {
    var root = document.documentElement;
    document.querySelectorAll('[data-study]').forEach(function (button) {
      button.addEventListener('click', function () {
        var mode = button.getAttribute('data-study');
        root.classList.toggle('study-large', mode === 'larger');
        root.classList.toggle('study-contrast', mode === 'contrast');
        if (mode === 'reset') {
          root.classList.remove('study-large', 'study-contrast');
          try { localStorage.removeItem('cipher-study-mode'); } catch (_) {}
        } else {
          try { localStorage.setItem('cipher-study-mode', mode); } catch (_) {}
        }
      });
    });
    try {
      var saved = localStorage.getItem('cipher-study-mode');
      if (saved === 'larger' || saved === 'contrast') root.classList.add('study-' + saved);
    } catch (_) {}
  }());
