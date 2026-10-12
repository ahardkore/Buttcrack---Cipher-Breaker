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
    # 1. A --windowed build has no console, so PyInstaller leaves stdout and
    #    stderr as None, and the first print() -- including the traceback
    #    multiprocessing writes when a worker dies -- raises AttributeError
    #    instead of reporting anything.  Give them a sink before any other code
    #    runs so that a failing worker leaves a readable trace on disk rather
    #    than silent nothing.
    #
    #    This has to happen *before* the freeze_support() call below rather than
    #    after it: on Windows a spawned worker is this same executable re-run,
    #    and inside it freeze_support() *is* the worker -- it runs the payload
    #    and exits the process, so nothing written after it in this function
    #    ever executes in a child.
    from buttcrack.desktop import ensure_streams

    ensure_streams()

    # 2. On Windows, multiprocessing re-launches this executable to create a
    #    worker, and this is what tells the child it is a child.  Without it the
    #    child re-runs main() instead of the worker body -- a new app window per
    #    worker, recursively, until the machine gives up.  The solver uses fork
    #    where the platform has it and spawn where it does not, so this path is
    #    live on Windows and not merely defensive.
    multiprocessing.freeze_support()

    from buttcrack.desktop import main as desktop_main

    return desktop_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
