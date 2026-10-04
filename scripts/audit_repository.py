#!/usr/bin/env python3
"""Fast, offline integrity checks for tracked repository sources and documentation.

This intentionally complements (rather than replaces) the unit, package, site,
and browser checks.  It covers files outside the installable package that are
still published in the repository: every tracked Python source must parse, and
inline relative Markdown links must resolve from the document that contains
them.  Network URLs and fragment-only links are deliberately out of scope.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SUFFIX = ".py"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkdn"}
# Match ordinary inline links and images.  Reference-style links are not used in
# the repository and require a full Markdown parser to resolve correctly.
INLINE_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:")


def tracked_files() -> list[Path]:
    """Return tracked working-tree files, with a useful fallback outside Git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
        )
    except (OSError, subprocess.CalledProcessError):
        return [path for path in ROOT.rglob("*") if path.is_file()]
    return [ROOT / value for value in result.stdout.decode("utf-8").split("\0") if value]


def python_syntax_errors(files: list[Path]) -> list[str]:
    """Parse Python without creating ``__pycache__`` side effects."""
    errors: list[str] = []
    for path in files:
        if path.suffix != PYTHON_SUFFIX:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as error:
            if isinstance(error, SyntaxError):
                where = f":{error.lineno}:{error.offset or 0}"
                message = error.msg
            else:
                where = ""
                message = str(error)
            errors.append(f"{path.relative_to(ROOT)}{where}: {message}")
    return errors


def local_link_target(raw_target: str) -> str | None:
    """Return a local path target, or ``None`` for external/fragment links."""
    target = raw_target.strip()
    # Markdown permits an optional quoted title after a destination.  There are
    # no spaces in this repository's local paths, so the first token is enough.
    target = target.split(maxsplit=1)[0].strip("<>")
    if not target or target.startswith(("#", "/")):
        return None
    if target.lower().startswith(EXTERNAL_SCHEMES) or "://" in target:
        return None
    return unquote(target.split("#", 1)[0].split("?", 1)[0])


def markdown_link_errors(files: list[Path]) -> list[str]:
    """Find unresolved inline local links in tracked Markdown files."""
    errors: list[str] = []
    for path in files:
        if path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{path.relative_to(ROOT)}: cannot read Markdown: {error}")
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in INLINE_LINK.finditer(line):
                target = local_link_target(match.group(1))
                if target is not None and not (path.parent / target).exists():
                    errors.append(f"{path.relative_to(ROOT)}:{line_number}: missing local link target: {target}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="print only errors")
    args = parser.parse_args()

    files = tracked_files()
    python_errors = python_syntax_errors(files)
    markdown_errors = markdown_link_errors(files)
    errors = python_errors + markdown_errors

    if not args.quiet:
        print("Repository integrity audit")
        print(f"  tracked files:          {len(files)}")
        print(f"  Python sources parsed:  {sum(path.suffix == PYTHON_SUFFIX for path in files)}")
        print(f"  Markdown files checked: {sum(path.suffix.lower() in MARKDOWN_SUFFIXES for path in files)}")
        print(f"  Python syntax defects:  {len(python_errors)}")
        print(f"  local-link defects:     {len(markdown_errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    if not args.quiet:
        print("PASS: tracked Python sources parse and local Markdown links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
