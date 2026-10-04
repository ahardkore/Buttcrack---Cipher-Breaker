"""Put Stripe Payment Link URLs into site.json and rebuild the store.

Hand-editing JSON is where the typos come from, so paste the URLs here
instead. Every link is validated before it is written (https, live mode, a
real payment link rather than a dashboard URL), the pages are regenerated,
and the post-payment redirect URL for each product is printed so you can
check it against what you set in Stripe.

    python3 ventures/cipher-solver-web/set_payment_links.py \\
        --vol1 https://buy.stripe.com/xxxxxxxx \\
        --vol2 https://buy.stripe.com/yyyyyyyy \\
        --tip  https://buy.stripe.com/zzzzzzzz

Any subset works — pass only what you have, run it again later for the rest.
Use --show to print the current state and the redirect URLs without changing
anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_JSON = HERE / "site.json"

sys.path.insert(0, str(HERE))


def delivery_url(cfg: dict, sku: str) -> str:
    """The URL Stripe must redirect to after a successful payment."""
    salt = cfg["stripe"].get("delivery_salt", "")
    token = hashlib.sha256(f"{sku}:{salt}".encode()).hexdigest()[:20]
    return f"{cfg['base_url']}/thank-you-{token}.html"


def report(cfg: dict) -> None:
    print("\nProducts")
    for product in cfg["stripe"]["products"]:
        link = product.get("payment_link") or "— not set —"
        state = "LIVE" if product.get("payment_link") else "no checkout"
        print(f"  {product['sku']:5} {product['price']:>3}  [{state}]")
        print(f"        payment link : {link}")
        print(f"        redirect to  : {delivery_url(cfg, product['sku'])}")
    tip = cfg["stripe"].get("tip_jar_url") or "— not set —"
    print(f"\n  tip jar: {tip}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vol1", help="Payment Link URL for volume one")
    parser.add_argument("--vol2", help="Payment Link URL for volume two")
    parser.add_argument("--tip", help="Payment Link URL for the tip jar")
    parser.add_argument("--show", action="store_true", help="print current state and exit")
    parser.add_argument("--no-build", action="store_true", help="write site.json but do not rebuild")
    args = parser.parse_args(argv)

    cfg = json.loads(SITE_JSON.read_text())

    if args.show or not any((args.vol1, args.vol2, args.tip)):
        report(cfg)
        if not args.show:
            print("\nNothing to set. Pass --vol1/--vol2/--tip with the URLs from Stripe.")
        return 0

    # Validate everything before writing anything: a half-applied config that
    # fails the next build is worse than a clean refusal.
    from build_pages import payment_url

    updates = {"vol1": args.vol1, "vol2": args.vol2}
    checked = {sku: payment_url(url, f"--{sku}") for sku, url in updates.items() if url is not None}
    tip = payment_url(args.tip, "--tip") if args.tip is not None else None

    known = {p["sku"] for p in cfg["stripe"]["products"]}
    for sku in checked:
        if sku not in known:
            raise SystemExit(f"no product with sku {sku!r} in site.json (have: {sorted(known)})")

    for product in cfg["stripe"]["products"]:
        if product["sku"] in checked:
            product["payment_link"] = checked[product["sku"]]
            print(f"set {product['sku']} payment_link")
    if tip is not None:
        cfg["stripe"]["tip_jar_url"] = tip
        print("set tip_jar_url")

    SITE_JSON.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {SITE_JSON.relative_to(SITE_JSON.parent.parent.parent)}")

    if not args.no_build:
        import importlib

        import build_pages

        # build_pages reads site.json once, at import time — and it was already
        # imported above for payment_url, i.e. before the write. Without this
        # reload the rebuild would regenerate the pages from the *old* config
        # and quietly ship a store with no buy buttons.
        importlib.reload(build_pages)
        print()
        build_pages.main()

    report(cfg)
    print("\nCheck each 'redirect to' URL matches the after-payment redirect set in Stripe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
