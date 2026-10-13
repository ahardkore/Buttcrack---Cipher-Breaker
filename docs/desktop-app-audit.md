# Desktop application audit

Reviewed 2026-10-13, at `main` @ `2789e6d` (version 1.2.0). Scope: everything the
Windows download actually runs.

| Reviewed | Notes |
| --- | --- |
| `buttcrack/desktop.py` (1174 l.) | control window, nine Toplevel panels, tray wiring, console fallback |
| `buttcrack/_wintray.py` (375 l.) | ctypes Win32 shell-notify icon |
| `buttcrack/server.py` (415 l.) | HTTP API the window hosts |
| `buttcrack/static/` | `app.js` 854 l., `index.html` 325 l., `style.css` 311 l. |
| `packaging/windows/` | `buttcrack.spec`, `buttcrack.iss`, `build.ps1`, `test-installer.ps1`, entry points |
| `buttcrack/userdata.py` | where state lives |
| `ventures/cipher-solver-web/build_pages.py` | the storefront and the post-payment delivery page |

Method: static reading of the above, plus a live probe — the server was started on
127.0.0.1:8099 and exercised with `curl` (spoofed `Host`, cross-origin `POST`,
`/api/health`, `/api/paradigm`). Every "verified" note below is an observed result,
not an inference. Effort tags: **XS** ≤30 min, **S** half a day, **M** a day or more.

**Status (same day):** items A1, A2, C1, E1, B1, B4, D1 and D3 have been
implemented — see the "1.2.1" list at the end of the change that touches
`buttcrack/desktop.py`, `buttcrack/_wintray.py`, `buttcrack/server.py`,
`buttcrack/static/` and `ventures/cipher-solver-web/`. Everything else below is
still open, and the sections describe the code as it was audited.

Nothing here is a rewrite. The app is in good shape — the entry points, the
loopback binding, the fallback chain (window → message box → console), the
uninstaller's PATH cleanup and the installer contract are all deliberate and
correct. What follows is what a paying customer, a support inbox and a Cloudflare
download will actually run into.

---

## Do these first

1. **Tray icon dies permanently when Explorer restarts** (§A1). The app can end up
   invisible, still running, stoppable only from Task Manager.
2. **No way to cancel a running search** (§B1) — and the X button keeps it running
   in the tray, so a 300 s exhaustive run is unstoppable from the UI.
3. **`_NullStream` throws away the only diagnostic a frozen build produces** (§E1),
   while `entry_gui.py` says the opposite in a comment.
4. **No `Host`/`Origin` check on the local server** (§C1) — verified reachable from a
   rebound origin; six lines to close.
5. **Cloudflare specifics** (§D1–D3): custom domain not `r2.dev`, versioned immutable
   key, publish the SHA-256 — and decide what to do about the unsigned-installer
   card the delivery page prints today.

---

## A. Stability and Windows integration

### A1. The tray icon does not survive an Explorer restart — **S**

`_wintray.py` calls `Shell_NotifyIconW(NIM_ADD, …)` once (l.312) and `NIM_DELETE`
on stop (l.257). It never registers the shell's `TaskbarCreated` broadcast message,
so when `explorer.exe` restarts — a crash, a Windows update, "Restart Explorer" —
the icon is gone for good and nothing re-adds it.

That would be cosmetic except for `desktop.py`:

```python
root.protocol("WM_DELETE_WINDOW", hide if tray.active else shutdown)   # l.1050
```

After the icon is lost, closing the window still hides it (`hide()` → `withdraw()`,
l.1019), the local server keeps serving, and the process keeps its port. The user
believes they closed the app. Fix: register the message with
`RegisterWindowMessageW("TaskbarCreated")` and re-issue `NIM_ADD` when it arrives in
the window procedure; if `NIM_ADD` ever fails, fall back to treating close as quit
rather than hide.

### A2. No single-instance guard — **S**

Launching again from the Start menu (or double-clicking the shortcut) starts a
*second* server: `free_port()` (l.96) hands out a different port, so there are now
two tray icons, two browser tabs and two different `127.0.0.1:<port>` URLs. Also
two ledger writers over the same SQLite file in `%LOCALAPPDATA%\Buttcrack`.

