# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the Buttcrack desktop build.

Produces one application directory containing two executables that share a
single copy of Python and of the language model:

    Buttcrack Desktop.exe    windowed  -- the desktop app (Start-menu shortcut)
    buttcrack.exe            console   -- the CLI, identical to `pip install buttcrack`

The windowed one is *not* called Buttcrack.exe, and that is not a style choice.
Windows and macOS filesystems are case-insensitive by default, so on those
platforms `Buttcrack.exe` and `buttcrack.exe` are the same file.  COLLECT would
write one over the other, the bundle would contain a single program, and the
Start-menu shortcut would launch whichever of the two happened to survive.
That is what the first Windows build of this installer did: it shipped a
"desktop app" whose shortcut opened the command line.  Nothing caught it until
an installer test read the shortcut's target back and compared it to the file it
expected -- so the names are asserted distinct below as well.

Build it with the wrapper, which also makes the installer::

    packaging\\windows\\build.ps1

or on its own, from the repository root::

    pyinstaller --clean --noconfirm packaging/windows/buttcrack.spec

A one-*directory* build is deliberate.  One-file would unpack 30 MB of n-gram
tables into %TEMP% on every launch, which is slow, trips antivirus heuristics,
and leaves the data on disk twice.  The installer hides the directory behind a
shortcut, so the user never sees the difference.

The spec is cross-platform as written: on macOS and Linux it produces the same
pair of binaries without the .exe suffix.  Only the installer step below it is
Windows-specific.
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

# SPECPATH is injected by PyInstaller; __file__ is not defined when a spec runs.
HERE = Path(SPECPATH).resolve()  # noqa: F821
ROOT = HERE.parent.parent
PACKAGE = ROOT / "buttcrack"
ASSETS = HERE / "assets"

sys.path.insert(0, str(ROOT))
from buttcrack import __version__ as VERSION  # noqa: E402

IS_WINDOWS = sys.platform == "win32"
ICON = str(ASSETS / "buttcrack.ico") if (ASSETS / "buttcrack.ico").is_file() else None

# --------------------------------------------------------------------------- #
# payload
# --------------------------------------------------------------------------- #

# `lang.py` does `Path(__file__).parent / "data"` and `server.py` does the same
# for "static", so the tree has to keep its shape inside the bundle.  Shipping
# them as datas (not as a zip) is also what lets the .gz tables be mmap-free
# plain reads at startup.
DATAS = [
    (str(PACKAGE / "data"), "buttcrack/data"),
    (str(PACKAGE / "static"), "buttcrack/static"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "NOTICE"), "."),
]
# Preserve license texts for the maintained provider and its wheel dependencies.
# A core-only build may omit these; the Windows AES smoke test may not.
for provider_name in ("cryptography", "cffi", "pycparser"):
    try:
        provider = distribution(provider_name)
    except PackageNotFoundError:
        continue
    for resource in provider.files or []:
        if "licenses" in resource.parts and resource.name.upper().startswith(("LICENSE", "COPYING")):
            DATAS.append((str(provider.locate_file(resource)), f"licenses/{provider_name}"))

if ICON:
    # desktop.py looks for this next to the executable, for the Tk window icon.
    DATAS.append((ICON, "."))

# Nothing in buttcrack is imported dynamically -- every cipher module is a
# plain `from .x import Y` in buttcrack/ciphers/__init__.py -- so the analyser
# finds the lot by itself.  Only the optional imports need naming:
#
# * desktop/_wintray are reached through a late import inside a function;
# * tkinter is imported inside `run_window()`, and while the analyser does read
#   function bodies, a silently missing Tk would downgrade the app to a console
#   loop with no error anywhere.  Naming it here turns that into a build-time
#   warning instead of a shipped regression.
#
# Both executables declare it: COLLECT writes the shared tcl/tk runtime once,
# so the console build costs a couple of hundred kilobytes for it and gains a
# `buttcrack app` that behaves identically to the shortcut.
HIDDEN = [
    "buttcrack.desktop",
    "buttcrack.modern",
    "buttcrack._wintray",
    "tkinter",
    "tkinter.ttk",
]

