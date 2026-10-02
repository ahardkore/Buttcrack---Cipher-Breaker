"""Assemble the single public site that GitHub Pages publishes.

The repository grew two independent web surfaces:

* ``ventures/cipher-solver-web`` — the generated, SEO-facing cipher solver,
  wiki and storefront. This is the front door.
* ``kryptos-app`` — the standalone Kryptos research explorer.

They used to have a GitHub Pages workflow each, racing for the same
``pages`` deployment, so whichever ran last silently replaced the other.
This script merges them into one tree instead::

    _site/                 <- the solver site, at the domain root
    _site/kryptos/         <- the Kryptos research explorer

Run it locally exactly as the deploy does::

    python3 scripts/build_site.py --out _site
    python3 -m http.server 8000 -d _site

Source files that are only build inputs (Python generators, the Node test
harness, the raw corpus) are left out of the published tree.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SOLVER = ROOT / "ventures" / "cipher-solver-web"
KRYPTOS_APP = ROOT / "kryptos-app"

#: Mounted under the site root; keep in step with ``KRYPTOS_HREF`` in
#: ``ventures/cipher-solver-web/build_pages.py``, which links to it from the nav.
KRYPTOS_DIR = "kryptos"

#: Build inputs, not site content. Publishing them would serve dead weight and
#: advertise the generator's configuration for no benefit.
EXCLUDE_NAMES = {
    "build_pages.py",
    "build_model.py",
    "set_payment_links.py",
    "wiki_ciphers.py",
    "wiki_history.py",
    "test.js",
    "site.json",
    "__pycache__",
}
EXCLUDE_SUFFIXES = {".pyc"}


def _skip(path: Path) -> bool:
    return path.name in EXCLUDE_NAMES or path.suffix in EXCLUDE_SUFFIXES


def copy_tree(src: Path, dest: Path) -> int:
    """Copy ``src`` into ``dest``, skipping build inputs. Returns file count."""
    if not src.is_dir():
        raise SystemExit(f"missing source directory: {src}")
    copied = 0
    for item in sorted(src.rglob("*")):
        if any(_skip(part) for part in (item, *item.relative_to(src).parents)):
            continue
        if _skip(item):
            continue
        target = dest / item.relative_to(src)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied += 1
    return copied


#: Extensions that must never reach the published tree. The Windows installer
#: is a paid product delivered from storage the author controls; this site and
#: the repository behind it are both public, so a copy that lands here is the
#: product given away, quietly, to anyone who guesses the path or clones.
PAID_BINARY_SUFFIXES = {".exe", ".msi"}


def refuse_paid_binaries(tree: Path) -> None:
    """Fail the deploy rather than publish something that is for sale."""
    strays = sorted(
        path for path in tree.rglob("*") if path.suffix.lower() in PAID_BINARY_SUFFIXES
    )
    if not strays:
        return
    listing = "\n  ".join(str(path.relative_to(tree)) for path in strays)
    raise SystemExit(
        f"refusing to publish executable(s) from the site tree:\n  {listing}\n\n"
        "The Windows installer is sold through Stripe and must live on storage you\n"
        "control (Cloudflare R2, Backblaze B2, S3), with its URL in site.json under\n"
        "windows_app.delivery_url. Publishing it here hands the paid build to anyone\n"
        "who finds the path.\n\n"
        "If you genuinely mean to give a binary away, set BUTTCRACK_PUBLISH_BINARIES=1."
    )


#: Read for ``adsense_client`` below. ``build_pages.py`` owns this file; this
#: script only reads it, and only to keep the two halves of the site in step.
SITE_JSON = SOLVER / "site.json"


def site_config() -> dict:
    """``site.json``, or an empty dict. ``build_pages.py`` owns this file; this
    script only reads it, to keep the two halves of the site in step."""
    if not SITE_JSON.is_file():
        return {}
    return json.loads(SITE_JSON.read_text(encoding="utf-8"))


def custom_domain() -> str:
    """The bare host from ``base_url``, or "" when the site is on github.io.

    ``ciphersolverpro.com``, not ``https://ciphersolverpro.com/`` — a CNAME
    file holds a hostname and nothing else.
    """
    base = site_config().get("base_url", "")
    host = urlparse(base).hostname or ""
    return "" if host.endswith(".github.io") else host


def write_cname(tree: Path) -> str:
    """Put the custom domain in the artifact, or the deploy will drop it.

    This one is a trap worth spelling out. A custom domain set in
    Settings → Pages is stored against the *repository*, but an Actions deploy
    publishes exactly what is in the *artifact* — and an artifact with no CNAME
    file clears the stored domain. The site then quietly falls back to
    github.io, with a green deploy and no error anywhere, until someone
    notices the domain is dead.

    So the file is generated here, from ``base_url``, on every build. A
    github.io ``base_url`` correctly produces no file at all.
    """
    host = custom_domain()
    if not host:
        return ""
    (tree / "CNAME").write_text(f"{host}\n", encoding="utf-8")
    return host


def adsense_loader() -> str:
    """The AdSense loader tag for the configured publisher, or "" if unset.

    Byte-for-byte what ``build_pages.adsense_head`` puts in the generated
    pages; see ``inject_adsense`` for why it is needed twice.
    """
    client = site_config().get("adsense_client", "")
    if not client:
        return ""
    return (
        '  <script async crossorigin="anonymous" '
        f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client}">'
        "</script>\n"
    )


def inject_adsense(tree: Path) -> int:
    """Put the AdSense loader in the <head> of hand-written pages.

    AdSense wants its tag on *every* page of the site, and site reviews fail on
    the pages that are missing it. The solver half is generated, so
    ``build_pages.py`` emits the tag into all of it; the Kryptos explorer is a
    hand-written app that no generator touches. Rather than paste the publisher
    ID into a second file, where it would quietly drift out of step with
    ``site.json``, insert it here at assembly time from the same config.

    Idempotent: a page that already loads adsbygoogle.js is left alone.
    """
    tag = adsense_loader()
    if not tag:
        return 0
    injected = 0
    for page in sorted(tree.rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        if "adsbygoogle.js" in html:
            continue
        if "</head>" not in html:
            raise SystemExit(f"cannot add the AdSense tag: {page} has no </head>")
        page.write_text(html.replace("</head>", f"{tag}</head>", 1), encoding="utf-8")
        injected += 1
    return injected


def build(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    pages = copy_tree(SOLVER, out)
    print(f"solver site   -> {out}/ ({pages} files)")

    kryptos_out = out / KRYPTOS_DIR
    research = copy_tree(KRYPTOS_APP, kryptos_out)
    print(f"kryptos app   -> {out}/{KRYPTOS_DIR}/ ({research} files)")

    added = inject_adsense(kryptos_out)
    if added:
        print(f"adsense tag   -> added to {added} hand-written page(s) under {KRYPTOS_DIR}/")

    host = write_cname(out)
    if host:
        print(f"custom domain -> {out}/CNAME ({host})")
    else:
        print("custom domain -> none (base_url is a github.io address)")

    # Both halves must actually have an entry point, or the deploy publishes a
    # directory listing (or a 404) and nobody notices until someone visits.
    for required in (out / "index.html", kryptos_out / "index.html"):
        if not required.is_file():
            raise SystemExit(f"assembled site is missing {required.relative_to(out)}")

    if os.environ.get("BUTTCRACK_PUBLISH_BINARIES") != "1":
        refuse_paid_binaries(out)

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        default=str(ROOT / "_site"),
        help="output directory for the assembled site (default: ./_site)",
    )
    args = parser.parse_args(argv)

    out = build(Path(args.out).resolve())
    print(f"\nsite assembled in {out}")
    print(f"preview with: python3 -m http.server 8000 -d {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
