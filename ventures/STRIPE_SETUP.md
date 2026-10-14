# Turning on payments — the exact steps

Everything on the storefront is ready except three URLs that only your Stripe
account can create. This is the whole job; budget fifteen minutes.

Nothing here needs an API key, a webhook, a server or a database. Stripe hosts
the checkout, Stripe emails the receipt, and the customer lands back on a
delivery page on this site that hands them the PDF.

---

## Before you start: the delivery URLs are now final

Each product has a delivery page whose filename is derived from the product SKU
and `stripe.delivery_salt` in `site.json`. The salt was rotated off its shipped
placeholder on 2026-09-29, so these URLs are settled. **Do not change
`delivery_salt` again** — every URL below would change with it and anyone who
had already bought a book would lose their download link.

| Product | Price | Post-payment redirect URL |
| ------- | ----- | ------------------------- |
| Volume One (60 puzzles) | $5 | `https://ciphersolverpro.com/thank-you-830991499d0d70f90abd.html` |
| Volume Two (90 puzzles) | $7 | `https://ciphersolverpro.com/thank-you-bc1474305b0ba8208121.html` |
| Buttcrack for Windows (installer) | $39.99 | `https://ciphersolverpro.com/thank-you-5e5e0b57e21b06f4e762.html` |

Print them again at any time:

```bash
python3 ventures/cipher-solver-web/set_payment_links.py --show
```

---

## 1. Make sure you are not in test mode

Top of the Stripe dashboard, the **Test mode** toggle must be **off**. A
test-mode link takes fake cards, completes checkout perfectly and pays you
nothing. The build refuses a `buy.stripe.com/test_...` URL for exactly this
reason, but it is easier to just start in live mode.

Live mode needs your business and bank details filled in; Stripe will prompt.

## 2. Create the two products

**Product catalogue → Add product**, once per book:

| Field | Volume One | Volume Two |
| ----- | ---------- | ---------- |
| Name | The Cryptogram Collection, Volume One | The Cryptogram Collection, Volume Two |
| Description | 60 hand-graded cryptograms, easy to hard, with a full solutions section. | 90 more puzzles at a step up in difficulty, with Caesar rotations mixed in. |
| Price | 5.00 USD | 7.00 USD |
| Billing | **One-off** (not recurring) | **One-off** |

Leave "tax behaviour" at its default unless your accountant says otherwise.

## 3. Create a Payment Link for each product

On the product page: **Create payment link** (or **Payment links → New**).

1. Product: the one you just made. Quantity: fixed at 1.
2. **After payment** → choose **"Don't show confirmation page"** →
   **Redirect customers to your website**, and paste that product's URL from
   the table above. This is the step that actually delivers the book — without
   it the customer pays and receives nothing.
3. Options worth turning on: **collect customer email** (it is your only
   record of who bought what) and Apple Pay / Google Pay if offered.
4. Create, then copy the link. It looks like `https://buy.stripe.com/aEU5kC...`.

Do it for both volumes.

### 3b. The Windows app — same redirect, easier to miss

The $39.99 desktop build already has its Payment Link in `site.json`
(`windows_app.payment_link`), so it is tempting to skip this step. Do not: the
link existing and the link *delivering* are two separate settings, and the
second one lives only in Stripe.

Open that link in the dashboard and confirm **After payment** is set to
**"Don't show confirmation page" → Redirect customers to your website**, with

```
https://ciphersolverpro.com/thank-you-5e5e0b57e21b06f4e762.html
```

Left on Stripe's default confirmation page, the buyer pays, sees a generic
"thanks, we've emailed your receipt", and gets no download button — a completed
sale with nothing delivered, which is indistinguishable from a working one in
the dashboard. Print the current value at any time with:

```bash
python3 ventures/cipher-solver-web/set_payment_links.py --show
```

Unlike the books, the Windows app's redirect cannot be checked by looking at
the site: the delivery page is `noindex` and unlinked by design.

## 4. Create the tip jar link

**Payment links → New → Customers choose what to pay**.

- Suggested amount: 3.00 USD, minimum 1.00.
- Name it something like "Tip the cipher solver".
- After payment: the default Stripe confirmation page is fine — there is
  nothing to deliver.

Copy that link too.

## 5. Paste all three in, in one command

