# The Windows installer

Short answer to the question that produced this document: **yes.** `buttcrack`
is pure Python with no runtime dependencies and its language model is already
inside the package, which makes it close to the easiest kind of program there
is to freeze into an `.exe`. The result is one file, around 25 MB, that anyone
can download from any web server and double-click. No Python, no `git`, no
package manager, no GitHub account, no command line.

This page covers how to build it and where to put it.

---

## What gets built

```
dist/
  Buttcrack/                       the application directory
    Buttcrack Desktop.exe          windowed  -- the desktop app
    buttcrack.exe                  console   -- the CLI
    _internal/                     Python runtime, the six language models, the web UI
  installer/
    buttcrack-setup-1.2.0.exe      ← this is the thing you publish
    buttcrack-setup-1.2.0.exe.sha256
```

Two executables, one shared runtime:

| | `Buttcrack Desktop.exe` | `buttcrack.exe` |
| --- | --- | --- |
| Start menu / desktop shortcut | yes | no |
| Console window | no | yes, it *is* the console |
| What it does | starts the local server on `127.0.0.1`, opens your browser, sits in the tray | the full CLI from the README |
| Equivalent to | `buttcrack app` | `buttcrack` |

They share one copy of Python and one copy of the 1.8 MB of n-gram tables, so
shipping both costs almost nothing over shipping either.

The desktop app is **not** called `Buttcrack.exe`, and that is not a style
choice. Windows and macOS filesystems are case-insensitive by default, so a build
directory containing both `Buttcrack.exe` and `buttcrack.exe` is a directory
containing one file: `COLLECT` writes the second over the first, the bundle holds
a single program, and the Start menu quietly launches whichever survived. The
first Windows build of this installer did exactly that, and shipped a "desktop
app" whose shortcut opened the command line.

Three things now refuse to let it happen again: `buttcrack.spec` exits if the two
names collide when lowercased, `build.ps1` compares the two files rather than
their names, and `test-installer.ps1` checks the installed programs have
different contents and that the shortcut's target is the one it claims to be.

### What the user sees

1. Downloads `buttcrack-setup-1.2.0.exe`.
2. Runs it. **No UAC prompt** — it installs per-user into
   `%LOCALAPPDATA%\Programs\Buttcrack`. (The first page offers a machine-wide
   install for anyone who wants one.)
3. Start menu → **Buttcrack**. A small window appears saying it is running, and
   the browser opens on the solver.
4. Everything is local. The server binds loopback only; no text leaves the
   machine, and the app never calls home.
5. Add/Remove Programs → Buttcrack → Uninstall removes all of it, including
   the `PATH` entry if they took it.

Optional during install: a desktop shortcut, and putting the CLI on `PATH` so
`buttcrack "Wkh txlfn eurzq ira"` works in any terminal. Both are off by
default except the desktop shortcut.

---

## Building it

### Prerequisites

On the Windows machine you build from:

* **Python 3.9+** from [python.org](https://www.python.org/downloads/windows/) —
  during installation tick **"tcl/tk and IDLE"** (the desktop window is Tk) and
  **"Add python.exe to PATH"**.
* **Inno Setup 6.3+**: `winget install --id JRSoftware.InnoSetup`, or from
  [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php).

PyInstaller is installed automatically into a throwaway virtualenv; it is not
added to your environment and is not a dependency of the project.

### One command

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

(That builds. `python scripts\publish_installer.py ...` is what puts the result
where buyers can download it — see [Publishing it](#publishing-it-one-command-or-one-click)
below.)

or double-click `packaging\windows\build.bat`.

It will, in order: find a usable Python, refuse to continue if that Python has
no `tkinter`, make `.venv-build\`, install PyInstaller, freeze both
executables, **run the frozen CLI against a Caesar sample and check it comes
back solved**, build the installer, and print the SHA-256.

That smoke test matters more than it looks. The failure mode of a frozen
Python app is almost never "it does not start" — it is "it starts, and then
cannot do anything, because a data file did not come along". Breaking an
actual cipher is the only check that catches it.

Useful flags:

```powershell
.\build.ps1 -Clean            # delete dist\, build\ and .venv-build\ first
.\build.ps1 -SkipInstaller    # stop after the executables
.\build.ps1 -CertThumbprint ABCD...   # sign everything (see below)
```

### Building the pieces separately

```powershell
pyinstaller --clean --noconfirm packaging\windows\buttcrack.spec
iscc packaging\windows\buttcrack.iss
```

The spec is cross-platform as written — run it on macOS or Linux and you get
the same two binaries without the `.exe` suffix, which is a quick way to test a
change to it. Only the Inno Setup step is Windows-only.

### Releasing a new version

The version comes from one place: `__version__` in `buttcrack/__init__.py`
(mirrored in `pyproject.toml`). Bump it there, rebuild, and the executables'
file properties, the installer filename and the Add/Remove Programs entry all
follow. `AppId` in `buttcrack.iss` must **never** change — it is what makes the
next installer an upgrade rather than a second entry in Add/Remove Programs.

---

## Code signing, and what happens if you skip it

An unsigned installer downloaded from the web gets a blue **"Windows protected
your PC"** SmartScreen dialog. It is dismissible — *More info* → *Run anyway* —
but a meaningful share of people stop there.

Options, in order of cost:

1. **Ship unsigned and explain it on the download page.** Show the SHA-256,
   say plainly that Windows will warn and why, and show the two clicks. This is
   what most small free tools do and it works.
2. **Build reputation.** SmartScreen tracks reputation per signing identity, and
   for unsigned files per exact binary. Keeping the same filename pattern,
   publishing checksums, and not rebuilding constantly all help a little.
3. **An OV code-signing certificate**, roughly $200–400/year (Sectigo, DigiCert,
   SSL.com). Since June 2023 the private key must live on a hardware token or
   in a cloud HSM, so there is setup involved. It removes the "unknown
   publisher" wording but reputation still has to accrue.
4. **An EV certificate**, roughly $400–700/year. Historically granted immediate
   SmartScreen trust. This is the only option that makes the warning go away on
   day one.

If you have a certificate installed:

```powershell
.\build.ps1 -CertThumbprint <thumbprint-from-certmgr.msc>
```

Both executables are signed before packaging and the installer after, each with
an RFC 3161 timestamp, so signatures stay valid after the certificate expires.

### Antivirus false positives

PyInstaller output is occasionally flagged by small-vendor engines, because
"self-extracting executable that loads a Python interpreter" also describes a
lot of malware. Two things in this build already reduce it: **UPX compression
is off** (packed binaries are far more likely to be flagged) and the
executables carry full `VERSIONINFO` metadata. If a specific engine still
complains, submit a false-positive report to that vendor — they are usually
turned around in a few days.

---

## Hosting it

The installer is sold for $39.99 through a Stripe Payment Link on
[`windows-app.html`](../ventures/cipher-solver-web/windows-app.html). That
changes where it can live, and the rule is short:

> **Never put the installer in this repository, and never serve it from the
> site.** Both are public. A paid `.exe` in either one is a paid `.exe` anyone
> can help themselves to, and once it is in Git history it is there for good.

`scripts/build_site.py` enforces this: it refuses to assemble a site tree
containing an `.exe` or `.msi`, so a stray copy fails the deploy instead of
quietly publishing the product. (`BUTTCRACK_PUBLISH_BINARIES=1` overrides it,
for the day you decide to give something away.)

### Publishing it: one command, or one click

Building the installer and *publishing* it are two steps on purpose — one is
verified by CI on every push, the other decides where the paid file lives — and
there is a command for the second:

```console
python scripts/publish_installer.py dist/installer/buttcrack-setup-1.2.0.exe --dry-run
python scripts/publish_installer.py dist/installer/buttcrack-setup-1.2.0.exe
```

The first prints what would happen and uploads nothing, and needs no credentials
at all. The second uploads it under an unguessable name and prints the four
values `site.json` needs — `delivery_url`, `version`, `size`, `sha256` — which is
the whole job. Add `--update-site-json ventures/cipher-solver-web/site.json` and
it writes those four keys for you as well, leaving the rest of that
hand-maintained file exactly as it was and printing each value it changed:

```
published https://downloads.yourdomain/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe
  15,558,568 bytes (15.6 MB), sha256 8cb5ffeb...

ventures/cipher-solver-web/site.json, under windows_app:
  "delivery_url": "https://downloads.yourdomain/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe",
  ...
```

Four environment variables say where, and the two credentials are the pair any
S3 client already reads. The endpoint, bucket and base URL are configuration,
not secrets; only the keys are:

```bash
export BUTTCRACK_DELIVERY_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
export BUTTCRACK_DELIVERY_BUCKET=buttcrack-downloads
export BUTTCRACK_DELIVERY_BASE_URL=https://downloads.yourdomain   # the custom domain on the bucket
export BUTTCRACK_DELIVERY_PREFIX=                                 # optional folder inside the bucket
export AWS_ACCESS_KEY_ID=...                                      # an R2 API token, or an S3 key
export AWS_SECRET_ACCESS_KEY=...
```

The upload itself is `aws s3 cp`, so it works against R2, B2 and S3 unchanged and
the script does not carry a second copy of the S3 signing rules. It sets the
three headers the download depends on, which are easy to lose with a drag-and-drop
upload: `Content-Type: application/octet-stream` (a host that guesses serves a
`.exe` as `text/html` and it arrives corrupt), `Content-Disposition: attachment`,
and a long `Cache-Control` (the object never changes once it is named).

Two more things it does, both because they have bitten this project:

* **The version comes out of the filename**, and anything that is not
  `buttcrack-setup-<version>.exe` is refused. The installer filename, the
  Add/Remove Programs entry and `OutputBaseFilename` all follow `__version__`;
  a publish that reads the name is a publish that cannot disagree with the build.
* **It will not publish a file that disagrees with its own `.sha256`.** The
  sidecar `build.ps1` writes next to the installer is compared before anything is
  uploaded, and the two are uploaded together. The page tells buyers to check the
  digest, so a digest that does not match its file is worse than none at all.

**Publish the build that was tested, and only that one.** The digest this prints
is of the file on the disk it ran on; `site.json` has to carry that same number.
Two builds of the same commit are not byte-identical, so fetching a fresh
artifact and publishing an older digest — or the other way round — describes a
file nobody can download. CI enforces this by fetching the artifact of a run that
already passed the install-and-uninstall test rather than building again:

**Actions → Publish installer to storage → Run workflow.** It takes an optional
artifact id (blank publishes the newest live one) and an optional token (blank
mints a new URL). `dry_run` prints the whole thing, including the URL, without
uploading and without needing any secrets — which is the way to see what a first
publish would look like. The storage credentials go in **Settings → Secrets and
variables → Actions** under exactly the five names above, plus the optional
prefix; the run checks they are set *before* it fetches anything, so an
unconfigured repository says which value is missing instead of failing at the
upload with an authentication error from a storage service.

`gh workflow run 'Publish installer to storage'` does the same from a terminal.
The run writes the four values into `site.json` in its checkout and shows you the
resulting `git diff` in the step summary, rather than committing it: a runner
should not push to `main` on its own, and four lines is the whole change.

Two things about ordering. The workflow cannot be dispatched until it is on the
default branch, so it becomes runnable the moment this merges to `main` — before
that, `publish_installer.py` runs perfectly well by hand. And the artifact it
fetches belongs to a `Release artifacts` run, so that run has to have happened
first; the workflow says which version it picked and fails cleanly if no
installer artifact is live.

### Withdrawing a publish

Republishing with the same URL is what `--token` is for: pass back the token
already in `delivery_url` and the object name, and therefore the link in buyers'
bookmarks, stays the same. Pass a new one and the old URL stops being the one you
advertise — but it keeps working until the object is deleted, so if a link does
start circulating, delete the old object too. An unguessable URL is the entire
paywall for a $39.99 download with no licence server, which is exactly why the
remedy has to be deleting the object rather than changing the link.

### How the sale actually flows

```
windows-app.html  --Buy for $39.99-->  Stripe Payment Link
                                              |
                                      post-payment redirect
                                              v
                              thank-you-<token>.html   (noindex, unlinked)
                                              |
                                     windows_app.delivery_url
                                              v
                                 your object storage, unguessable name
```

The delivery page is generated from the SKU and `stripe.delivery_salt`, so its
URL survives rebuilds. `build_pages.py` prints it on every run — that is the
value you paste into Stripe as the payment link's "after payment" redirect.

Protection is deliberately light, exactly as it is for the puzzle books: an
unguessable URL on a `noindex` page stops casual sharing and nothing more. Real
entitlement checks need a server; for a one-off download that trade is not worth
making. If it ever becomes a problem, Gumroad or Lemon Squeezy enforce
entitlements for a cut of the sale.

### Object storage with a custom domain

This is where the file should go — pick one, upload, paste the URL into
`site.json` under `windows_app.delivery_url`:

| Host | Free tier | Egress | Notes |
| --- | --- | --- | --- |
| **Cloudflare R2** | 10 GB storage | **free** | No bandwidth bill, ever. Attach a custom domain in the dashboard. The usual recommendation. |
| **Backblaze B2** | 10 GB storage | free via Cloudflare CDN | Long-standing Cloudflare Bandwidth Alliance partner. |
| **Bunny.net Storage** | paid, ~$0.01/GB | ~$0.01/GB | Cheap, fast, simple. Good if you want a CDN too. |
| **AWS S3 + CloudFront** | 12 months limited | ~$0.085/GB | Works, and will happily bill you if something goes viral. |

With R2, publishing a new version is:

```bash
rclone copy dist/installer/buttcrack-setup-1.2.0.exe r2:buttcrack-downloads/
```

Give the object a name nobody would guess — the unguessable URL *is* the
paywall:

```
buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe
```

then paste `https://downloads.yourdomain/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe`
into `site.json`. Only the post-payment page ever shows it.

If your bucket supports it, turn off directory listing and set a long
`Cache-Control`. You do not need signed URLs for a $39.99 download — but R2 and
S3 both offer them if you later decide you want links that expire.

### Selling it somewhere that enforces entitlements

The Stripe + unguessable-URL arrangement is light protection by design. If the
file starts circulating and you care, these host *and* police the download for
a cut of each sale, and you would drop the `delivery_url` plumbing entirely:

* **Gumroad** — ~10% + fees, handles VAT, gives buyers a library and a licence key API.
* **Lemon Squeezy** — merchant of record, so they handle sales tax worldwide.
* **itch.io** — a good fit for puzzle and CTF audiences; you set the revenue share.

### Serving it correctly

Whatever you use, check these three:

* **`Content-Type: application/octet-stream`** (or
  `application/vnd.microsoft.portable-executable`). Some hosts guess, and a
  `.exe` served as `text/html` arrives corrupt.
* **HTTPS, no redirect chain.** Browsers are increasingly hostile to executables
  that arrive over plain HTTP or after a redirect hop.
* **Publish the SHA-256** next to the link. `build.ps1` writes it to
  `dist/installer/*.sha256` for you, and the download page shows users the
  one-liner to check it:

  ```powershell
  Get-FileHash .\buttcrack-setup-1.2.0.exe -Algorithm SHA256
  ```

### Package managers, if you want them later

Not needed, but they are the other way people install Windows software without
touching a browser:

* **winget** — a manifest PR to `microsoft/winget-pkgs`.
* **Chocolatey** — a `.nuspec` package, same idea.
* **Scoop** — a JSON manifest in a bucket.

All three need a **publicly reachable** installer URL and its SHA-256, which is
precisely what a paid product does not have. They are listed here for the day
there is a free or trial build to put in them; submitting the paid installer
would publish it.

---

## Other platforms

`buttcrack.spec` is not Windows-specific. On macOS it produces the same pair of
binaries and can be extended with a `BUNDLE()` step to make `Buttcrack.app`
(which then wants notarisation, a separate $99/year exercise); on Linux the
usual target is a `.tar.gz` of `dist/Buttcrack/`, or an AppImage built from it.
Neither is wired up here because neither was asked for.

---

---

## Verifying the installer

`build.ps1` proves the *executables* work. `test-installer.ps1` proves the
*installer* does, which is a different program with a different failure mode: a
wizard can install perfectly and still leave a dead directory on the user's
`PATH` after an uninstall, or put a shortcut somewhere the script never checked.

```powershell
.\test-installer.ps1 -Installer ..\..\dist\installer\buttcrack-setup-1.2.0.exe
```

It installs silently into a temporary directory, then checks:

* every file the installer is meant to lay down, including both language model
  tables and all three web UI files;
* the Start-menu group, the desktop shortcut, and the per-user `PATH` entry;
* that the *installed* `buttcrack.exe` breaks a Caesar sample and returns the
  exact plaintext — the only way to catch a data file that did not travel;
* that the SQLite-backed `results` command runs, because the build used to
  exclude `sqlite3` from the bundle and both that command and the campaign panel
  in the window died on it;
* the full 142-check self-test, unless you pass `-SkipSelftest`;
* that a silent uninstall removes every file, both shortcuts and the `PATH`
  entry, and leaves no non-empty directory behind.

It touches two things outside a temp directory — the per-user `PATH` value and
the Start-menu and desktop shortcuts — because those are precisely what it is
testing. Both are undone by the uninstall it performs, and neither needs
administrator rights. Pass `-NoPathTask` to leave `PATH` alone.

The `installer` job in `.github/workflows/release.yml` runs this on
`windows-latest` for every push and pull request, so the wizard is exercised on
every change instead of on the day someone downloads it.

### What that job leaves behind, and for how long

The job uploads the installer, its `.sha256` and `INSTALLER-SHA256.json` as one
workflow artifact, and then — for any run triggered by a push or a pull request
— deletes it again in its last step. That is not tidiness for its own sake.

**A public repository's artifacts are public.** The rule above says the paid
`.exe` never goes in the repository and never goes on the site, because both are
public; a workflow artifact of a public repository belongs on that list. It
needs no account: `GET /repos/<owner>/<repo>/actions/artifacts` answers
anonymously and lists every artifact with its size, and
`GET .../actions/artifacts/<id>/zip` answers with a redirect to a signed
download URL. Anyone who knows the repository is called can be holding a copy of
the product a minute later. Thirty days of retention, refreshed by every push to
`main`, is a paid download sitting on a public shelf.

So a run that is verifying a commit keeps no copy past the checks that read it.
The copy you publish comes from a run you ask for:

```powershell
gh workflow run 'Release artifacts'          # or Actions -> Release artifacts -> Run workflow
gh run list --workflow 'Release artifacts' --limit 5
gh run download <run-id> --name buttcrack-installer-<version> --dir dist\installer
```

A deliberate run keeps its artifact for one day (`retention-days: 1`), which is
the window in which it is downloaded, checked against its own digest, and
uploaded to storage. If that window closes, dispatch another run: the build is
reproducible, and the digest that matters is the one of the file you actually
uploaded. `INSTALLER-SHA256.json` travels with the artifact, and the run's
`SHA-256 the installer` step echoes it into the log.

Because ordinary runs give their copy back, the newest run is usually *not* the
one to look in — ask what exists instead of reading runs one at a time:

```console
python scripts/fetch_installer.py --list
```

```
created           version        size  lapses           artifact
2026-10-13 05:00  1.2.1       15.6 MB  2026-11-12 05:00 11790265857
2026-10-12 23:57  1.2.0       15.6 MB  2026-11-11 23:57 11780675745

2 live. Fetch one with --version <version> or --artifact <id>.
```

Every name that comes back is a build that passed the install, exercise and
uninstall test, because the upload happens after it — so a live artifact is a
verified installer, and the list is also the honest answer to "what can somebody
download from this repository right now?". The same script fetches one, checks
the digest, and prints the three numbers `site.json` wants:

```console
python scripts/fetch_installer.py                       # newest, into dist/installer
python scripts/fetch_installer.py --version 1.2.0       # the version the page sells
python scripts/fetch_installer.py --artifact 11780675745
```

It uses the anonymous artifact API, so it needs no account and no `gh`; set
`GITHUB_TOKEN` only if a build is ever private. By hand, the same two steps are
the run's **Artifacts** section in the browser, or:

```powershell
gh run download <run-id> --name buttcrack-installer-<version> --dir dist\installer
```

Note that there is no per-artifact web address — `/actions/runs/<run>/artifacts/<id>`
does not exist, and a link built that way answers 404 however you are signed in.
The run page shows the artifact with its size and downloads it on click; that is
the only browser route.

The delete step never fails the build. A pull request from a fork runs with a
read-only token, so it cannot withdraw anything; when that happens the run says
so with a warning and the artifact lapses on its own after a day. It says
something either way — a notice naming the artifact it withdrew, or a warning
naming the one it could not — so whether a build of this repository is
downloadable at any moment can be answered from the API alone, without opening
a log or taking anyone's word for it.

The `checks` job is treated the same way, and for the same reason. Its `dist`
artifact is `Buttcrack/` frozen by PyInstaller — both executables and the
runtime they share — which is the application the wizard wraps, and the thing
the price actually buys: a copy that runs without Python. It is uploaded as a
build record and withdrawn the moment the checks are done. Rebuilding it is one
command locally, so nothing is lost but the public copy.

---

## Parallel solving on Windows

`buttcrack/search.py` spreads the stochastic searches — simple substitution,
Playfair, Bifid, Trifid and the M-94 wheel — across worker processes. It now
picks the cheapest start method the platform actually offers: `fork` where it
exists, where a worker inherits the loaded language model copy-on-write and costs
nothing measurable to start, and `spawn` everywhere else, Windows included.

Spawn is not free. Each worker re-imports the package and re-reads the n-gram
tables, roughly 0.25 s, paid once in parallel against a budget that defaults to
30 s. That is the difference between those attacks using one core on Windows and
using four, which is what they used to do: the pool was created with
`multiprocessing.get_context("fork")` unconditionally, that call raises on
Windows, and the solver quietly fell back to a serial loop.

Every worker callable is a top-level function and every payload is plain data —
text, integers, a seed, a language name — which is what makes them picklable and
therefore spawn-safe. `tests/test_search.py` forces the spawn context on Linux
and runs the real substitution worker through it, so the Windows path is covered
by the ordinary test suite rather than by a customer.

---

## Where the installed app keeps its data

The desktop window owns two files: the PK9 campaign ledger and the saved
assistant transcripts. Both live in `%LOCALAPPDATA%\Buttcrack` (on macOS,
`~/Library/Application Support/Buttcrack`; on Linux, `$XDG_DATA_HOME/buttcrack`).

They used to be relative paths — `kryptos\pk9-results.sqlite3` and
`%USERPROFILE%\buttcrack-assistant.jsonl`. From a checkout the first is
perfectly reasonable. Installed, it resolves against whatever directory the
shortcut launched the process in, which is not a directory anyone chose and
usually does not have a `kryptos` subdirectory; SQLite will not create a missing
parent, so the campaign panel showed "Campaign ledger unavailable" to everyone
who installed the program and to nobody who ran it from source.
`buttcrack/userdata.py` resolves both locations properly, and
`tests/test_userdata.py` reproduces the installed situation to keep it that way.

You can move either with `BUTTCRACK_DATA_DIR`, or point the campaign panel at one
particular ledger with `BUTTCRACK_PK9_LEDGER`.

An uninstall leaves that directory alone on purpose: it is the user's data, not
the program's, and deleting it would take their campaign results with it.
