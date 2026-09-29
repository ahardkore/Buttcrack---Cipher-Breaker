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
the site is built as six separate content pages rather than one tool — and why
the weekly checklist below is mostly about content and links, not code.

## What's here

### 1. `cipher-solver-web/` — the free browser solver

A complete static site. The full cipher-breaking engine runs client-side in a
Web Worker, so there is no server, no API bill, and nothing to maintain. It can
sit on GitHub Pages indefinitely at a cost of exactly zero.

Six pages, each targeting a different search intent: general solver, Caesar,
Vigenère, substitution, Morse, CTF crypto. Each has genuine explanatory content
(AdSense rejects thin pages, and so does Google's ranking).

Accuracy is verified by `test.js` — 19 end-to-end cases covering every cipher
and several layered combinations. It passes 19/19, and CI runs it on every
deploy so a bad change cannot ship.

```bash
python3 ventures/cipher-solver-web/build_model.py   # compile the language model
python3 ventures/cipher-solver-web/build_pages.py   # generate the HTML
node    ventures/cipher-solver-web/test.js          # verify accuracy
python3 -m http.server 8000 -d ventures/cipher-solver-web   # preview
```

Monetisation is switched on entirely from `site.json` — fill in the AdSense and
Ko-fi fields, push, and the workflow rebuilds the pages with real ad units. No
code changes.

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
6. **Wire up Stripe** (you have the account, so this is the short version):
   1. Run `python3 ventures/cipher-solver-web/build_pages.py`. It prints a
      delivery URL per product — copy them.
   2. Change `delivery_salt` in `site.json` to anything you like. Do this
      **before** your first sale, then leave it alone forever.
   3. In Stripe → Product catalogue, create a product per volume, priced to
      match `site.json` ($5 and $7 as shipped).
   4. For each, create a **Payment Link**. Under "After payment", choose
      *Don't show confirmation page* → **Redirect to your website**, and paste
      that product's delivery URL.
   5. Paste each Payment Link URL into the matching `payment_link` field in
      `site.json`, and push. The Buy buttons go live on deploy.
   6. Optional: make one more Payment Link with a customer-chosen amount and
      put it in `tip_jar_url`. It appears as "Leave a tip" on every page.
   7. Stripe needs your bank details before it will pay out — do that in the
      Stripe dashboard, not here.

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
