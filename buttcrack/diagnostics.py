"""One block of text that answers "what am I running, and where is it?".

A frozen Windows build has no console, so the two questions a support email
always starts with -- *which version, and what does its data directory look
like* -- had no answer a user could produce.  Everything here is local: no
network calls, no telemetry, and nothing that a user could not read out of the
window themselves.  ``buttcrack doctor`` prints it from a terminal, and the
desktop window's "Copy diagnostics" button puts the same block on the
clipboard.

The layout is deliberately plain text with aligned columns: it survives being
pasted into an email, a forum post or an issue, which is the whole point.
"""

from __future__ import annotations

import os
import platform
import socket
import sys
from pathlib import Path

from . import __version__, userdata

#: Wider than any label below, so the values line up when the block is read as
#: plain text rather than rendered markdown.
_LABEL_WIDTH = 18


def _row(label: str, value: str) -> str:
    return f"{label:<{_LABEL_WIDTH}}{value}"


def _writable(directory: Path) -> tuple[bool, str]:
    """Whether a file can actually be created in ``directory``, and why not."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".buttcrack-write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as error:
        return False, f"NOT WRITABLE ({error})"
    return True, "writable"


def _human_bytes(count: int) -> str:
    if count < 1024:
        return f"{count} bytes"
    if count < 1024 * 1024:
        return f"{count / 1024:.1f} KB"
    return f"{count / (1024 * 1024):.1f} MB"


def _model_row() -> tuple[str, bool]:
    """The language model's size, or the reason it did not load."""
    try:
        from .lang import LANGUAGES, get_model

        model = get_model("english")
        return (
            f"{model.ngram_count(4):,} quadgrams, {len(model.words):,} words, "
            f"{len(LANGUAGES)} languages",
            True,
        )
    except Exception as error:  # a broken install is exactly what this reports
        return f"FAILED TO LOAD: {type(error).__name__}: {error}", False


def _port_row() -> tuple[str, bool]:
    """Whether the address people bookmark is free, and what would be used."""
    from .desktop import LOCAL_HOST, PREFERRED_PORT, free_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        try:
            probe.bind((LOCAL_HOST, PREFERRED_PORT))
        except OSError:
            chosen = free_port()
            return (
                f"{PREFERRED_PORT} is busy; {LOCAL_HOST}:{chosen} is free",
                True,
            )
    return f"{LOCAL_HOST}:{PREFERRED_PORT} is free", True


def report_lines(
    *,
    port: int | None = None,
    tray: bool | None = None,
    last_job: str | None = None,
) -> tuple[list[str], list[str]]:
    """The diagnostics block, and the list of things wrong with it (usually empty).

    ``port``, ``tray`` and ``last_job`` are only known to a running window, so
    they are passed in rather than probed: the CLI has no window, and pretending
    otherwise would print a port the user is not actually being served on.
    """
    from . import CIPHERS
    from .desktop import is_frozen, log_path

    problems: list[str] = []
    lines = [
        _row("buttcrack", __version__),
        _row(
            "python",
            f"{sys.version.split()[0]} ({platform.python_implementation()}) on {platform.platform()}",
        ),
        _row("build", "frozen executable" if is_frozen() else "source checkout"),
        _row("ciphers", f"{len(CIPHERS)} registered"),
    ]

    directory = userdata.data_dir()
    writable, note = _writable(directory)
    lines.append(_row("data directory", f"{directory}  ({note})"))
    if not writable:
        problems.append(f"the data directory is not writable: {directory}")

    log = log_path()
    if log.is_file():
        lines.append(_row("log file", f"{log}  ({_human_bytes(log.stat().st_size)})"))
    else:
        lines.append(_row("log file", f"{log}  (not created yet)"))

    model_row, model_ok = _model_row()
    lines.append(_row("language model", model_row))
    if not model_ok:
        problems.append("the language model would not load")

    port_row, port_ok = _port_row()
    lines.append(_row("address", f"{port_row}" + (f" (currently serving port {port})" if port else "")))
    if not port_ok:
        problems.append("no usable loopback port")

    if tray is not None:
        lines.append(_row("tray icon", "active" if tray else "not available"))
    if last_job:
        lines.append(_row("last search", last_job))

    if os.environ.get(userdata.ENV_DATA_DIR):
        # Worth saying out loud: with this set, the "data directory" above is
        # not the one a double-click would use.
        lines.append(_row("note", f"{userdata.ENV_DATA_DIR} overrides the data directory"))
    return lines, problems


def report_text(**kwargs: object) -> str:
    """The block as one string, ready for the clipboard or a terminal."""
    lines, problems = report_lines(**kwargs)  # type: ignore[arg-type]
    body = "\n".join(lines)
    if problems:
        return body + "\n\nproblems:\n" + "\n".join(f"  - {line}" for line in problems)
    return body + "\n\nno problems found."
