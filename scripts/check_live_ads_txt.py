"""Check what the *live* domain actually serves at /ads.txt.

AdSense reports "no ads.txt file was found" against the last time its crawler
visited, not against the current state of the site. So after a deploy that
adds or fixes the file, the warning stays up for a day or two and there is no
way to tell, from inside the AdSense console, whether the problem is fixed and
stale or still real.

``scripts/audit_site.py`` already fails the deploy when ads.txt is missing from
the *artifact*. This script closes the other half of the loop: it fetches the
file over the network, exactly as the crawler does, and checks that

* the apex host serves it with a 200,
* ``www`` serves it too (AdSense may hold the property under either name),
* the body authorises the publisher ID configured in ``site.json``,
* nothing serves an HTML 404 page with a 200 status, which is the usual way a
  static host "has" a file it does not have.

Usage::

    python3 scripts/check_live_ads_txt.py
    python3 scripts/check_live_ads_txt.py --base-url http://localhost:8000

Exit status is 0 when the live site is correct, 1 when it is not — so it can
be run from a scheduled job as well as by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE_JSON = ROOT / "ventures" / "cipher-solver-web" / "site.json"

#: A crawler-ish identity. Some hosts and CDNs answer a bare urllib request
#: with a challenge page, which would look like a broken ads.txt.
USER_AGENT = "buttcrack-ads-txt-check/1.0 (+https://ciphersolverpro.com)"

TIMEOUT = 20


def config() -> dict:
    if not SITE_JSON.is_file():
        return {}
    return json.loads(SITE_JSON.read_text(encoding="utf-8"))


def publisher_id(client: str) -> str:
    """``ca-pub-123…`` and ``pub-123…`` both mean the same publisher."""
    return client[3:] if client.startswith("ca-") else client


def fetch(url: str) -> tuple[int, str, str]:
    """Return ``(status, body, final_url)``; status 0 means the fetch failed."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(64_000).decode("utf-8", "replace")
            return response.status, body, response.url
    except urllib.error.HTTPError as exc:
        return exc.code, "", url
    except Exception as exc:  # DNS, TLS, timeout — all equally fatal here
        return 0, f"{type(exc).__name__}: {exc}", url


def check(url: str, publisher: str, *, required: bool) -> bool:
    """Fetch one URL and report. ``required`` false downgrades a miss to a note."""
    label = "FAIL" if required else "note"
    status, body, final = fetch(url)

    if status == 0:
        print(f"  {label}  {url}\n        unreachable — {body}")
        return not required
    if status != 200:
        print(f"  {label}  {url}\n        HTTP {status}")
        return not required
    if "<html" in body.lower():
        # A 200 that is really the 404 page. AdSense parses this as garbage
        # and reports no ads.txt, which is the confusing case this catches.
        print(f"  FAIL  {url}\n        HTTP 200 but the body is HTML, not an ads.txt record")
        return False
    if publisher not in body:
        print(f"  FAIL  {url}\n        served, but does not authorise {publisher}:\n"
              f"        {body.strip()[:200]!r}")
        return False

    note = "" if final == url else f" (via {final})"
    print(f"  ok    {url}{note}\n        {body.strip().splitlines()[0]}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default="",
        help="override site.json's base_url (e.g. http://localhost:8000)",
    )
    args = parser.parse_args(argv)

    cfg = config()
    base = (args.base_url or cfg.get("base_url", "")).rstrip("/")
    client = cfg.get("adsense_client", "")

    if not client:
        print("adsense_client is empty in site.json — nothing to check.")
        return 0
    host = urlparse(base).hostname or ""
    if not host:
        print(f"cannot read a hostname out of base_url {base!r}")
        return 1
    if host.endswith(".github.io"):
        print(f"{host} is a github.io address; ads.txt is only read at a domain "
              "root, so there is nothing to serve. Move to the custom domain first.")
        return 0

    publisher = publisher_id(client)
    print(f"ads.txt for {host}, expecting {publisher}\n")

    ok = check(f"{base}/ads.txt", publisher, required=True)
    if host.count(".") == 1:  # apex: the www alias is worth a look too
        scheme = urlparse(base).scheme or "https"
        ok &= check(f"{scheme}://www.{host}/ads.txt", publisher, required=False)

    print()
    if ok:
        print("live ads.txt is correct.\n"
              "If AdSense still shows the warning, it is reporting its last crawl;\n"
              "the console clears it on the next one. Check that AdSense → Sites\n"
              f"lists {host} itself — a stale github.io entry can never pass.")
        return 0
    print("live ads.txt is wrong or missing — redeploy, then re-run this check.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
