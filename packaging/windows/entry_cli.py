"""Entry point for ``buttcrack.exe`` -- the console build.

The same command line as ``pip install buttcrack`` gives you, so everything in
the README works verbatim once the installer has put this directory on PATH::

    buttcrack "Wkh txlfn eurzq ira"
    buttcrack identify --file puzzle.txt
    buttcrack serve --port 8080
"""

from __future__ import annotations

import multiprocessing
import sys


def main() -> int:
    # See entry_gui.py: a frozen Windows build re-launches itself to spawn
    # multiprocessing workers, and this is what tells the child it is a child.
    multiprocessing.freeze_support()

    from buttcrack.cli import main as cli_main

    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
