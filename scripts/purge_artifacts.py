"""Withdraw installer artifacts that should not be public any more.

`.github/workflows/release.yml` now deletes a build's own artifact at the end of
an ordinary run, so the pile stops growing.  This clears what is already up,
because a public repository's artifacts are public: anyone can list them and ask
for a download URL, and the repository is public.

Nothing is deleted unless `--apply` is passed, and what would go is printed
first, with sizes and expiry dates:

    python scripts/purge_artifacts.py                        # installer artifacts, keep newest per version
    python scripts/purge_artifacts.py --keep 11780675745     # ...but not this one
    python scripts/purge_artifacts.py --include-builds       # also the frozen application bundles
    python scripts/purge_artifacts.py --apply --keep 11780675745

`--apply` needs `GITHUB_TOKEN` (or `GH_TOKEN`) with `actions: write` on the
repository -- a fine-grained token with that one permission is enough.  Keep the
artifact you intend to publish: `scripts/fetch_installer.py --list` says which
are live and when they lapse, and the build is reproducible either way.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict

REPO = "ahardkore/Buttcrack---Cipher-Breaker"
API = "https://api.github.com"
INSTALLER_PREFIX = "buttcrack-installer-"
BUILD_NAMES = {"buttcrack-windows-latest", "buttcrack-ubuntu-latest"}


def is_installer(artifact: dict) -> bool:
    return artifact["name"].startswith(INSTALLER_PREFIX)


def is_build(artifact: dict) -> bool:
    return artifact["name"] in BUILD_NAMES


def group_key(artifact: dict) -> str:
    """What "newest one" is newest *of*: a version, or a platform's bundle."""
    if is_installer(artifact):
        return artifact["name"]
    return artifact["name"]


def select(artifacts: list[dict], keep_newest: int = 1, keep_ids: set[int] | None = None, include_builds: bool = False):
    """Which artifacts to withdraw, and which were never candidates.

    Keeps the newest ``keep_newest`` of each group, and anything named in
    ``keep_ids``.  Returns ``(doomed, spared, ignored)`` so the caller can say
    what it left alone and why.
    """
    keep_ids = keep_ids or set()
    candidates = [a for a in artifacts if is_installer(a) or (include_builds and is_build(a))]
    ignored = [a for a in artifacts if a not in candidates]

    grouped: dict[str, list[dict]] = defaultdict(list)
    for artifact in sorted(candidates, key=lambda a: a["created_at"], reverse=True):
        grouped[group_key(artifact)].append(artifact)

    doomed, spared = [], []
    for group in sorted(grouped):
        for index, artifact in enumerate(grouped[group]):
            if index < keep_newest or artifact["id"] in keep_ids:
                spared.append(artifact)
            else:
                doomed.append(artifact)
    return doomed, spared, ignored


def _request(method: str, url: str, token: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "buttcrack-purge-artifacts")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def live_artifacts() -> list[dict]:
    """Every artifact the repository still holds."""
    found: list[dict] = []
    page = 1
    while True:
        status, body = _request("GET", f"{API}/repos/{REPO}/actions/artifacts?per_page=100&page={page}", "")
        if status != 200:
            raise SystemExit(f"GitHub answered {status} listing artifacts: {body.decode('utf-8', 'replace')[:300]}")
        payload = json.loads(body.decode("utf-8"))
        batch = payload.get("artifacts", [])
        found.extend(batch)
        if len(batch) < 100:
            return found
        page += 1


def megabytes(count: int) -> str:
    return f"{count / 1_000_000:.1f} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List (and with --apply, withdraw) public installer artifacts.")
    parser.add_argument("--keep-newest", type=int, default=1, help="keep this many of each version (default 1)")
    parser.add_argument("--keep", type=int, action="append", default=[], help="never touch this artifact id (repeatable)")
    parser.add_argument("--include-builds", action="store_true", help="also consider the frozen application bundles")
    parser.add_argument("--apply", action="store_true", help="actually delete; without it, nothing is touched")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if args.apply and not token:
        raise SystemExit("--apply needs GITHUB_TOKEN (or GH_TOKEN) with actions: write on the repository.")

    artifacts = live_artifacts()
    kept_ids = set(args.keep)
    doomed, spared, ignored = select(artifacts, args.keep_newest, kept_ids, args.include_builds)

    print(f"{len(artifacts)} artifacts in the repository, {megabytes(sum(a['size_in_bytes'] for a in artifacts))}")
    print(f"{len(doomed)} would be withdrawn ({megabytes(sum(a['size_in_bytes'] for a in doomed))})\n")
    for artifact in doomed:
        print(
            f"  {artifact['id']:>12}  {artifact['name']:32} {megabytes(artifact['size_in_bytes']):>9}  "
            f"made {artifact['created_at'][:10]}  lapses {artifact['expires_at'][:10]}"
        )
    if spared:
        print(f"\nkept {len(spared)}:")
        for artifact in spared:
            print(f"  {artifact['id']:>12}  {artifact['name']:32} {artifact['created_at'][:10]}")
    if ignored:
        kinds = sorted({artifact["name"] for artifact in ignored})
        print(f"\nnot this script's business ({len(ignored)} artifacts): {', '.join(kinds[:6])}"
              f"{' ...' if len(kinds) > 6 else ''}")

    if not args.apply:
        print("\nNothing was deleted. Add --apply to withdraw the list above.")
        return 0

    if not doomed:
        print("\nNothing to withdraw.")
        return 0

    failed = 0
    for artifact in doomed:
        status, body = _request("DELETE", f"{API}/repos/{REPO}/actions/artifacts/{artifact['id']}", token)
        if status == 204:
            print(f"  withdrew {artifact['id']}  {artifact['name']}")
        else:
            failed += 1
            print(f"  FAILED {artifact['id']} ({status}): {body.decode('utf-8', 'replace')[:120]}")
    if failed:
        raise SystemExit(
            f"\n{failed} of {len(doomed)} could not be withdrawn. A 403 means the token lacks "
            f"actions: write on this repository."
        )
    print(f"\n{len(doomed)} withdrawn, {megabytes(sum(a['size_in_bytes'] for a in doomed))} no longer downloadable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