Fix: a named mutex (`CreateMutexW(None, False, "Buttcrack.Desktop.1")` — a name the
installer's `AppMutex` can share), and when it already exists, forward "show
yourself" to the first instance using the message-only window the tray already
creates, then exit. Bonus: the second launch can hand over its `app.url` so the
browser tab that opens is the *existing* server.

### A3. DPI awareness is missing — **S**

There is no `SetProcessDpiAwareness` / `shcore` call anywhere in the tree (verified
by grep). Tk on Windows is therefore DPI-unaware, so on a 125–200% display the whole
control window and all nine panels are bitmap-stretched and blurry, and the
`Segoe UI 13 bold` headings scale worse than native controls. Fix: set
`shcore.SetProcessDpiAwareness(1)` (system-aware) before creating the root window,
then `root.tk.call("tk", "scaling", <screen dpi>/72)`. Per-monitor v2 needs a
manifest — system awareness is the cheap 90% and does not change layout.

### A4. Window position and size are not remembered — **XS**

`root` is created with `minsize(430, 0)` / `resizable(False, False)` (l.236–237) and
Tk's default position. The nine panels each `minsize(760, 560)` etc. and are placed
by the window manager — cascaded roughly over the parent. On a multi-monitor
workstation that means dragging the Transposition Lab back to the second screen
every session. Persist `wm_geometry()` per panel title in a small JSON under
`userdata.data_dir()` and restore on open. Same file is a natural home for the
`--port` preference in §B6.

### A5. The tray is the only clue that hiding is not quitting — **XS**

`hide()` sets a status string (l.1022) on the very window it is hiding. A one-time
balloon (`NIF_INFO`, i.e. `NIM_MODIFY` with `uFlags |= 0x10`) the first time the user
hides the window is the difference between "app closed" and "app in the tray" — and
it also covers the case in §A1 before the icon disappears.

### A6. The control window has no keyboard support — **XS**

Twelve `ttk.Button`s in a 3-column grid (l.982–1004) with no menu bar, no
accelerators and no default action; the address `Entry` is `state="readonly"` so it
cannot even take focus for Ctrl+C-style selection. A `tk.Menu` on the root with
`accelerator=` labels bound via `root.bind_all` gives Ctrl+Q/Alt+F4 parity, Ctrl+C
"copy address", F1 "open in browser", and makes the panels reachable without
hunting. The nine panels themselves are plain stacked widgets — `Tab` order is
creation order, which is not the visual order.

---

## B. The desktop app is a browser tab

That is a sound design (no WebView2 dependency, stdlib only, the UI is the same one
`serve` ships), but the browser is doing the work, so the gaps a user notices are
browser-tab gaps.

### B1. No cancel — **S**

`app.js` polls a job every 250 ms (l.340) and has no Cancel control; `resetResult()`
only *forgets* a job, and `server.py`'s `JobStore` has no abort path. So on the
default UI, a mis-chosen "300 s — everything" run is unstoppable except by closing
the tab — which does nothing to the daemon thread. And because closing the window
hides to tray (§A1), the machine keeps burning every core with no visible owner.

Cheap fix, no engine surgery: `Solver` already exposes a progress callback
(`engine.py:358,388-389`) which sub-solvers receive (`l.425`). Have
`JobStore._run` wrap its `progress` in a closure that raises a `JobCancelled`
exception when `job["cancel"]` is set, catch it, and mark the job `cancelled`; add
`POST /api/job/<id>/cancel` and a Cancel button next to the disabled "Break it".
Watch for broad `except Exception` inside the engine swallowing the sentinel —
derive it from `BaseException` if so.

### B2. Nothing is remembered between sessions — **XS**

No `localStorage`/`sessionStorage` anywhere in `app.js` (verified by grep). Closing
the tab loses the ciphertext, the hints, the budget and the report. For a desktop
product that is the most-remarked missing feature. Store `{text, budget, workers,
depth, language, hints}` under one versioned key and offer "Restore last session?"
rather than silently repopulating; optionally keep the last ~20 input hashes with
their verdicts as a history list.

### B3. No file input — **XS**

No `dragover`/`drop` handler and no `<input type="file">` (verified). A user with a
4 KB ciphertext in a `.txt` cannot drop it on the window; they must open it
elsewhere and copy. `FileReader` + a drop target on `#input` is ~20 lines, and it
stays offline — worth saying so in the UI, since "no ciphertext leaves the machine"
is the product's promise (`index.html` footer).

### B4. Default worker count loads the whole machine — **XS**

`renderWorkers()` selects `cpus` (l.182), so on a 4-core laptop the default is 4
processes and the UI the user is *looking at* competes with the search it started.
Default to `max(1, cpus - 1)` and label the last entry "…, leaves a core free".

### B5. Accessibility and printing — **XS**

- No `color-scheme: dark` on `:root`, so the UI's dark theme sits next to the light
  UA theme for scrollbars, `<select>` dropdowns and autofill — visible seams in an
  otherwise carefully matched palette (no `prefers-color-scheme` either, so a light
  theme is not an option; the point is just to declare the one you have).
- No `@media print` rule exists, yet `tests/browser/app.spec.js` has a test named
  "responsive accessibility modes and print mode" that only emulates print and
  asserts `body` is visible. Printing a report today prints the dark theme. Either
  add a two-rule print stylesheet (white background, black text, no chrome) or
  rename the test.
- Focus styles exist (`style.css:117`), so keyboard users are fine on the web side.
  The Tk side (§A6) is where keyboard support is thin.

### B6. A stable URL worth bookmarking — **XS**

`PREFERRED_PORT = 8080` (l.42) gives a stable URL *when it is free*; the moment
another app holds 8080, `free_port()` randomises it and the user's bookmark is
dead. Remember the last successfully bound port in `userdata.data_dir()` and prefer
it on the next launch (bind → on `EADDRINUSE`, try the remembered port → then
random). Also surface "port 8080 was busy, using 53412" in `summary_lines()` — it is
already the visible line 2 of the window.

### B7. Make the UI open in an app-style window — **M (optional)**

Three lines get 90% of the "real app" feel with no new dependency: if Edge/Chrome
is present, launch `msedge --app=http://127.0.0.1:<port>/` (chromeless window, its
own taskbar entry, no tabs/URL bar), else fall back to `webbrowser.open()` as today
(`LocalApp.open_browser`, l.154). Keep it behind `--browser`/default-on and a tray
"Open in app window". A WebView2 wrapper is the "real" answer but breaks the
no-dependencies, no-installer-payload story — not worth it for 1.2.

---

## C. The local server (hardening)

### C1. `Host` and `Origin` are not checked — **XS, verified**

Observed against a live instance:

```
$ curl -H "Host: evil.example" http://127.0.0.1:8099/api/health   → 200 OK (full JSON)
$ curl -X POST http://127.0.0.1:8099/api/crack \
      -H "Content-Type: text/plain" -H "Origin: https://evil.example" \
      -d '{"text":"Wkh txlfn…","budget":1}'                       → {"job":"b9bff2d1d1d8", …}
```

`Handler` never looks at the `Host` header, and `_read_body()` ignores
`Content-Type`, so a `text/plain` POST is a CORS *simple* request — no preflight — and
the JSON body is parsed anyway. The server sends no CORS headers, so a normal
cross-origin `fetch` cannot read the reply; the exposure is DNS rebinding, where the
attacker's page is served from a hostname that resolves to 127.0.0.1, making it
same-origin: then it can read everything the API returns *and* queue up to 32 crack
jobs at `workers = cpus × 2` (`server.py:51`, `l.83`, `l.254`). The desktop window and
`serve` share this handler.

Fix in `Handler`: reject any request whose `Host` is not `127.0.0.1[:port]`,
`localhost[:port]` or `[::1][:port]` with 403, and reject a request whose `Origin`
is present and not that same origin. Add `Content-Type: application/json` as a
requirement for `POST /api/*` as belt-and-braces (it forces a preflight, which the
browser will refuse). While there: send `Content-Security-Policy: default-src
'self'; img-src 'self' data:` — `index.html` has no inline scripts or styles and the
only data URI is the favicon, so it will not break anything (verified: no `onclick`,
no `<style>`).

### C2. `buttcrack serve` defaults to the whole network — **XS**

`serve(host="0.0.0.0")` (`server.py:367`) versus `LocalApp`'s loopback binding. That
is deliberate and documented, but combined with C1 it means an unprotected engine on
every interface. After C1 the Host check covers it; also print the LAN URL and a
"reachable from your network" warning so nobody leaves it running on a café Wi-Fi
believing it is local-only.

### C3. Job eviction can orphan a running search — **XS**

`JobStore._prune()` (l.78–86) drops finished jobs after 600 s, but the `MAX_JOBS`
loop evicts the *oldest* job whether or not it is done. Evicting a running job
leaves its thread and its ledger writes alive with no way to observe or stop them —
the same symptom as §B1. Prefer refusing new jobs (HTTP 429) or evicting only
finished ones; once §B1 exists, evicting a running job can cancel it cleanly.

### C4. Not a bug, worth a sentence in the UI — **XS**

`/api/paradigm` returns the corpus with full texts (~11 KB) and the browser polls
`/api/job/<id>` 4×/s. Both are fine locally; they are exactly what an unbounded
public-LAN deployment would not want. The 403-from-Host fix is the real defence;
no further rate limiting is warranted for a single-user desktop app.

---

## D. Shipping the installer on Cloudflare

The plumbing already exists and is the right shape: `site.json` →
`windows_app.delivery_url`, validated in `build_pages.py:1101–1136` (must be https,
must not point back at the public site, warns if it does not end in `.exe`), and the
post-payment page is unguessable-by-construction (`windows_app.token`,
`thank-you-<token>.html`). Four Cloudflare-specific notes:

### D1. Serve from an R2 custom domain, and turn `r2.dev` off — **XS**

Cloudflare's own dashboard text: enabling `r2.dev` gives every object a second public
URL; "usage is rate-limited and is not recommended for production", and Access/Cache
are unavailable on it. For a paid installer that is doubly wrong — the dev hostname
bypasses the unguessable-URL design and has been blocked outright by some ISPs.
Attach a bucket custom domain (e.g. `dl.example.com`), put *that* URL in
`windows_app.delivery_url`, and disable the `pub-<hash>.r2.dev` hostname in the
bucket settings. Keep public listing off.

### D2. Versioned keys with long-lived cache headers — **XS**

`build.ps1` already names the installer `buttcrack-setup-<version>.exe` (l.3). Upload
it under that exact key with `Cache-Control: public, max-age=31536000, immutable`,
and never reuse a key for a different binary (a re-upload of the same key is how a
CDN hands one customer the previous build). Cloudflare does **not** cache `.exe` by
default — the default cacheable-extension list covers `zip`/`7z`/`rar` but not
`exe` — so add a Cache Rule ("Cache Everything" on `*/buttcrack-setup-*.exe`) if you
want repeat downloads served from the edge; with R2's zero egress it is an
optimisation, not a cost fix. Note the community-reported failure mode where
"Cache Everything" plus an origin `Cache-Control: no-store`/`no-cache` produces
intermittent 404s — the object headers and the rule have to agree.

### D3. Publish the digest, and fix the card that says the build is unsigned — **XS**

The release job already writes `dist/installer/INSTALLER-SHA256.json`
(`release.yml:171–187`) and `build_pages.py:1176–1179` already renders
`windows_app.sha256` on the delivery page — so the remaining step is to fill that
field from the release artifact on every build (a script that reads the JSON and
patches `site.json`, or a Cloudflare-side `SHA256SUMS` object next to the binary).

The bigger one is the hardcoded card at `build_pages.py:1203`:

> "Windows will warn you the first time — The installer is not code-signed, so
> SmartScreen shows a blue *"Windows protected your PC"* box."

Every customer paying $39.99 reads that today — and it is repeated on the storefront
(`l.1317`) and in the FAQ (`l.1702`). Signing is already documented
(`docs/windows-installer.md:133–162`, `build.ps1 -CertThumbprint`) but the default
build is unsigned, so the honest fix is to make all three occurrences conditional —
a `windows_app.signed: true` flag that swaps the text for "signed by …; verified by
Windows" — and remove them the moment a certificate exists. Until then the wording
is correct and should stay; just do not let it become permanent by accident. Note
also that a browser-downloaded `.exe` from any host (Cloudflare included) carries the
Mark-of-the-Web, so signing is the only thing that changes the dialog, not hosting.

### D4. Make the upload reproducible — **S**

Today the only artifacts are GitHub Actions ones, which expire after the default
retention window and require a GitHub login to fetch. Since the host is Cloudflare,
add a final step to `release.yml` that pushes `buttcrack-setup-<version>.exe` and
`INSTALLER-SHA256.json` to the R2 bucket (an R2 API token + account id in repository
secrets, `aws s3 cp --endpoint-url https://<account>.r2.cloudflarestorage.com`, or
`wrangler r2 object put`), triggered only on tag pushes so fork PRs never see the
secrets. That removes the manual upload step and guarantees the digest on the page
matches the binary in the bucket.

### D5. If you enable Bot Fight Mode, verify plain downloads — **XS**

Bot Fight Mode / Super Bot Fight Mode sits in front of the zone and can challenge
non-browser fetches. Whatever hosts the installer, check once with
`curl -sI https://<host>/buttcrack-setup-1.2.0.exe` from outside the dashboard and
confirm a 200 with `Content-Length` rather than a challenge page. Add an explicit
skip rule for the download path if it interferes.

---

## E. Diagnostics and support

### E1. The frozen build throws away every traceback — **S**

`_NullStream.write()` returns the length and discards the text (`desktop.py:50–75`),
and `entry_gui.py` installs it before anything else runs. Its comment claims the
opposite:

> "Give them a sink before any other code runs so that a failing worker leaves a
> readable trace on disk rather than silent nothing."

Nothing reaches disk. There is no logging framework anywhere in `buttcrack/`
(verified by grep) and no `FileHandler`. So when a multiprocessing worker dies in the
windowed build — precisely the failure mode the py3.13 CI work chased — the child's
traceback (written to stderr by CPython) vanishes and the user sees only "search
ended". Make `_NullStream` tee to
`%LOCALAPPDATA%\Buttcrack\logs\buttcrack-<date>.log` with a size cap and a couple of
rotations, keep `write()` non-throwing, and the comment becomes true.

### E2. A "support" button and a `doctor` command — **S**

Once §E1 exists, the product can answer "what happened?" without email. Two cheap
pieces:

- Windows window: a "Copy diagnostics" button (Ctrl+D) placing version, Python,
  frozen/not, port, data dir, log path, model provenance, cipher count, tray state
  and the last job's verdict on the clipboard — one paste into a support email.
- CLI: `buttcrack doctor`, printing the same block plus write-permission checks on
  `data_dir()` and whether 8080 is free (`free_port` is already there, l.96). It
  also gives `test-installer.ps1` a single command to smoke-test a fresh install.
- Add "Open data folder" (`os.startfile(data_dir())`) to the Tk window and the tray
  menu; users delete `pk9-results.sqlite3` often enough that finding it should not
  require knowing the Windows convention.

### E3. Decide about updates — **M, a decision more than a build**

There is no update check anywhere (verified), and the storefront FAQ promises "no
analytics, no update check and no account"
(`ventures/cipher-solver-web/build_pages.py:1706`). That promise is worth keeping —
but for a paid, Cloudflare-hosted, unsigned build, the only fix path for a bad 1.2.0
is "download again". The minimum that keeps the promise: an optional, user-clicked
**Check for updates** in the window's About area that fetches a small
`version.json` from the Cloudflare host (`{"version": "1.2.1", "url": …}`) and
compares strings — never on startup, never automatic, ideally off by default with a
checkbox. If that is not wanted, make the storefront say how fixes are delivered
("the download page always serves the newest build") so nobody expects an updater.

---

## F. Tests and packaging

### F1. The browser suite asserts almost nothing — **S**

`tests/browser/app.spec.js` is four tests; three of them cannot fail for the
behaviour they name:

- `toContainText(/assistant|score|verify|crib|transposition/i)` on `body` matches the
  tab labels themselves — it passes on a page where every panel is broken.
- `page.locator('#error-card, #error-text, body').first()` resolves to `body`, so
  "session export/import" asserts nothing about export or import.
- "print mode" emulates print and asserts `body` is visible.

Replace with one real end-to-end path — paste the Caesar sample, click **Break it**,
wait for `#plaintext` to contain "the quick brown fox", assert the confidence row and
the copy button — plus tab keyboard activation (arrow keys between `role="tab"`
buttons are not wired), and the 640 px layout. That single test would have caught the
last two CI regressions in this area.

### F2. What the frozen build needs that CI does not check — **S**

`test-installer.ps1` boots the desktop exe (l.429) and checks the CLI contract
(l.395–421) — good. Worth adding while the installer is being touched:

- launch the app twice and assert the second launch does not start a second server
  (fails today — §A2);
- after closing the window, assert the process is still alive *and* reachable (i.e.
  the tray path) and then quit via the tray message;
- assert the log file in §E1 was created and contains the version banner.

### F3. Packaging nits — **XS**

- `buttcrack.spec` sets `upx=False` and the version resource, and includes Tk in both
  exes — all correct. There is no `Windows longPathAware`/`dpiAware` manifest; §A3 is
  the reason to add one.
- `build.ps1` finds Inno Setup through the uninstall registry (l.93–118) — fine —
  but the release workflow's `installer` job and the docs should pin the same Inno
  version so a local build and the CI build produce comparable sizes.
- `packaging/windows/test-installer.ps1` is 505 lines of PowerShell with no
  equivalent on the Python side; anything it learns about behaviour (rather than
  installation) is better placed in `tests/` where the fast suite can run it on any
  OS.

---

## Effort summary

| # | Finding | Effort | Value |
| --- | --- | --- | --- |
| A1 | Tray icon lost after Explorer restart | S | High |
| A2 | No single-instance guard | S | High |
| A3 | No DPI awareness | S | High (visible) |
| A4 | Window geometry not remembered | XS | Medium |
| A5 | First-hide balloon | XS | Medium |
| A6 | Menu bar and accelerators in the Tk window | XS | Medium |
| B1 | Cancel a running search | S | High |
| B2 | Remember the last session | XS | High |
| B3 | Drop/open a file | XS | Medium |
| B4 | Default workers = cores − 1 | XS | Medium |
| B5 | `color-scheme`, print stylesheet | XS | Low |
| B6 | Remember the bound port | XS | Medium |
| B7 | `msedge --app=` window | M | Medium |
| C1 | `Host`/`Origin`/CSP checks | XS | High |
| C2 | Warn on the `serve` LAN binding | XS | Low |
| C3 | Do not evict running jobs | XS | Medium |
| D1 | R2 custom domain, disable `r2.dev` | XS | High |
| D2 | Versioned immutable keys + cache rule | XS | Medium |
| D3 | Publish digest; conditional unsigned card | XS | High |
| D4 | Upload from the release job | S | Medium |
| D5 | Verify downloads behind Bot Fight Mode | XS | Low |
| E1 | `_NullStream` → log file on disk | S | High |
| E2 | Diagnostics button + `buttcrack doctor` | S | High |
| E3 | Decide on updates (or document the absence) | M | Medium |
| F1 | Real browser test | S | High |
| F2 | Frozen-build behaviours in the installer test | S | Medium |
| F3 | Packaging nits (manifest, Inno pin) | XS | Low |

A credible 1.2.1: §A1, §A2, §C1, §E1, §B1, §B4, §D1, §D3 — one focused day, no new
dependencies, and it covers every finding that a first-time Windows user or a paying
customer would notice.
