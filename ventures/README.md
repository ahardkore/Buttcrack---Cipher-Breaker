# Ventures

Revenue experiments built on top of `buttcrack`. Each one is designed to run
with near-zero ongoing input and zero hosting cost.

**Read this part first, because it is the part that matters.**

## What this can realistically earn

| Stream | Realistic year-1 range | Ceiling if it takes off |
| --- | --- | --- |
| Ad revenue on the solver site | $0–40/mo | $200–600/mo |
| GitHub Sponsors / Ko-fi | $0–15/mo | $50–150/mo |
| Puzzle books (Stripe/Gumroad/KDP) | $0–30/mo | $100–400/mo |

Nobody should plan their life around the right-hand column. The honest
expectation is that this makes somewhere between nothing and a couple of
hundred dollars a month, and that it takes six to twelve months to get there
because search traffic accumulates slowly.

**This will not make you financially independent.** No zero-capital,
zero-maintenance asset does, and anything claiming otherwise is selling you
something. What these are: real assets that cost nothing to run, compound
slowly with traffic, and might eventually cover a bill or two.

The one thing that genuinely changes the numbers is traffic, and traffic comes
from the site ranking for searches like "vigenere cipher solver". That is why
the site is built as sixty separate content pages rather than one tool — and why
the weekly checklist below is mostly about content and links, not code.

## What's here

### 1. `cipher-solver-web/` — the free browser solver and cipher wiki

A complete static site. The full cipher-breaking engine runs client-side in a
Web Worker, so there is no server, no API bill, and nothing to maintain. It can
sit on GitHub Pages indefinitely at a cost of exactly zero.

Two layers of content, each targeting a different search intent:

* **Tool pages** — general solver, Caesar decoder, Vigenère solver,
  substitution solver, Morse translator, CTF crypto solver, and the
  puzzle-book storefront.
* **The cipher wiki** — a Wikipedia-style encyclopedia with one article per
  cipher in the registry (all fifty), a main page with featured-article and
  "did you know" rotation, a left navigation rail with live search over every
  article, infoboxes and tables of contents generated from the solver's own
  cipher registry, and three long-form history features. The facts on every
  cipher page — family, key type, keyspace, minimum text — are generated at
  build time from the registry, and each worked example is produced by
  actually running the cipher, so a page cannot quietly disagree with the tool
  it documents. `build_pages.py` fails the build if any cipher lacks a page,
  any page is unlinked, or any internal link is broken.

