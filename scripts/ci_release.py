"""CI artifact checks: deterministic, offline, and platform-neutral."""

import hashlib
import json
import sys
from pathlib import Path


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dist")
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    if command == "size":
        limit = int(sys.argv[3]) * 1024 * 1024 if len(sys.argv) > 3 else 250 * 1024 * 1024
        total = sum(p.stat().st_size for p in files)
        print(f"{total} bytes")
        if not files:
            raise SystemExit("no release artifact produced")
        if total > limit:
            raise SystemExit(f"artifact exceeds {limit} bytes")
    elif command == "sha256":
        print(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2))
    else:
        raise SystemExit("usage: ci_release.py size|sha256 DIRECTORY [MB]")


if __name__ == "__main__":
    main()