```bash
python3 ventures/cipher-solver-web/set_payment_links.py \
    --vol1   https://buy.stripe.com/XXXXXXXX \
    --vol2   https://buy.stripe.com/YYYYYYYY \
    --winapp https://buy.stripe.com/WWWWWWWW \
    --tip    https://buy.stripe.com/ZZZZZZZZ
```

It validates each URL, writes `site.json`, rebuilds the pages, and prints the
redirect URL for each product so you can confirm it matches what you set in
Stripe. Partial runs are fine — pass only the flags you have.

The build refuses, with an explanation, if a URL is a test-mode link, a
`dashboard.stripe.com` editing URL (the common copy-paste mistake), plain
`http`, or not a URL at all.

## 6. Preview, then ship

```bash
python3 scripts/build_site.py --out _site
python3 -m http.server 8000 -d _site     # visit /downloads.html
git add -A && git commit -m "Activate Stripe payment links" && git push
```

Pushing to `main` triggers `.github/workflows/deploy-site.yml`, which rebuilds
and deploys. Give it a minute, then check the live store page.

## 7. Buy your own book

Use a real card for the $5 volume. Confirm that:

- checkout completes and Stripe emails a receipt,
- you land on the delivery page and the PDF downloads,
- the payment appears in the Stripe dashboard.

Then do the same for the $39.99 Windows app, which is the purchase that most
needs it: it is the only product whose delivery page nothing else can reach, and
the only one where "the button is there" and "the button works" come apart. On
that one also confirm the file downloads rather than opening an error page, and
that its SHA-256 matches `windows_app.sha256` in `site.json`:

```powershell
certutil -hashfile buttcrack-setup-1.2.1-347eb70aac291eec.exe SHA256
```

Then refund yourself from the dashboard (Stripe keeps nothing on a refunded
payment within 90 days on most accounts). This is the only test that proves the
redirect is wired correctly, and it takes two minutes.

---

## Optional: embedded Buy Buttons

To keep checkout on the page instead of sending visitors to Stripe:

1. **Payment links → your link → Buy button**, create one, copy its
   `buy_button_id`.
2. Put your **publishable** key (`pk_live_...`) in `stripe.publishable_key` in
   `site.json`, and the id in that product's `buy_button_id`.

Publishable keys are designed to be public and are safe in committed HTML. A
secret key (`sk_live_...`) is not, and the build hard-fails if one appears in
`site.json`. If you ever paste one by accident, rotate it in the dashboard
immediately — committing it to a public repo is a compromise even if you delete
it in the next commit.

## What happens after a sale

Delivery is a content-hashed PDF on a `noindex` page whose URL is unguessable
but shareable. That is deliberate: it stops casual link-sharing and nothing
more. For a five dollar puzzle book, the alternative — a licensing server with
accounts and expiring tokens — costs more to run than the books earn. If piracy
ever becomes a real problem, move the products to Gumroad rather than build
entitlement checks here.

## Troubleshooting

| Symptom | Cause |
| ------- | ----- |
| Store still says "Payment link not configured yet" | `site.json` was edited but the pages were not rebuilt, or the deploy has not finished. |
| Customer pays, sees Stripe's generic thank-you, gets no book | The link's "After payment" redirect is unset. Fix it on the link in Stripe; no rebuild needed. |
| Redirect goes to a 404 | The redirect URL does not match the table above — usually an old one from before the salt was rotated. |
| Money never arrives | Test-mode link. Recreate it in live mode. |
| Windows buyer pays and never sees a download button | The `winapp` link's "After payment" redirect is unset — see 3b. Fix it in Stripe; no rebuild needed. |
| Windows buyer reaches the delivery page but the download fails | `windows_app.delivery_url` no longer resolves. Check the object still exists and that the bucket's public access is still on for the hostname in that URL; if it is an `r2.dev` address it may also be rate-limited or ISP-blocked, which is why the build warns about it. |
| Delivery page says the link "is being sent by email" instead of showing a button | `windows_app.delivery_url` is empty, so the installer was never published. Run the **Publish installer to storage** workflow and commit the `site.json` diff it prints. |

The two symptoms above that end in a *successful* payment are the expensive
ones, because Stripe reports them as ordinary completed sales. After changing
anything in this table's neighbourhood, buy the product yourself once — step 7 —
rather than reasoning about it.
