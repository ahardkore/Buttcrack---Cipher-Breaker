"""Fetch a finished Windows installer from CI, and say which ones exist.

The installer is never in this repository: it is the paid download and the
repository is public.  What CI produces instead is a *workflow artifact*, and
because an ordinary run now withdraws its own copy (see
`docs/windows-installer.md`), the newest run is usually the one place there is
nothing to find.  "Where is the installer" is therefore a question about the
artifacts that are live, which is what this answers:

    python scripts/fetch_installer.py --list
    python scripts/fetch_installer.py                        # newest, into dist/installer
    python scripts/fetch_installer.py --version 1.2.0
    python scripts/fetch_installer.py --artifact 11780675745

Every name `--list` prints has already passed the silent install, the installed
CLI breaking a cipher, the 142-check self-test and the uninstall, because the
upload happens after that test.  A live artifact is a verified installer.

The download uses the anonymous artifact API and needs no account, because the
repository is public.  Should a build ever be private, set `GITHUB_TOKEN` (or
`GH_TOKEN`) and the same commands keep working.

The three numbers the download page wants -- version, size, SHA-256 -- are
printed at the end, ready to paste into `ventures/cipher-solver-web/site.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

REPO = "ahardkore/Buttcrack---Cipher-Breaker"
API = "https://api.github.com"
PREFIX = "buttcrack-installer-"
DEFAULT_OUT = Path("dist") / "installer"


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Follow artifact storage's redirect without handing it the API token.

    The zip endpoint answers 302 to a signed URL on a different host.  That URL
    carries its own signature, and forwarding an Authorization header to a host
    that never asked for one is a way to have a working download rejected.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            new.remove_header("Authorization")
        return new


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "buttcrack-fetch-installer",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _read(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers=_headers())
    opener = urllib.request.build_opener(_StripAuthOnRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"GitHub answered {error.code} for {url}\n{detail}") from None
    except urllib.error.URLError as error:
        raise SystemExit(f"could not reach {url}: {error.reason}") from None


def live_installers() -> list[dict]:
    """Every live ``buttcrack-installer-*`` artifact, newest first."""
    found: list[dict] = []
    page = 1
    while True:
        payload = json.loads(_read(f"{API}/repos/{REPO}/actions/artifacts?per_page=100&page={page}").decode("utf-8"))
        batch = payload.get("artifacts", [])
        for artifact in batch:
            if artifact["name"].startswith(PREFIX) and not artifact.get("expired"):
                found.append(artifact)
        if len(batch) < 100:
            break
        page += 1
    return sorted(found, key=lambda artifact: artifact["created_at"], reverse=True)


def version_of(artifact: dict) -> str:
    return artifact["name"][len(PREFIX):]


def choose(artifacts: list[dict], version: str | None, artifact_id: int | None) -> dict:
    if artifact_id is not None:
        for artifact in artifacts:
            if artifact["id"] == artifact_id:
                return artifact
        raise SystemExit(f"no live installer artifact with id {artifact_id} -- try --list")
    if version is not None:
        matches = [artifact for artifact in artifacts if version_of(artifact) == version]
        if not matches:
            live = ", ".join(sorted({version_of(artifact) for artifact in artifacts})) or "none"
            raise SystemExit(f"no live installer for version {version} (live: {live})")
        return matches[0]
    if not artifacts:
        raise SystemExit(
            "no installer artifact is live right now.\n"
            "An ordinary run withdraws its own copy, so ask for one and try again in about\n"
            "twenty minutes:\n"
            "  gh workflow run 'Release artifacts'"
        )
    return artifacts[0]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def human_megabytes(size: int) -> str:
    return f"{size / 1_000_000:.1f} MB"


def download(artifact: dict, out_dir: Path) -> Path:
    """Fetch the artifact, write what is in it, and check the digest landed."""
    payload = _read(f"{API}/repos/{REPO}/actions/artifacts/{artifact['id']}/zip", timeout=900)
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        wanted = [
            name
            for name in bundle.namelist()
            if name.endswith((".exe", ".sha256")) or name == "INSTALLER-SHA256.json"
        ]
        if not any(name.endswith(".exe") for name in wanted):
            raise SystemExit(f"artifact {artifact['id']} carries no .exe -- contents: {bundle.namelist()}")
        out_dir.mkdir(parents=True, exist_ok=True)
        written = {}
        for name in wanted:
            target = out_dir / Path(name).name
            target.write_bytes(bundle.read(name))
            written[target.name] = target
    setup = next(path for path in written.values() if path.name.endswith(".exe"))
    digest = sha256_of(setup)
    recorded = Path(f"{setup}.sha256")
    if recorded.exists():
        expected = recorded.read_text(encoding="utf-8").strip().split()[0].lower()
        if expected != digest:
            setup.unlink()
            raise SystemExit(
                f"digest mismatch: {setup.name} hashed {digest}, its .sha256 says {expected}.\n"
                f"The download is not intact and the file has been removed; run this again."
            )
    size = setup.stat().st_size
    print(f"wrote {setup}  ({size:,} bytes, {human_megabytes(size)})")
    print(f"sha256 {digest}{'  (checked against ' + recorded.name + ')' if recorded.exists() else ''}")
    print()
    print("ventures/cipher-solver-web/site.json:")
    print(f'  "version": "{version_of(artifact)}",')
    print(f'  "size": "{human_megabytes(size)}",')
    print(f'  "sha256": "{digest}"')
    return setup


def as_json(artifacts: list[dict]) -> str:
    """The same facts as ``--list``, for whatever wants to read them.

    ``publish-installer.yml`` picks the newest live artifact with this rather
    than with a fourth copy of the filtering rules.
    """
    return json.dumps(
        [
            {
                "id": artifact["id"],
                "name": artifact["name"],
                "version": version_of(artifact),
                "created_at": artifact["created_at"],
                "expires_at": artifact["expires_at"],
                "size_in_bytes": artifact["size_in_bytes"],
            }
            for artifact in artifacts
        ],
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List and download the Windows installers CI has built.",
        epilog="Nothing here touches the network but the GitHub API.",
    )
    parser.add_argument("--list", action="store_true", help="show every live installer and when it lapses")
    parser.add_argument("--json", action="store_true", help="with --list, print JSON instead of a table")
    parser.add_argument("--version", help="fetch this version instead of the newest")
    parser.add_argument("--artifact", type=int, help="fetch this artifact id instead of the newest")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"where to write it (default {DEFAULT_OUT})")
    args = parser.parse_args(argv)

    artifacts = live_installers()
    if args.list:
        if args.json:
            print(as_json(artifacts))
            return 0
        if not artifacts:
            print("no installer artifact is live right now.")
            print("Ask for one:  gh workflow run 'Release artifacts'")
            return 0
        print(f"{'created':16}  {'version':9} {'size':>9}  {'lapses':16} artifact")
        for artifact in artifacts:
            print(
                f"{artifact['created_at'][:16].replace('T', ' ')}  "
                f"{version_of(artifact):9} {human_megabytes(artifact['size_in_bytes']):>9}  "
                f"{artifact['expires_at'][:16].replace('T', ' ')} {artifact['id']}"
            )
        print(f"\n{len(artifacts)} live. Fetch one with --version <version> or --artifact <id>.")
        return 0

    download(choose(artifacts, args.version, args.artifact), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
