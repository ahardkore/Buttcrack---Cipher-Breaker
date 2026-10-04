"""Audit the assembled public site for broken links and SEO/accessibility faults.

The site is generated (``ventures/cipher-solver-web/build_pages.py``) and then
assembled (``scripts/build_site.py``), so a mistake in a template is a mistake
on sixty pages at once. Nothing was checking the output, which is how a link to
a page that does not exist, or a canonical URL pointing at the wrong file, stays
live indefinitely: the build is green either way.

Run it exactly as CI does::

    python3 scripts/build_site.py --out _site
    python3 scripts/audit_site.py _site

What it checks, per page:

* every internal ``href``/``src`` resolves to a file in the tree, and every
  ``#fragment`` resolves to an ``id`` on the target page;
* ``<title>``, meta description, canonical, viewport, ``<html lang>`` exist,
  and the canonical matches the page's own path under ``base_url``;
* titles and descriptions are unique across the site, and within the length
  Google will actually render;
* exactly one ``<h1>``, no skipped heading levels;
* every ``<img>`` has ``alt``; every input has a label or ``aria-label``;
* every ``application/ld+json`` block parses as JSON.

And across the site: sitemap entries exist and are not orphaned, robots.txt
points at the sitemap, a 404 page is present, no page is unreachable from the
front door.

Exit status is non-zero if any *error* is found; warnings are advisory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent

#: Google truncates around these widths. Not errors — the page still works —
#: but a 90-character title is a title with its ending cut off in the results.
TITLE_MAX = 65
DESC_MIN = 70
DESC_MAX = 165

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

#: Form controls that need an accessible name.
LABELLED_TAGS = {"input", "select", "textarea"}
#: ...except these, which are named by their own value or need no name.
UNLABELLED_INPUT_TYPES = {"hidden", "submit", "reset", "button", "image"}


class Page(HTMLParser):
    """Collects everything the audit needs in a single pass over one file."""

    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.links: list[tuple[str, str, int]] = []  # (attr, value, line)
        self.ids: set[str] = set()
        self.duplicate_ids: list[tuple[str, int]] = []
        self.headings: list[tuple[int, str, int]] = []
        self.title: str | None = None
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.lang: str | None = None
        self.ld_json: list[tuple[str, int]] = []
        self.images_without_alt: list[int] = []
        self.unlabelled: list[tuple[str, int]] = []
        self.labels_for: set[str] = set()
        self.controls: list[tuple[str, str | None, int]] = []  # (tag, id, line)
        self.unclosed: list[tuple[str, int]] = []
        self.empty_links: list[int] = []

        self._stack: list[tuple[str, int]] = []
        self._in_title = False
        self._in_ld = False
        self._ld_buf: list[str] = []
        self._ld_line = 0
        self._text_target: list[str] | None = None
        self._open_anchor: list[str] | None = None

    # -- parsing -----------------------------------------------------------
    def handle_starttag(self, tag, attrs):  # noqa: C901 - a flat dispatch
        a = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]

        if tag not in VOID_TAGS:
            self._stack.append((tag, line))

        if "id" in a and a["id"]:
            if a["id"] in self.ids:
                self.duplicate_ids.append((a["id"], line))
            self.ids.add(a["id"])
        if "name" in a and tag == "a" and a["name"]:
            self.ids.add(a["name"])

        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
            self._text_target = []
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key.lower()] = a.get("content", "")
        elif tag == "link":
            rels = a.get("rel", "").lower().split()
            if "canonical" in rels:
                self.canonical = a.get("href", "")
            if a.get("href"):
                self.links.append(("href", a["href"], line))
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_ld = True
                self._ld_buf = []
                self._ld_line = line
            if a.get("src"):
                self.links.append(("src", a["src"], line))
        elif tag == "img":
            if a.get("src"):
                self.links.append(("src", a["src"], line))
            if "alt" not in a:
                self.images_without_alt.append(line)
        elif tag == "a":
            if a.get("href"):
                self.links.append(("href", a["href"], line))
            self._open_anchor = []
            self._anchor_named = bool(a.get("aria-label") or a.get("title") or a.get("aria-labelledby"))
            self._anchor_line = line
        elif tag in LABELLED_TAGS:
            exempt = tag == "input" and a.get("type", "text").lower() in UNLABELLED_INPUT_TYPES
            named = bool(a.get("aria-label") or a.get("aria-labelledby") or a.get("title"))
            if not exempt and not named:
                self.controls.append((tag, a.get("id"), line))
        elif tag == "label" and a.get("for"):
            self.labels_for.add(a["for"])
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._text_target = []
            self._heading = (int(tag[1]), line)
        elif tag in {"source", "iframe", "video", "audio"} and a.get("src"):
            self.links.append(("src", a["src"], line))

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                break

        if tag == "title" and self._in_title:
            self.title = "".join(self._text_target or []).strip()
            self._in_title = False
            self._text_target = None
        elif tag == "script" and self._in_ld:
            self.ld_json.append(("".join(self._ld_buf), self._ld_line))
            self._in_ld = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._text_target is not None:
            level, line = self._heading
            self.headings.append((level, "".join(self._text_target).strip(), line))
            self._text_target = None
        elif tag == "a" and self._open_anchor is not None:
            text = "".join(self._open_anchor).strip()
            if not text and not self._anchor_named:
                self.empty_links.append(self._anchor_line)
            self._open_anchor = None

    def handle_data(self, data):
        if self._in_ld:
            self._ld_buf.append(data)
        if self._text_target is not None:
            self._text_target.append(data)
        if self._open_anchor is not None:
            self._open_anchor.append(data)

    def close(self):
        super().close()
        # <p> and <li> are allowed to be left open by the HTML parsing spec.
        self.unclosed = [
            (t, line)
            for t, line in self._stack
            if t not in {"p", "li", "dt", "dd", "option", "tr", "td", "th", "thead", "tbody"}
        ]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


def load_pages(site: Path) -> dict[Path, Page]:
    pages: dict[Path, Page] = {}
    for html in sorted(site.rglob("*.html")):
        page = Page(html)
        page.feed(html.read_text(encoding="utf-8", errors="replace"))
        page.close()
        pages[html] = page
    return pages


def resolve(site: Path, page: Path, target: str) -> Path | None:
    """Map an internal href to a file in the tree, or None if it escapes it."""
    clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not clean:
        return page
    base = site if clean.startswith("/") else page.parent
    dest = (base / clean.lstrip("/")).resolve()
    try:
        dest.relative_to(site.resolve())
    except ValueError:
        return None
    if dest.is_dir():
        dest = dest / "index.html"
    return dest


def check_links(site: Path, pages: dict[Path, Page], report: Report) -> None:
    for path, page in pages.items():
        rel = path.relative_to(site)
        for attr, value, line in page.links:
            if value.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:")):
                continue
            if value.startswith("//"):
                continue
            if value.startswith("#"):
                frag = unquote(value[1:])
                if frag and frag not in page.ids:
                    report.error(f"{rel}:{line}", f"fragment #{frag} has no matching id on this page")
                continue
            dest = resolve(site, path, value)
            if dest is None:
                report.error(f"{rel}:{line}", f'{attr}="{value}" escapes the site root')
                continue
            if not dest.exists():
                report.error(
                    f"{rel}:{line}",
                    f'broken {attr} "{value}" -> missing {dest.relative_to(site.resolve())}',
                )
                continue
            if "#" in value:
                frag = unquote(value.split("#", 1)[1])
                target_page = pages.get(dest)
                if frag and target_page is not None and frag not in target_page.ids:
                    report.error(
                        f"{rel}:{line}",
                        f'link "{value}" points at #{frag}, which does not exist on '
                        f"{dest.relative_to(site.resolve())}",
                    )


def _canonical_key(url: str) -> str:
    """Normalise a canonical URL so /dir/ and /dir/index.html compare equal."""
    trimmed = url.rstrip("/")
    if trimmed.endswith("/index.html"):
        trimmed = trimmed[: -len("/index.html")]
    elif trimmed.endswith("index.html"):
        trimmed = trimmed[: -len("index.html")].rstrip("/")
    return trimmed


def check_head(site: Path, pages: dict[Path, Page], base_url: str, report: Report) -> None:
    titles: dict[str, list[str]] = defaultdict(list)
    descriptions: dict[str, list[str]] = defaultdict(list)

    for path, page in pages.items():
        rel = path.relative_to(site)
        where = str(rel)

        # A noindex page is not a search result, so a canonical URL and a meta
        # description would be noise at best. The 404 page and the Stripe
        # delivery pages are deliberately in this category; everything else
        # still has to carry both.
        noindex = "noindex" in page.meta.get("robots", "").lower()

        if not page.lang:
            report.error(where, "<html> has no lang attribute")
        if not page.title:
            report.error(where, "no <title>")
        else:
            titles[page.title].append(where)
            if len(page.title) > TITLE_MAX:
                report.warn(
                    where, f"title is {len(page.title)} chars (over {TITLE_MAX}, will be truncated in results)"
                )

        desc = page.meta.get("description", "").strip()
        if not desc:
            if not noindex:
                report.error(where, "no meta description")
        else:
            descriptions[desc].append(where)
            if len(desc) > DESC_MAX:
                report.warn(where, f"meta description is {len(desc)} chars (over {DESC_MAX})")
            elif len(desc) < DESC_MIN:
                report.warn(where, f"meta description is only {len(desc)} chars (under {DESC_MIN})")

        if "viewport" not in page.meta:
            report.error(where, "no viewport meta — the page will not be mobile-friendly")

        if page.canonical is None:
            if not noindex:
                report.error(where, "no canonical link")
        elif base_url:
            expected = f"{base_url.rstrip('/')}/{rel.as_posix()}"
            # "/kryptos/" and "/kryptos/index.html" address the same document;
            # either spelling is a correct canonical, so compare normalised.
            if _canonical_key(page.canonical) != _canonical_key(expected):
                report.error(where, f"canonical is {page.canonical!r}, expected {expected!r}")

        for raw, line in page.ld_json:
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                report.error(f"{where}:{line}", f"invalid JSON-LD: {exc}")

    for title, where in titles.items():
        if len(where) > 1:
            report.warn("duplicate title", f"{title!r} on {', '.join(sorted(where))}")
    for desc, where in descriptions.items():
        if len(where) > 1:
            report.warn("duplicate description", f"{desc[:60]!r}... on {', '.join(sorted(where))}")


def check_structure(site: Path, pages: dict[Path, Page], report: Report) -> None:
    for path, page in pages.items():
        where = str(path.relative_to(site))

        h1s = [h for h in page.headings if h[0] == 1]
        if not h1s:
            report.error(where, "no <h1>")
        elif len(h1s) > 1:
            report.warn(where, f"{len(h1s)} <h1> elements (lines {', '.join(str(h[2]) for h in h1s)})")

        previous = 0
        for level, text, line in page.headings:
            if previous and level > previous + 1:
                report.warn(
                    f"{where}:{line}",
                    f"heading level jumps h{previous} -> h{level} ({text[:40]!r})",
                )
            previous = level

        for line in page.images_without_alt:
            report.error(f"{where}:{line}", "<img> without alt attribute")
        for line in page.empty_links:
            report.warn(f"{where}:{line}", "link with no text and no accessible name")
        for tag, control_id, line in page.controls:
            if not control_id or control_id not in page.labels_for:
                report.error(f"{where}:{line}", f"<{tag}> has no label and no aria-label")
        for element_id, line in page.duplicate_ids:
            report.error(f"{where}:{line}", f'duplicate id="{element_id}"')
        for tag, line in page.unclosed:
            report.error(f"{where}:{line}", f"<{tag}> is never closed")


def check_sitemap(site: Path, pages: dict[Path, Page], base_url: str, report: Report) -> None:
    sitemap = site / "sitemap.xml"
    if not sitemap.is_file():
        report.error("sitemap.xml", "missing")
        return

    text = sitemap.read_text(encoding="utf-8")
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", text)
    if not locs:
        report.error("sitemap.xml", "contains no <loc> entries")

    listed: set[str] = set()
    for loc in locs:
        if base_url and not loc.startswith(base_url):
            report.error("sitemap.xml", f"{loc} is not under base_url {base_url}")
            continue
        rel = loc[len(base_url) :].lstrip("/") if base_url else loc
        if rel in ("", "/") or rel.endswith("/"):
            rel = f"{rel}index.html"
        listed.add(rel)
        if not (site / rel).exists():
            report.error("sitemap.xml", f"lists {rel}, which is not in the built site")

    indexable = {str(p.relative_to(site)) for p in pages if "noindex" not in pages[p].meta.get("robots", "").lower()}
    # Thank-you pages are intentionally noindex; 404 is never listed.
    for missing in sorted(indexable - listed - {"404.html"}):
        report.warn("sitemap.xml", f"does not list {missing}")

    robots = site / "robots.txt"
    if not robots.is_file():
        report.error("robots.txt", "missing")
    else:
        body = robots.read_text(encoding="utf-8")
        if "Sitemap:" not in body:
            report.warn("robots.txt", "does not point at the sitemap")
        elif base_url and f"{base_url}/sitemap.xml" not in body:
            report.warn("robots.txt", "Sitemap: line does not match base_url")

    if not (site / "404.html").is_file():
        report.warn("404.html", "no custom 404 page")


def check_reachability(site: Path, pages: dict[Path, Page], report: Report) -> None:
    """Orphan pages: present in the tree but not linked from anywhere."""
    linked: set[Path] = set()
    for path, page in pages.items():
        for _attr, value, _line in page.links:
            if value.startswith(("http", "mailto:", "tel:", "data:", "#", "//", "javascript:")):
                continue
            dest = resolve(site, path, value)
            if dest is not None and dest.exists():
                linked.add(dest)

    root = (site / "index.html").resolve()
    for path in sorted(pages):
        resolved = path.resolve()
        if resolved == root or resolved in linked:
            continue
        name = path.relative_to(site).name
        if name == "404.html" or name.startswith("thank-you-"):
            continue
        report.warn(str(path.relative_to(site)), "orphan — nothing in the site links to it")


def check_domain_files(site: Path, base_url: str, report: Report) -> None:
    """CNAME and ads.txt: two one-line files whose absence is silent.

    Neither produces an error anybody sees. A missing CNAME makes an Actions
    deploy *clear* the custom domain stored in repository settings, and the
    site falls back to github.io with a green build. A missing or wrong
    ads.txt costs ad revenue without costing a page.
    """
    host = urlparse(base_url).hostname or ""
    cname = site / "CNAME"

    if host and not host.endswith(".github.io"):
        if not cname.is_file():
            report.error(
                "CNAME",
                f"missing — an Actions deploy publishes only the artifact, so this "
                f"would clear the custom domain ({host}) set in Settings and drop the site "
                f"back to github.io",
            )
        else:
            written = cname.read_text(encoding="utf-8").strip()
            if written != host:
                report.error("CNAME", f"says {written!r} but base_url host is {host!r}")
    elif cname.is_file():
        report.error("CNAME", f"present ({cname.read_text().strip()!r}) but base_url is {base_url}")

    config = ROOT / "ventures" / "cipher-solver-web" / "site.json"
    client = ""
    if config.is_file():
        client = json.loads(config.read_text(encoding="utf-8")).get("adsense_client", "")
    if not client or not host or host.endswith(".github.io"):
        return

    ads = site / "ads.txt"
    publisher = client[3:] if client.startswith("ca-") else client
    if not ads.is_file():
        report.error("ads.txt", f"missing — AdSense will report no ads.txt for {host}")
    elif publisher not in ads.read_text(encoding="utf-8"):
        report.error("ads.txt", f"does not authorise {publisher}")


def check_assets(site: Path, report: Report) -> None:
    """Assets referenced by CSS/JS that must exist, plus empty-file checks."""
    for path in sorted(site.rglob("*")):
        if path.is_file() and path.stat().st_size == 0:
            report.error(str(path.relative_to(site)), "file is empty")

    for css in sorted(site.rglob("*.css")):
        body = css.read_text(encoding="utf-8", errors="replace")
        for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", body):
            if ref.startswith(("http", "data:", "//")):
                continue
            dest = (css.parent / ref.split("?", 1)[0]).resolve()
            if not dest.exists():
                report.error(str(css.relative_to(site)), f"url({ref}) does not exist")


def base_url_from_site_json() -> str:
    config = ROOT / "ventures" / "cipher-solver-web" / "site.json"
    if config.is_file():
        return json.loads(config.read_text(encoding="utf-8")).get("base_url", "").rstrip("/")
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "site", nargs="?", default=str(ROOT / "_site"), help="the assembled site directory (default: ./_site)"
    )
    parser.add_argument("--base-url", default=None, help="override the base URL used to check canonicals")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures too")
    args = parser.parse_args(argv)

    site = Path(args.site).resolve()
    if not site.is_dir():
        raise SystemExit(f"no assembled site at {site}\nBuild it first: python3 scripts/build_site.py --out _site")

    base_url = args.base_url if args.base_url is not None else base_url_from_site_json()
    base_url = base_url.rstrip("/")

    pages = load_pages(site)
    report = Report()

    check_links(site, pages, report)
    check_head(site, pages, base_url, report)
    check_structure(site, pages, report)
    check_sitemap(site, pages, base_url, report)
    check_reachability(site, pages, report)
    check_domain_files(site, base_url, report)
    check_assets(site, report)

    print(f"audited {len(pages)} pages in {site}")
    for warning in report.warnings:
        print(f"  warning  {warning}")
    for error in report.errors:
        print(f"  ERROR    {error}")

    print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    if report.errors or (args.strict and report.warnings):
        return 1
    print("site audit clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
