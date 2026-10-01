"""Entry point for ``Buttcrack.exe`` -- the windowed desktop build.

This is what the Start-menu shortcut runs.  It is deliberately almost empty:
everything it does belongs to :mod:`buttcrack.desktop`, which also has to work
from a plain ``pip install``.  The only things that live here are the two
pieces of housekeeping a *frozen* process needs before any other code runs.
"""

from __future__ import annotations

import multiprocessing
import sys


def main() -> int:
    # 1. On Windows, multiprocessing re-launches this executable to create a
    #    worker.  Without freeze_support() the child re-runs main() instead of
    #    the worker body -- a new app window per worker, recursively, until the
    #    machine gives up.  The solver only forks today (so it never reaches
    #    here on Windows), but this costs nothing and the failure mode it
    #    prevents is spectacular.
    multiprocessing.freeze_support()

    # 2. A --windowed build has no console, so PyInstaller sets stdout/stderr
    #    to None.  Anything that prints would raise AttributeError before the
    #    window appears.  Give them a sink first, then import the app.
    from buttcrack.desktop import ensure_streams

    ensure_streams()

    from buttcrack.desktop import main as desktop_main

    return desktop_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
