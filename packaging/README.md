# packaging

Everything needed to turn the source tree into a downloadable, double-clickable
program for people who do not have Python and are never going to install it.

Full instructions, including where to host the result: **[`docs/windows-installer.md`](../docs/windows-installer.md)**.

```
windows/
  build.ps1              one command: freeze, smoke-test, package, checksum
  build.bat              double-clickable wrapper around build.ps1
  test-installer.ps1     install, exercise, uninstall, and check nothing is left
  buttcrack.spec         PyInstaller recipe (works on macOS/Linux too)
  buttcrack.iss          Inno Setup installer definition
  entry_gui.py           entry point for the windowed build
  entry_cli.py           entry point for buttcrack.exe  (console)
                         -- the windowed build cannot be called Buttcrack.exe;
                            see the note in buttcrack.spec
  buttcrack-prompt.cmd   Start-menu shortcut: a prompt with the CLI on PATH
  assets/                buttcrack.ico, wizard bitmaps, the 1024px master
```

Quick version, on Windows with Python 3.9+ and Inno Setup 6.3+ installed:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

Output: `dist\installer\buttcrack-setup-<version>.exe`, plus its SHA-256.

No Windows machine to hand? CI builds and verifies the same file, and
`scripts\fetch_installer.py` lists what is live and fetches one, digest checked:

```console
python scripts\fetch_installer.py --list
python scripts\fetch_installer.py --version 1.2.0
```

Then check it actually installs, runs and uninstalls:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\test-installer.ps1 `
    -Installer dist\installer\buttcrack-setup-<version>.exe
```

Both are run on `windows-latest` for every push by the `installer` job in
`.github/workflows/release.yml`, so the wizard is verified on every change rather
than on the day someone downloads it.

Then put it where buyers can get it -- an unguessable name on storage you
control, with the URL, size and SHA-256 printed for `site.json`:

```console
python scripts\publish_installer.py dist\installer\buttcrack-setup-<version>.exe --dry-run
```

`.github/workflows/publish-installer.yml` does the same from CI, against the
artifact of a run that already passed the test above. See
`docs/windows-installer.md` for the five environment variables.

Nothing here is a dependency of the project. `buttcrack` itself still installs
with `pip install .` and still has an empty `dependencies` list; PyInstaller is
fetched into a throwaway virtualenv (`.venv-build/`) that the build makes and
`.gitignore` ignores.
