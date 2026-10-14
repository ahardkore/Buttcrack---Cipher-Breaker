"""Opt-in desktop update checks. No startup checks, downloads or telemetry."""

from __future__ import annotations

import json
import queue
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import __version__

MANIFEST_URL = "https://ciphersolverpro.com/desktop-version.json"
UPDATES_URL = "https://ciphersolverpro.com/windows-app.html#updates"
MAX_MANIFEST_BYTES = 4096
TIMEOUT = 8


class UpdateError(Exception):
    """A check failed; the installed app can continue working offline."""


def version_parts(version: str) -> tuple[int, int, int]:
    """Compare stable releases numerically (1.10.0 is newer than 1.9.0)."""
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}", version):
        raise ValueError("Expected a stable major.minor.patch version")
    major, minor, patch = map(int, version.split("."))
    return major, minor, patch


def release_notes(items: object) -> tuple[str, ...]:
    """Accept short, plain-text bullets only; never render remote HTML or markup."""
    if not isinstance(items, list) or len(items) > 8:
        raise ValueError("Release notes must contain at most eight bullets")
    notes = []
    for item in items:
        if not isinstance(item, str) or not item.strip() or len(item) > 180:
            raise ValueError("Each release note must be 1–180 characters")
        if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in item):
            raise ValueError("Release notes must be single-line plain text")
        notes.append(item.strip())
    return tuple(notes)


@dataclass(frozen=True)
class UpdateResult:
    version: str
    newer: bool
    release_notes: tuple[str, ...] = ()


def update_dialog_text(result: UpdateResult, current_version: str = __version__) -> str:
    """The popup explains improvements before asking to open update information."""
    improvements = "\n".join(f"• {note}" for note in result.release_notes)
    if not improvements:
        improvements = "Release notes were not provided for this version. See the update information page."
    return (
        f"Version {result.version} is available. You have {current_version}.\n\n"
        f"What's new in {result.version}:\n{improvements}\n\n"
        "Open update information? Existing buyers can use their original download page.\n"
        "Download and run the new installer to upgrade; nothing is installed automatically."
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # One fixed HTTPS endpoint, not a remotely supplied destination.
        raise UpdateError("The update service moved. Please visit the update information page.")


def check_for_updates(current_version: str = __version__) -> UpdateResult:
    """Fetch only published version metadata; called solely at the user's request."""
    request = urllib.request.Request(
        MANIFEST_URL,
        headers={"Accept": "application/json", "Cache-Control": "no-cache"},
    )
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError("Manifest too large")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Manifest must be an object")
        latest = payload.get("version")
        return UpdateResult(
            latest, version_parts(latest) > version_parts(current_version),
            release_notes(payload.get("release_notes", [])),
        )
    except (OSError, urllib.error.URLError) as exc:
        raise UpdateError("Could not reach the update service. Check your connection and try again.") from exc
    except (ValueError, TypeError) as exc:
        raise UpdateError("The update service returned invalid version information. Please try again later.") from exc


class UpdateChecker:
    """Worker-to-UI mailbox. Only the main thread polls and changes UI state."""

    def __init__(self) -> None:
        self.busy = False
        self._results: queue.Queue[UpdateResult | UpdateError] = queue.Queue()

    def start(self) -> bool:
        if self.busy:
            return False
        self.busy = True

        def work() -> None:
            try:
                result = check_for_updates()
            except Exception as exc:
                result = exc if isinstance(exc, UpdateError) else UpdateError("Unable to check for updates. Try again later.")
            self._results.put(result)

        try:
            threading.Thread(target=work, name="buttcrack-update-check", daemon=True).start()
        except RuntimeError:
            self.busy = False
            raise UpdateError("Unable to start the update check. Try again later.") from None
        return True

    def poll(self) -> UpdateResult | UpdateError | None:
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            return None
        self.busy = False
        return result
