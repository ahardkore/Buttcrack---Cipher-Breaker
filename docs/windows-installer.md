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
  Buttcrack/                     the application directory
    Buttcrack.exe                windowed  -- the desktop app
    buttcrack.exe                console   -- the CLI
    _internal/                   Python runtime, the six language models, the web UI
  installer/
    buttcrack-setup-1.1.0.exe    ← this is the thing you publish
    buttcrack-setup-1.1.0.exe.sha256
```

Two executables, one shared runtime:

| | `Buttcrack.exe` | `buttcrack.exe` |
| --- | --- | --- |
| Start menu / desktop shortcut | yes | no |
| Console window | no | yes, it *is* the console |
| What it does | starts the local server on `127.0.0.1`, opens your browser, sits in the tray | the full CLI from the README |
| Equivalent to | `buttcrack app` | `buttcrack` |

They share one copy of Python and one copy of the 1.8 MB of n-gram tables, so
shipping both costs almost nothing over shipping either.

### What the user sees

1. Downloads `buttcrack-setup-1.1.0.exe`.
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
rclone copy dist/installer/buttcrack-setup-1.1.0.exe r2:buttcrack-downloads/
```

Give the object a name nobody would guess — the unguessable URL *is* the
paywall:

```
buttcrack-setup-1.1.0-7f3a9c2e51b04d88.exe
```

then paste `https://downloads.yourdomain/buttcrack-setup-1.1.0-7f3a9c2e51b04d88.exe`
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
  Get-FileHash .\buttcrack-setup-1.1.0.exe -Algorithm SHA256
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

## Known limitation on Windows

`buttcrack/search.py` parallelises its stochastic searches with
`multiprocessing.get_context("fork")`, and `fork` does not exist on Windows, so
the call raises and the solver falls back to a serial loop. In practice: the
hill-climbing attacks (simple substitution, Playfair, bifid, the M-94 wheel)
run on one core on Windows and benefit from a larger `--budget`. Exhaustive and
analytic attacks — Caesar, affine, Vigenère, XOR, every encoding — are
unaffected.

This is not something the installer introduced; running from a source checkout
on Windows behaves the same way. Fixing it means making the worker callables
picklable and using the `spawn` context, which is a change to the search
engine, not to the packaging.
