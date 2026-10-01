# packaging

Everything needed to turn the source tree into a downloadable, double-clickable
program for people who do not have Python and are never going to install it.

Full instructions, including where to host the result: **[`docs/windows-installer.md`](../docs/windows-installer.md)**.

```
windows/
  build.ps1              one command: freeze, smoke-test, package, checksum
  build.bat              double-clickable wrapper around build.ps1
  buttcrack.spec         PyInstaller recipe (works on macOS/Linux too)
  buttcrack.iss          Inno Setup installer definition
  entry_gui.py           entry point for Buttcrack.exe  (windowed)
  entry_cli.py           entry point for buttcrack.exe  (console)
  buttcrack-prompt.cmd   Start-menu shortcut: a prompt with the CLI on PATH
  assets/                buttcrack.ico, wizard bitmaps, the 1024px master
```

Quick version, on Windows with Python 3.9+ and Inno Setup 6.3+ installed:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

Output: `dist\installer\buttcrack-setup-<version>.exe`, plus its SHA-256.

Nothing here is a dependency of the project. `buttcrack` itself still installs
with `pip install .` and still has an empty `dependencies` list; PyInstaller is
fetched into a throwaway virtualenv (`.venv-build/`) that the build makes and
`.gitignore` ignores.
