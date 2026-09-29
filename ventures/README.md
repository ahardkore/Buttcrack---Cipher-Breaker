# Ventures

Revenue experiments built on top of `buttcrack`. Each one is designed to run
with near-zero ongoing input and zero hosting cost.

**Read this part first, because it is the part that matters.**

## What this can realistically earn

| Stream | Realistic year-1 range | Ceiling if it takes off |
| --- | --- | --- |
| Ad revenue on the solver site | $0–40/mo | $200–600/mo |
| GitHub Sponsors / Ko-fi | $0–15/mo | $50–150/mo |
| Puzzle packs (Gumroad/KDP) | $0–30/mo | $100–400/mo |

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

Generates a print-ready puzzle book: cover, solving instructions, 60–90 graded
puzzles, full solutions. Deterministic from a seed, so each seed is a different
volume you can sell separately.

```bash
python3 ventures/puzzle-packs/generate.py --puzzles 60 --seed 1
python3 ventures/puzzle-packs/generate.py --puzzles 90 --seed 42 --title "Cryptograms Volume Two"
```

Open the HTML in a browser, Print → Save as PDF, upload to Gumroad (free to
list) or Amazon KDP (free to publish, they print on demand). Price at $4–7.
Quotations are short fragments from authors who died before 1956, kept
deliberately conservative so the book is sellable without licensing worries.

### 3. GitHub Sponsors

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
3. **Submit to Google.** [Search Console](https://search.google.com/search-console)
   → add the site → submit `sitemap.xml`. Nothing ranks until Google knows the
   pages exist. This is the single highest-value step in the whole list.
4. **Add analytics** (optional, free): create a
   [Plausible](https://plausible.io) or Cloudflare Web Analytics property and
   put the domain in `site.json`. You cannot improve what you cannot measure.
5. **Apply to AdSense** once the site has a little traffic — applying with zero
   visitors usually gets rejected. Put the client and slot IDs in `site.json`.
   Note that AdSense requires a payment address and pays out at $100.
6. **Open a Gumroad account**, export a puzzle pack to PDF, list it at $5.
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
