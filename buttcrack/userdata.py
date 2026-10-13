"""Where this program keeps state that belongs to the person using it.

The command line writes only where it is told, so nothing here concerns it.
This exists for the parts that have to choose a location for themselves: the
desktop app's PK9 campaign ledger and its saved assistant transcripts.

Those two used to be relative -- ``kryptos/pk9-results.sqlite3`` and
``~/buttcrack-assistant.jsonl``.  Relative paths are fine in a checkout, where
the current directory is the repository and the file lands somewhere meaningful.
They are wrong in an installed application, where there is no checkout and the
current directory belongs to whatever launched the process:

* resolved against the current directory, the ledger landed wherever the
  shortcut's working directory happened to be, and the parent directory usually
  did not exist, so SQLite refused to open the file and the campaign panel in
  the desktop window showed "Campaign ledger unavailable" to everyone, forever;
* resolved against the install directory, it would be deleted by the next
  upgrade, or would leave a non-empty directory behind that an uninstall then
  could not remove.

The per-user data directory avoids all of that: it is writable without
administrator rights, it is private to the account, and it survives an upgrade.
On Windows that is ``%LOCALAPPDATA%\\Buttcrack``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

__all__ = ["assistant_log", "data_dir", "pk9_ledger"]

#: Set this to put everything this module chooses somewhere specific.  Used by
#: the tests, and useful for a campaign that wants its data on another drive.
ENV_DATA_DIR = "BUTTCRACK_DATA_DIR"

#: Set this to point the PK9 campaign panel at one particular ledger.
ENV_LEDGER = "BUTTCRACK_PK9_LEDGER"

#: The directory name, in the platform's usual place for application data.
APP_DIR_NAME = "Buttcrack"


def _default_data_dir() -> Path:
    """This platform's convention for per-user application data."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    # Lower case on POSIX: the conventional spelling there, and it keeps a
    # Linux home directory looking tidy next to everything else in ~/.local.
    return Path(base) / APP_DIR_NAME.lower()


def data_dir(*, create: bool = True) -> Path:
    """The directory this program owns, created if it is not already there.

    Creating it is the point rather than a side effect: SQLite will not create a
    missing parent directory, so a caller that only got a path back would have to
    remember to make it, and the one that forgets is the bug this module exists
    to fix.
    """
    directory = Path(os.environ[ENV_DATA_DIR]) if os.environ.get(ENV_DATA_DIR) else _default_data_dir()
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _checkout_root() -> Path | None:
    """The repository this code is running from, or None if it was installed.

    Judged from the package's own location rather than the current directory,
    which is the whole point: an installed copy must not be able to mistake
    wherever it was launched from for a checkout.
    """
    root = Path(__file__).resolve().parent.parent
    return root if (root / "pyproject.toml").is_file() and (root / "buttcrack").is_dir() else None


def pk9_ledger() -> Path:
    """The PK9 campaign ledger, wherever this copy of the program keeps it.

    Three answers, in order:

    1. ``$BUTTCRACK_PK9_LEDGER``, the escape hatch for a campaign that lives
       somewhere specific.
    2. ``kryptos/pk9-results.sqlite3`` inside the checkout this code is running
       from, but only when that file already exists.  The campaign tooling in
       ``scripts/`` writes it there, and running from source should keep seeing
       the ledger it always has.
    3. The per-user data directory, which is what an installed copy uses.
    """
    override = os.environ.get(ENV_LEDGER)
    if override:
        path = Path(override)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    root = _checkout_root()
    if root is not None:
        existing = root / "kryptos" / "pk9-results.sqlite3"
        if existing.is_file():
            return existing

    return data_dir() / "pk9-results.sqlite3"


def assistant_log() -> Path:
    """Where the desktop window appends its saved assistant transcripts."""
    return data_dir() / "buttcrack-assistant.jsonl"


def instance_file() -> Path:
    """The desktop app's "I am running" marker: a small JSON file holding its URL.

    Read by a second launch and by the support path, so it is deliberately *not*
    the file that carries the exclusive lock.  On Windows a byte-range lock is
    mandatory: while a process holds one over byte 0, every read of that byte by
    any other process -- and by the same process through a second handle -- fails
    with ERROR_LOCK_VIOLATION.  A marker that was also the lock could therefore
    never be read by the launch it exists to inform.
    """
    return data_dir() / "desktop-instance.json"


def instance_lock_file() -> Path:
    """The file whose exclusive lock means "the desktop app is running".

    Nothing ever reads it, which is the point: a lock may sit on a file nobody
    needs to open, but not on one that carries a message.
    """
    return data_dir() / "desktop-instance.lock"