Each page has genuine explanatory content (AdSense rejects thin pages, and so
does Google's ranking).

Accuracy is verified by `test.js` — 30 end-to-end cases covering every cipher
family (including the periodic family: Beaufort, Variant Beaufort, Porta,
Gronsfeld, Trithemius and autokey) and several layered combinations. It passes
30/30, and CI runs it on every deploy so a bad change cannot ship.

```bash
python3 ventures/cipher-solver-web/build_model.py   # compile the language model
python3 ventures/cipher-solver-web/build_pages.py   # generate the HTML
node    ventures/cipher-solver-web/test.js          # verify accuracy
python3 scripts/build_site.py --out _site           # assemble the full site
python3 scripts/audit_site.py _site --strict        # check the assembled output
python3 -m http.server 8000 -d _site                # preview exactly what deploys
```

#### Auditing the output

`test.js` proves the solver still solves; it says nothing about the sixty-odd
pages wrapped around it. Because those pages are generated, one wrong value in
a template is one wrong value on every page at once, and the build is green
either way. `scripts/audit_site.py` reads the *assembled* tree and fails on:

* internal links and `#anchors` that point at something which is not there;
* a canonical URL that does not match the page's own path under `base_url`,
  or a missing title, description, viewport or `lang` (pages marked
  `noindex` — the 404 and the Stripe delivery pages — are exempt by design);
* duplicate titles or descriptions, and ones long enough to be truncated;
* no `<h1>`, more than one, or a skipped heading level;
* `<img>` without `alt`, form controls with no label and no `aria-label`,
  duplicate `id`s, unclosed elements, invalid JSON-LD;
* sitemap entries that are not in the built tree, indexable pages missing
  from the sitemap, a `robots.txt` that does not point at it, orphan pages.

Both `ci.yml` (on every pull request) and `deploy-site.yml` (before the upload)
run it with `--strict`, so warnings stop the deploy too. CI additionally
rebuilds the pages and fails if the committed HTML differs from what
`build_pages.py` now produces — stale generated output cannot reach the site.

#### One site, two halves

The repository has two web surfaces and publishes them as **one** site.
`scripts/build_site.py` assembles the tree that GitHub Pages serves:

| URL          | Source                       | What it is                                   |
| ------------ | ---------------------------- | -------------------------------------------- |
| `/`          | `ventures/cipher-solver-web` | Solver, cipher wiki, puzzle-book storefront   |
| `/kryptos/`  | `kryptos-app`                | Kryptos research explorer                     |

They link to each other: the solver's nav has a **Kryptos** pill, and the
explorer has a bar back to the solver. `.github/workflows/deploy-site.yml` is
the only Pages workflow — there used to be a second one uploading `kryptos-app`
by itself, and because both wrote the same `pages` deployment, whichever
finished last erased the other's site.

Monetisation is switched on entirely from `site.json` — fill in the AdSense and
Ko-fi fields, push, and the workflow rebuilds the pages with real ad units. No
code changes.

#### AdSense

`adsense_client` is the only required field, and it puts Google's loader
snippet in the `<head>` of every page:

```html
<script async crossorigin="anonymous"
  src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-…"></script>
```

The 67 solver pages are generated, so `build_pages.adsense_head()` writes it
into each one. The Kryptos explorer is hand-written, so
`scripts/build_site.py` injects the identical tag at assembly time, reading
the same `site.json` — the publisher ID is never written down twice. Both are
pinned by `TestAdSense` in `tests/test_wiki.py`.

The three `thank-you-*.html` delivery pages are deliberately left without it.
They are `noindex`, reachable only after a Stripe payment, and consist of a
download button; "Google-served ads on screens without publisher content" is
a policy violation, so thin pages are the ones to keep ads off.

`adsense_slot` is separate and optional:

| `adsense_client` | `adsense_slot` | What the pages get                             |
| ---------------- | -------------- | ---------------------------------------------- |
| empty            | —              | an inert dashed placeholder (local reminder)    |
| set              | empty          | loader only — Auto ads places units itself      |
| set              | set            | loader plus an explicit responsive `<ins>` unit |

`ads.txt` is generated too, but **only on a custom domain**. It is read from
the domain root and nowhere else, so on a `github.io` project path the file
would sit at a URL no crawler looks at; `write_ads_txt()` writes nothing in
that case rather than create false confidence. On `ciphersolverpro.com` it
publishes `google.com, pub-…, DIRECT, f08c47fec0942fa0`.

This matters because **AdSense approves top-level domains, not subdomains**.
`*.github.io` belongs to GitHub, so an application naming a project page is
normally rejected on ownership grounds regardless of content quality — which
is why the site moved to its own domain.

### The custom domain

The site is served from **ciphersolverpro.com**, registered at Wix, hosted on
GitHub Pages. `base_url` in `site.json` is the single source of truth: the
canonicals, the sitemap, `robots.txt`, the Stripe redirect URLs, `ads.txt` and
the `CNAME` file are all derived from it. Change it there and rebuild; do not
hand-edit any of them.

**The CNAME file is not optional, and this is the trap.** A custom domain set
in Settings → Pages is stored against the *repository*, but a GitHub Actions
deploy publishes exactly what is in the *artifact*. An artifact with no CNAME
file **clears** the stored domain — the site reverts to github.io, the deploy
reports success, and nothing anywhere says what happened. So
`scripts/build_site.py` writes `_site/CNAME` from `base_url` on every build,
and `scripts/audit_site.py` fails the deploy if it is missing or disagrees.
A `github.io` `base_url` correctly produces no file at all.

DNS lives at Wix, which does **not** permit external nameservers for domains
it registered — everything is done with records in Wix's own editor
(Domains → the domain → Domain Actions → Manage DNS Records):

| Type  | Host  | Value             |
| ----- | ----- | ----------------- |
| A     | @     | `185.199.108.153` |
| A     | @     | `185.199.109.153` |
| A     | @     | `185.199.110.153` |
| A     | @     | `185.199.111.153` |
| CNAME | `www` | `ahardkore.github.io` |

All four A records are needed: they are GitHub's published Pages addresses,
and the redundancy is the point. The `www` CNAME targets the *user* page
(`ahardkore.github.io`, no repository path) — GitHub works out which
repository to serve from the domain itself. Delete any pre-existing A or CNAME
record pointing at Wix's own servers (`185.230.63.x`, `*.wixdns.net`) or the
domain will keep resolving to Wix.

Note that Wix cannot do plain URL forwarding, and does not support DNSSEC or
a proxy in front of these records — leave both off.

### 2. `puzzle-packs/` — sellable cryptogram books

Generates a print-ready puzzle book: cover, solving instructions, graded
puzzles with answer blanks, full solutions. Deterministic from a seed, so each
seed is a different volume you can sell separately.

```bash
python3 ventures/puzzle-packs/build_pdf.py  --puzzles 60 --seed 1   # PDF, direct
python3 ventures/puzzle-packs/generate.py   --puzzles 60 --seed 1   # HTML edition
```

`build_pdf.py` writes a real US Letter PDF with no dependencies and no browser
— `pdf.py` is a small PDF writer using only the standard library and the
base-14 fonts, so books can be produced in CI. That is what lets the storefront
below rebuild its products automatically on every deploy.

Quotations are short fragments from authors who died before 1956, kept
deliberately conservative so the book is sellable without licensing worries.

### 3. Stripe storefront — `downloads.html`

A store page and a per-product delivery page, both generated. No server, no
webhook, no database: Stripe Payment Links host the checkout, and Stripe's
post-payment redirect sends the buyer to a delivery page carrying the download.

Protection is deliberately light. Download URLs are content-hashed and delivery
pages are `noindex`, which stops casual sharing of a tidy link — it is not
entitlement enforcement. Running real licence checks means running a server,
which costs money and attention; for a $5 puzzle book that trade is not worth
making. If piracy ever becomes a real problem, move the products to Gumroad,
which enforces entitlements for a cut of the sale.

The delivery URL is derived from the SKU and a fixed salt, never from file
contents, so it survives rebuilds. **Change `delivery_salt` in `site.json` once,
before your first sale, then never again** — changing it later breaks the
download link for everyone who already bought.

A free ten-puzzle sampler is generated alongside the paid volumes. It exists to
convert visitors who would never click a Buy button, and to give you something
to link when someone asks for a recommendation.

### 3b. The Windows desktop app — `windows-app.html`

Same machinery, one important difference: **the installer is never served from
this site.**

The puzzle-book PDFs are regenerated on every deploy, so they can live in
`files/` and ship with the site. The Windows installer cannot be — it needs
Windows, PyInstaller and Inno Setup to build — and, more to the point, this
repository and the site it publishes are both public. A paid `.exe` sitting in
either one is a paid `.exe` anybody can take. `scripts/build_site.py` fails the
deploy if it finds an executable in the assembled tree, so this cannot happen by
accident.

The installer therefore lives on storage you control and the site only ever
holds its URL:

1. Build it: `packaging\windows\build.ps1` (see
   [`docs/windows-installer.md`](../docs/windows-installer.md)). It prints a
   SHA-256.
2. Upload `buttcrack-setup-<version>.exe` somewhere private-by-obscurity and
   cheap — **Cloudflare R2** is the usual answer: 10 GB free, no egress charge
   ever, custom domain in two clicks. Give the file an unguessable name.
3. Put that URL in `site.json` under `windows_app.delivery_url`, along with the
   `version`, `size` and `sha256` the build printed.
4. In Stripe, set the payment link's post-payment redirect to the `winapp`
   delivery URL that `build_pages.py` prints.

Until step 3 is done the build prints a loud warning, and the delivery page
tells buyers their download is coming by email rather than showing them a dead
button. The sales page works either way.

### 4. GitHub Sponsors

`.github/FUNDING.yml` puts a Sponsor button on the repo. This earns roughly
nothing until the project has visible users, which is exactly why the free tool
comes first: the site drives people to the repo, the repo converts a tiny
fraction of them.

## Your setup, once (about an hour)

Do these in order. Stop after step 3 if you want — the site works and is live at
that point; the rest is monetisation.

1. **Turn on Pages.** Repo → Settings → Pages → Source: **GitHub Actions**.
   Merge this branch to `main` and the site deploys itself. Confirm it loads and
   the sample buttons solve.
2. **Set the real URL.** If the deployed URL differs from the `base_url` in
   `ventures/cipher-solver-web/site.json`, fix it there and push. Canonical tags
   and the sitemap depend on it.
3. **Verify ownership, then submit to Google.**
   [Search Console](https://search.google.com/search-console) → add a
   **URL prefix** property for your `base_url` → choose the **HTML tag** method
   → copy the token out of the snippet it shows you, and paste it into
   `google_site_verification` in `site.json`. Push. Wait for the deploy to go
   green, then press **Verify**.

   Paste the bare token or the whole `<meta …>` tag — either is accepted. Put it
   in `site.json`, **not** into the HTML by hand: `build_pages.py` regenerates
   every page on each deploy, so a hand-edited tag disappears on the next build
   and silently un-verifies the property. Leave the token in place permanently;
   removing it makes Google drop ownership.

   Prefer Google's *HTML file* method, or verifying Bing at the same time? Use
   `verification_files` and the `verification` map in `site.json` — both are
   written into the site on every build. (The *DNS TXT* method skips the repo
   entirely, but needs a custom domain, which `github.io` is not.)

   Then submit `sitemap.xml`. Verification on its own does nothing for indexing;
   the sitemap is what tells Google the pages exist. This is the
   single highest-value step in the whole list.
4. **Add analytics** (optional, free): create a
   [Plausible](https://plausible.io) or Cloudflare Web Analytics property and
   put the domain in `site.json`. You cannot improve what you cannot measure.
5. **Apply to AdSense** once the site has a little traffic — applying with zero
   visitors usually gets rejected. Put the client and slot IDs in `site.json`.
   Note that AdSense requires a payment address and pays out at $100.
6. **Wire up Stripe.** Full click-path, with this repo's delivery URLs already
   filled in: **[`STRIPE_SETUP.md`](STRIPE_SETUP.md)**. The short version:
   1. `delivery_salt` has already been rotated off its placeholder, so the
      delivery URLs are final. Never change it again — it would break the
      download link of everyone who has already bought a book.
   2. In Stripe (live mode, not test), create a product per volume priced to
      match `site.json` ($5 and $7 as shipped), plus a customer-chooses-amount
      link for the tip jar.
   3. For each product link, set "After payment" → *Don't show confirmation
      page* → **Redirect to your website**, pasting that product's delivery
      URL from `set_payment_links.py --show`.
   4. Paste all three URLs in at once, which validates them, writes
      `site.json` and rebuilds:

      ```bash
      python3 ventures/cipher-solver-web/set_payment_links.py \
          --vol1 https://buy.stripe.com/… --vol2 https://buy.stripe.com/… \
          --tip  https://buy.stripe.com/…
      ```
   5. Push. The Buy buttons go live on deploy. Then buy your own $5 book with a
      real card to prove the redirect works, and refund yourself.
   6. Stripe needs your bank details before it will pay out — do that in the
      Stripe dashboard, not here.

   Bad URLs fail the build rather than shipping a dead button: test-mode links,
   `dashboard.stripe.com` editing URLs, `http`, and a `buy_button_id` with no
   publishable key are each refused with an explanation.

**On API keys.** Nothing in this setup requires one. Payment Links are
self-contained URLs, which means there is no credential to leak, rotate or
accidentally commit — that is the main reason the storefront is built this way.

The one optional exception is Stripe's embedded Buy Button, which keeps checkout
on your page rather than sending the visitor to Stripe. It needs a
**publishable** key (`pk_live_…`), which is explicitly designed to be readable in
public HTML. Put it in `publishable_key` in `site.json` along with each
product's `buy_button_id` and the store page will embed the button instead of a
plain link.

A **secret** key (`sk_live_…`, `rk_live_…`) must never appear in this repo, in a
config file, or in a chat message — it grants full control of your Stripe
account, including moving money. `build_pages.py` aborts the build if it finds
one in `publishable_key`, but do not rely on that: if a secret key is ever
exposed, rotate it immediately at Stripe → Developers → API keys.
7. **Enable GitHub Sponsors** at github.com/sponsors.

## Your weekly hour

This is the whole job. It is mostly not coding.

- **20 min — answer one question somewhere.** Reddit r/codes, r/cryptography,
  r/puzzles, Stack Exchange Puzzling. Someone posts unknown ciphertext daily.
  Solve it, explain how, link the tool if genuinely relevant. Never spam; a
  helpful answer that happens to link a free tool is welcome, a drive-by link is
  not. This is the main traffic source in month one.
- **20 min — add or extend one page.** Another cipher page (Playfair, rail
  fence, book cipher, A1Z26), or deepen an existing one. More pages, more search
  surface.
- **10 min — check Search Console.** Which queries are you nearly ranking for?
  Write about those specifically.
- **10 min — everything else.** Ship a puzzle pack volume, reply to an issue,
  post a solved puzzle.

Skipping weeks does not break anything. The site keeps serving and keeps earning
whatever it earns; it just stops growing.

## Ideas worth trying later

- A paid API for the solver. Real demand exists, but it needs a server, which
  needs a card and a Stripe account, and it stops being zero-maintenance.
- Browser extension — "solve selected text" — distributed free on the Chrome
  and Firefox stores, linking back to the site.
- A daily cryptogram page with a shareable result, since daily puzzles retain
  visitors far better than one-off tools.
