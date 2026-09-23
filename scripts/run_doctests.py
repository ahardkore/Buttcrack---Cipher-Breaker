#!/usr/bin/env python3
"""Run every doctest in the package.

``python3 -m doctest buttcrack/text.py`` does not work on a package that uses
relative imports, and doctests are not collected by ``unittest discover``, so
they rot silently unless something runs them.  This does::

    python3 scripts/run_doctests.py            # all modules
    python3 scripts/run_doctests.py --verbose  # show each example

Exits non-zero if any example fails, which is what CI wants.
"""

from __future__ import annotations

import argparse
import doctest
import importlib
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    import buttcrack

    attempted = failed = 0
    modules = 0
    for info in pkgutil.walk_packages(buttcrack.__path__, "buttcrack."):
        try:
            module = importlib.import_module(info.name)
        except Exception as error:  # pragma: no cover - a broken import is the point
            print(f"IMPORT FAILED {info.name}: {type(error).__name__}: {error}")
            failed += 1
            continue
        result = doctest.testmod(module, verbose=args.verbose, optionflags=doctest.NORMALIZE_WHITESPACE)
        modules += 1
        attempted += result.attempted
        failed += result.failed
        if result.attempted and not args.verbose:
            print(f"  {info.name}: {result.attempted} example(s), {result.failed} failed")

    print(f"\n{modules} modules, {attempted} doctest examples, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
