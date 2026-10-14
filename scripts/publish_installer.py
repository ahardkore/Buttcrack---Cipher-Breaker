"""Put a verified installer where the buyer's download page points.

`docs/windows-installer.md` states the rule this exists to keep: the paid `.exe`
never goes in the repository and never goes on the site, because both are
public.  It goes to storage you control, under a name nobody would guess, and
only the post-payment page ever shows the URL.  This is that step, and it prints
the four values `site.json` and the Stripe payment link need.

The storage has to speak the S3 API, which Cloudflare R2, Backblaze B2 and S3
all do:

    export BUTTCRACK_DELIVERY_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
    export BUTTCRACK_DELIVERY_BUCKET=buttcrack-downloads
    export BUTTCRACK_DELIVERY_BASE_URL=https://downloads.yourdomain
    export AWS_ACCESS_KEY_ID=...        # an R2 API token, or an S3 key
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_DEFAULT_REGION=auto      # optional; filled in automatically for R2

    python scripts/publish_installer.py dist/installer/buttcrack-setup-1.2.0.exe
    python scripts/publish_installer.py ... --dry-run        # say what would happen

`--dry-run` needs none of the above and uploads nothing.

**Publish the build you tested.** The digest printed here is of the file on this
disk, and that is the number `site.json` has to carry -- a hash from a different
build is worse than no hash, because the page promises the file is the one
described there.  `.github/workflows/publish-installer.yml` therefore fetches the
artifact of a run that already passed the install and uninstall test rather than
building again.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_installer import human_megabytes, sha256_of  # noqa: E402  (path set up above)

#: The checkout this script is publishing from.
ROOT = Path(__file__).resolve().parents[1]

#: The object name: an unguessable URL *is* the paywall for a $39.99 download
#: with no licence server, so the token is the product's lock and 64 bits of it
#: is the number the docs have published from the start.
TOKEN_BYTES = 8


def repo_version(root: Path = ROOT) -> str:
    """The version this checkout says it is, or ``""`` if it cannot be read.

    Read from ``pyproject.toml`` rather than by importing ``buttcrack``: this
    script runs in a job that installs nothing, and the two are pinned equal by
    ``tests/test_windows_bundle.py`` anyway.  An unreadable value returns empty
    and the caller skips the comparison rather than guessing.
    """
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


ENV = {
    "endpoint": "BUTTCRACK_DELIVERY_ENDPOINT",
    "bucket": "BUTTCRACK_DELIVERY_BUCKET",
    "base_url": "BUTTCRACK_DELIVERY_BASE_URL",
    "prefix": "BUTTCRACK_DELIVERY_PREFIX",
}

CONTENT_TYPE = "application/octet-stream"


def parse_version(name: str) -> str:
    """The version out of ``buttcrack-setup-1.2.0.exe``."""
    stem = Path(name).name
    for suffix in (".exe", ".msi"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    prefix = "buttcrack-setup-"
    if not stem.startswith(prefix):
        raise SystemExit(f"not something this publishes: {Path(name).name} (expected buttcrack-setup-<version>.exe)")
    version = stem[len(prefix):]
    if not version or not all(part.isdigit() for part in version.split(".")):
        raise SystemExit(f"cannot read a version out of {Path(name).name}")
    return version


def new_token() -> str:
    """A fresh 16-hex-digit object-name token."""
    return secrets.token_hex(TOKEN_BYTES)


def object_key(version: str, token: str) -> str:
    return f"buttcrack-setup-{version}-{token}.exe"


def delivery_url(base_url: str, prefix: str, key: str) -> str:
    """Join the public base, the optional folder and the object name.

    ``base_url`` is the host the download page links to -- a custom domain on
    the bucket, or an r2.dev address -- so this is the string that goes into
    ``windows_app.delivery_url``.
    """
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/{prefix.strip('/')}/{key}".replace("//", "/").replace(":/", "://")


def aws_command(path: Path, bucket: str, key: str, endpoint: str) -> list[str]:
    """The S3 upload, with the three headers the download depends on.

    ``application/octet-stream`` because a host that guesses serves a `.exe` as
    ``text/html`` and it arrives corrupt; a long ``Cache-Control`` because the
    object never changes once it is named; ``content-disposition: attachment``
    so the browser saves it rather than offering to render it.
    """
    return [
        "aws",
        "s3",
        "cp",
        str(path),
        f"s3://{bucket}/{key}",
        "--endpoint-url",
        endpoint,
        "--content-type",
        CONTENT_TYPE,
        "--cache-control",
        "public, max-age=31536000, immutable",
        "--content-disposition",
        f'attachment; filename="{path.name}"',
    ]


def upload_env(endpoint: str) -> dict[str, str]:
    """The environment the AWS CLI needs, defaulted so R2 works untouched.

    Signature V4 signs a region, and the CLI refuses to sign anything without
    one -- ``NoRegionError`` before it ever reaches the network.  R2 accepts any
    region string and its own tooling writes ``auto``; B2 wants the region in its
    endpoint (``s3.us-west-004.``) and S3 wants the bucket's real region, so this
    only fills in R2 and otherwise leaves the environment alone.  An explicit
    ``AWS_DEFAULT_REGION`` always wins.
    """
    env = dict(os.environ)
    if "AWS_DEFAULT_REGION" not in env and "r2.cloudflarestorage.com" in endpoint:
        env["AWS_DEFAULT_REGION"] = "auto"
    return env


def run_upload(path: Path, bucket: str, key: str, endpoint: str) -> None:
    if shutil.which("aws") is None:
        raise SystemExit(
            "the AWS CLI is not on PATH, and it is what performs the upload.\n"
            "  pip install awscli    # or: brew install awscli\n"
            "It only makes S3 API calls, so it works against R2 and B2 unchanged."
        )
    command = aws_command(path, bucket, key, endpoint)
    print("$ " + " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, env=upload_env(endpoint))
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"upload failed with exit code {result.returncode}")


def update_site_json(path: Path, url: str, version: str, size: int, digest: str) -> list[str]:
    """Write the four published values into ``site.json``; return what changed.

    Opt-in, because this edits a file that is also hand-maintained: only the four
    keys under ``windows_app`` are touched, everything else is left exactly as it
    was, and the change is reported rather than assumed.  ``build_pages.py``
    validates ``delivery_url`` on every build, so a bad one here fails the next
    deploy instead of quietly going live.
    """
    if not url:
        raise SystemExit(
            "refusing to write site.json with no delivery URL: set "
            "BUTTCRACK_DELIVERY_BASE_URL (or --base-url) so the buyer's link can be built."
        )
    if not path.is_file():
        raise SystemExit(f"no such file: {path}")

    document = json.loads(path.read_text(encoding="utf-8"))
    app = document.setdefault("windows_app", {})
    wanted = {"delivery_url": url, "version": version, "size": human_megabytes(size), "sha256": digest}
    changes = [
        f"  windows_app.{key}: {app.get(key)!r} -> {value!r}" for key, value in wanted.items() if app.get(key) != value
    ]
    app.update(wanted)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changes


def fields_block(url: str, version: str, size: int, digest: str) -> str:
    return "\n".join(
        [
            "ventures/cipher-solver-web/site.json, under windows_app:",
            f'  "delivery_url": "{url}",',
            f'  "version": "{version}",',
            f'  "size": "{human_megabytes(size)}",',
            f'  "sha256": "{digest}"',
            "",
            "Then the buyer's path is: windows-app.html -> Stripe Payment Link -> the",
            "thank-you page build_pages.py prints -> windows_app.delivery_url. Paste that",
            "thank-you URL into the payment link's post-payment redirect if it is not there",
            "yet; build_pages.py prints both on every run.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload a verified installer to your own storage.")
    parser.add_argument("installer", type=Path, help="the buttcrack-setup-<version>.exe to publish")
    parser.add_argument("--token", default="", help="object-name token; reuse one to republish the same URL")
    parser.add_argument("--prefix", default=os.environ.get(ENV["prefix"], ""), help="folder inside the bucket")
    parser.add_argument("--bucket", default=os.environ.get(ENV["bucket"], ""))
    parser.add_argument("--endpoint", default=os.environ.get(ENV["endpoint"], ""))
    parser.add_argument("--base-url", default=os.environ.get(ENV["base_url"], ""))
    parser.add_argument("--dry-run", action="store_true", help="print what would happen; upload nothing")
    parser.add_argument(
        "--allow-version-mismatch",
        action="store_true",
        help="publish an installer whose version is not this checkout's version",
    )
    parser.add_argument(
        "--update-site-json",
        type=Path,
        metavar="PATH",
        help="also write delivery_url/version/size/sha256 into site.json at PATH",
    )
    parser.add_argument("--annotate", action="store_true", help="also emit ::notice lines for GitHub Actions")
    args = parser.parse_args(argv)

    path = args.installer
    if not path.is_file():
        raise SystemExit(f"no such file: {path}")
    version = parse_version(path.name)
    digest = sha256_of(path)
    size = path.stat().st_size

    # A `.sha256` written by build.ps1 travels next to the installer and is the
    # cheapest possible check that the file is the one that was tested.
    sidecar = Path(f"{path}.sha256")
    recorded = sidecar.read_text(encoding="utf-8").strip().split()[0].lower() if sidecar.is_file() else ""
    if recorded and recorded != digest:
        raise SystemExit(
            f"{path.name} hashes {digest} but its .sha256 says {recorded}.\n"
            f"These are not the same build; publish the pair that belongs together."
        )

    # The check that was missing when a stale 1.2.1 was published from a 1.2.2
    # checkout and the run still reported success.  The workflow picks "the
    # newest live artifact", and an ordinary push or pull-request run *withdraws*
    # its own installer, so the newest live one is routinely the last manually
    # dispatched build -- which is whatever version main happened to be at that
    # day.  Nothing downstream compares it to the code being published from, so
    # the upload succeeds, the digest is printed, and the download page ends up
    # advertising yesterday's build as today's.  Refuse here, at the one point
    # that touches production storage, whatever selected the file.
    checkout_version = repo_version()
    if checkout_version and version != checkout_version and not args.allow_version_mismatch:
        raise SystemExit(
            f"{path.name} is version {version}, but this checkout is {checkout_version}.\n"
            f"Publishing it would advertise {version} as the current release.\n"
            f"\n"
            f"The usual cause is that no build of {checkout_version} was ever kept: an\n"
            f"ordinary push or pull-request run withdraws its own installer artifact, so\n"
            f"only a manually dispatched one survives to be fetched. Ask for one and try\n"
            f"again in about twenty minutes:\n"
            f"  gh workflow run 'Release artifacts' --ref main\n"
            f"\n"
            f"Live artifacts:  python scripts/fetch_installer.py --list\n"
            f"If you really mean to republish an older version, pass --allow-version-mismatch."
        )

    token = args.token.strip() or new_token()
    key = object_key(version, token)
    url = delivery_url(args.base_url, args.prefix, key)

    if args.dry_run:
        print(f"would publish {path.name} ({size:,} bytes)")
        print(f"  object    s3://{args.bucket or '<bucket>'}/{args.prefix.strip('/') + '/' if args.prefix.strip('/') else ''}{key}")
        print(f"  endpoint  {args.endpoint or '<BUTTCRACK_DELIVERY_ENDPOINT>'}")
        print(f"  url       {url or '<BUTTCRACK_DELIVERY_BASE_URL> missing -- set it to see the link buyers get'}")
        print(f"  sha256    {digest}")
        if sidecar.is_file():
            print(f"  sidecar   {sidecar.name} would be uploaded beside it")
        if args.update_site_json:
            print(f"  site.json {args.update_site_json} would be updated (nothing is written on a dry run)")
        print()
        print(fields_block(url or "<delivery_url>", version, size, digest))
        return 0

    # Checked on the resolved values, so a flag and its environment variable are
    # interchangeable -- and so the message names the variable, which is the one
    # that has to be set in CI.
    missing = [
        name
        for name, value in (
            (ENV["bucket"], args.bucket),
            (ENV["endpoint"], args.endpoint),
            (ENV["base_url"], args.base_url),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            f"not set: {', '.join(missing)}\n"
            f"Set each as an environment variable (or pass --bucket/--endpoint/--base-url).\n"
            f"See the top of this file, or docs/windows-installer.md, for what each one is."
        )

    run_upload(path, args.bucket, f"{args.prefix.strip('/') + '/' if args.prefix.strip('/') else ''}{key}", args.endpoint)
    if sidecar.is_file():
        run_upload(sidecar, args.bucket, f"{args.prefix.strip('/') + '/' if args.prefix.strip('/') else ''}{key}.sha256", args.endpoint)

    print()
    print(f"published {url}")
    print(f"  {size:,} bytes ({human_megabytes(size)}), sha256 {digest}")
    print()
    print(fields_block(url, version, size, digest))

    if args.update_site_json:
        changes = update_site_json(args.update_site_json, url, version, size, digest)
        print()
        if changes:
            print(f"{args.update_site_json}:")
            for change in changes:
                print(change)
        else:
            print(f"{args.update_site_json}: already carries these values; nothing written.")

    if args.annotate:
        print(f"::notice title=installer published::{url}")
        print(f"::notice title=site.json windows_app::{url} | {human_megabytes(size)} | sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
