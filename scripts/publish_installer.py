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
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_installer import human_megabytes, sha256_of  # noqa: E402  (path set up above)

#: The object name: an unguessable URL *is* the paywall for a $39.99 download
#: with no licence server, so the token is the product's lock and 64 bits of it
#: is the number the docs have published from the start.
TOKEN_BYTES = 8

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


def run_upload(path: Path, bucket: str, key: str, endpoint: str) -> None:
    if shutil.which("aws") is None:
        raise SystemExit(
            "the AWS CLI is not on PATH, and it is what performs the upload.\n"
            "  pip install awscli    # or: brew install awscli\n"
            "It only makes S3 API calls, so it works against R2 and B2 unchanged."
        )
    command = aws_command(path, bucket, key, endpoint)
    print("$ " + " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"upload failed with exit code {result.returncode}")


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

    if args.annotate:
        print(f"::notice title=installer published::{url}")
        print(f"::notice title=site.json windows_app::{url} | {human_megabytes(size)} | sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
