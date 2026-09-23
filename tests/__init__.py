"""Buttcrack's test suite.

Standard library ``unittest`` only -- the project has no runtime dependencies and
no test dependencies either, so ``python3 -m unittest discover -s tests`` works on
a bare interpreter::

    python3 -m unittest discover -s tests          # the fast suite
    BUTTCRACK_SLOW=1 python3 -m unittest discover -s tests   # plus Playfair, Bifid
"""

from __future__ import annotations