# The core solver has zero dependencies; the AES provider is bundled separately.
# The only weight to trim here is the standard
# library's own baggage.  Everything here is both large and unreachable from
# the solver.  Note what is *not* excluded:
#
# * ssl     -- too much of the standard library imports it opportunistically
#              for it to be worth 5 MB;
# * sqlite3 -- buttcrack/results_db.py imports it at the top of the module and
#              the PK9 Campaign panel in the desktop window is built on it.  It
#              used to be listed here, which meant the frozen app started,
#              solved ciphers, and then died with ModuleNotFoundError the first
#              time someone opened that panel.  tests/test_windows_bundle.py
#              now fails the build if anything listed below is reachable from
#              the package at all.
EXCLUDES = [
    "pydoc_data",
    "lib2to3",
    "distutils",
    "setuptools",
    "pip",
    "test",
    "idlelib",
    "asyncio",
    "xmlrpc",
    "turtle",
    "turtledemo",
    "numpy",
    "PIL",
]


def analysis(script: str) -> Analysis:  # noqa: F821
    return Analysis(  # noqa: F821
        [str(HERE / script)],
        pathex=[str(ROOT)],
        binaries=[],
        datas=DATAS,
        hiddenimports=HIDDEN,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=EXCLUDES,
        noarchive=False,
        optimize=0,
    )


gui_a = analysis("entry_gui.py")
cli_a = analysis("entry_cli.py")

gui_pyz = PYZ(gui_a.pure)  # noqa: F821
cli_pyz = PYZ(cli_a.pure)  # noqa: F821

# --------------------------------------------------------------------------- #
# Windows file properties
# --------------------------------------------------------------------------- #

#: Version strings may carry a suffix (1.2.0rc1); the Win32 resource wants four
#: plain integers, so take what is numeric and pad.
_QUAD = ", ".join(
    str(int(p) if p.isdigit() else 0)
    for p in (VERSION.split("+")[0].split("-")[0] + ".0.0.0").split(".")[:4]
)


def version_file(filename: str, description: str) -> str | None:
    """Write a VERSIONINFO resource and return its path (None off Windows).

    This is what right-click -> Properties -> Details shows, and what software
    inventories and SmartScreen reputation records read.  An unsigned binary
    with no metadata at all is the single most suspicious thing you can hand a
    Windows machine, so it is worth the twenty lines.
    """
    if not IS_WINDOWS:
        return None
    path = HERE / f"version_info_{Path(filename).stem}.txt"
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({_QUAD}), prodvers=({_QUAD}), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'ahardkore'),
      StringStruct('FileDescription', '{description}'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'buttcrack'),
      StringStruct('LegalCopyright', 'MIT Licence'),
      StringStruct('OriginalFilename', '{filename}'),
      StringStruct('ProductName', 'Buttcrack'),
      StringStruct('ProductVersion', '{VERSION}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ]
)
""",
        encoding="utf-8",
    )
    return str(path)


COMMON = dict(
    exclude_binaries=True,
    bootloader_ignore_signals=False,
    debug=False,
    strip=False,
    upx=False,  # UPX-packed binaries are a reliable way to get flagged by antivirus
    icon=ICON,
    contents_directory="_internal",
)

#: The two program names, kept here so the collision below cannot creep back in.
#: `buttcrack` has to stay as it is: it is what the README, the installer's PATH
#: entry and the Start-menu command-prompt shortcut all promise.
GUI_NAME = "Buttcrack Desktop"
CLI_NAME = "buttcrack"

if GUI_NAME.lower() == CLI_NAME.lower():
    raise SystemExit(
        f"[buttcrack] {GUI_NAME}.exe and {CLI_NAME}.exe differ only in letter case. "
        "On a case-insensitive filesystem -- Windows, and macOS by default -- "
        "COLLECT would silently keep one and discard the other."
    )

gui_exe = EXE(  # noqa: F821
    gui_pyz, gui_a.scripts, [],
    name=GUI_NAME,
    console=False,
    version=version_file(f"{GUI_NAME}.exe", "Buttcrack - automatic cipher breaker"),
    **COMMON,
)
cli_exe = EXE(  # noqa: F821
    cli_pyz, cli_a.scripts, [],
    name=CLI_NAME,
    console=True,
    version=version_file(f"{CLI_NAME}.exe", "Buttcrack command line"),
    **COMMON,
)

# One COLLECT for both: identical binaries and data files are written once, so
# the pair costs barely more on disk than either alone.
coll = COLLECT(  # noqa: F821
    gui_exe,
    gui_a.binaries,
    gui_a.datas,
    cli_exe,
    cli_a.binaries,
    cli_a.datas,
    strip=False,
    upx=False,
    name="Buttcrack",
)

print(f"[buttcrack] spec: version {VERSION}, icon {'yes' if ICON else 'no'}, "
      f"output {os.path.join('dist', 'Buttcrack')} ({GUI_NAME}.exe, {CLI_NAME}.exe)")
