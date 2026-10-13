"""Guards for the Windows build, checked without a Windows machine.

The frozen build has one characteristic failure mode, and it is not "it does not
start": it is "it starts, breaks a cipher, and then dies the first time someone
opens the one panel whose module got trimmed".  PyInstaller's ``excludes`` list
takes precedence over the import graph, so naming a module that the package
actually uses turns a working build into a crash the smoke test cannot see --
which is exactly what ``sqlite3`` did to the PK9 Campaign panel.

Everything here is offline and platform-neutral, so it runs in the normal test
suite on Linux, on macOS, and on the Windows release runner alike.  The real
proof is ``packaging/windows/test-installer.ps1``, which installs and uninstalls
the finished product; these are the cheap checks that stop an obvious mistake
reaching it.
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging" / "windows"
SPEC = PACKAGING / "buttcrack.spec"
ISS = PACKAGING / "buttcrack.iss"
ENTRY_POINTS = (PACKAGING / "entry_gui.py", PACKAGING / "entry_cli.py")


def execute_spec() -> tuple[dict, list]:
    """Run ``buttcrack.spec`` with PyInstaller's build API replaced by recorders.

    The spec is executed rather than parsed so that every assertion below is
    made against the values PyInstaller would genuinely be handed, including
    ones computed at run time -- the version, the icon path, the DATAS list.
    Stubbing the four API names is enough to make the whole file run to the end.

    Returns the namespace the spec left behind and the calls it made.
    """
    calls: list = []

    class Recorder:
        """Stands in for Analysis/PYZ/EXE/COLLECT and remembers its arguments."""

        def __init__(self, kind: str, *args, **kwargs) -> None:
            self.kind, self.args, self.kwargs = kind, args, kwargs
            # Attributes the spec reads back off an Analysis.
            self.pure = [f"{kind}-pure"]
            self.binaries = [f"{kind}-binaries"]
            self.datas = [f"{kind}-datas"]
            self.scripts = [f"{kind}-scripts"]
            calls.append(self)

    def factory(kind: str):
        return lambda *args, **kwargs: Recorder(kind, *args, **kwargs)

    namespace = {
        "SPECPATH": str(PACKAGING),
        "Analysis": factory("Analysis"),
        "PYZ": factory("PYZ"),
        "EXE": factory("EXE"),
        "COLLECT": factory("COLLECT"),
        "__file__": str(SPEC),
        "__name__": "buttcrack_spec",
    }
    source = SPEC.read_text(encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):  # the spec prints a summary line
        exec(compile(source, str(SPEC), "exec"), namespace)
    return namespace, calls


def _importable(name: str) -> bool:
    """Whether ``name`` can be found, without importing it.

    ``find_spec`` reports a missing parent package by raising rather than by
    returning None, so ``tkinter.ttk`` on a Tk-less interpreter does not merely
    fail to be found -- it throws.
    """
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def imported_top_level_names() -> set[str]:
    """Every module name imported anywhere in the shipped code.

    Only ``buttcrack/`` and the two entry points are scanned, because that is
    exactly what PyInstaller walks to build the bundle.  Function-level imports
    count: the whole point is to catch a module reached only on a rarely-taken
    code path, which is how ``sqlite3`` slipped through in the first place.
    """
    paths = sorted((ROOT / "buttcrack").rglob("*.py")) + [p for p in ENTRY_POINTS if p.is_file()]
    names: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


class TestSpecExcludes(unittest.TestCase):
    """Nothing may be trimmed that the package can reach."""

    def setUp(self) -> None:
        self.namespace, _ = execute_spec()
        self.excludes = set(self.namespace["EXCLUDES"])

    def test_no_excluded_module_is_imported_by_the_package(self):
        # This is the regression guard for the sqlite3 bug: results_db.py imports
        # it, the PK9 Campaign panel uses results_db, and the build was dropping
        # it, so that panel raised ModuleNotFoundError in the shipped app while
        # every other screen worked.
        collisions = sorted(self.excludes & imported_top_level_names())
        self.assertEqual(
            collisions,
            [],
            f"buttcrack.spec excludes {collisions}, but the package imports it. "
            "The frozen build would raise ModuleNotFoundError at run time.",
        )

    def test_the_excludes_are_a_trimming_list_not_an_empty_gesture(self):
        # A guard against "fix the test by emptying the list": the weight is only
        # worth trimming if something is actually being trimmed.
        self.assertGreater(len(self.excludes), 5)

    def test_large_stdlib_modules_that_nothing_uses_stay_excluded(self):
        for name in ("idlelib", "lib2to3", "pydoc_data", "test"):
            self.assertIn(name, self.excludes)


class TestSpecPayload(unittest.TestCase):
    """The data files the frozen app needs at run time are the ones it ships."""

    def setUp(self) -> None:
        self.namespace, self.calls = execute_spec()

    def test_every_data_source_exists_on_disk(self):
        # A missing source is a build failure, or worse, a bundle that starts
        # and cannot solve anything because the n-gram tables were not in it.
        for source, _target in self.namespace["DATAS"]:
            self.assertTrue(Path(source).exists(), f"spec DATAS points at a missing path: {source}")

    def test_the_language_model_and_web_ui_are_both_shipped(self):
        sources = [str(source) for source, _ in self.namespace["DATAS"]]
        self.assertIn(str(ROOT / "buttcrack" / "data"), sources)
        self.assertIn(str(ROOT / "buttcrack" / "static"), sources)

    def test_the_model_tables_are_actually_in_the_data_directory(self):
        # The directory being listed is not the same as the tables being in it.
        data = ROOT / "buttcrack" / "data"
        for table in ("english_quadgrams.txt.gz", "english_trigrams.txt.gz", "english_bigrams.txt.gz"):
            self.assertTrue((data / table).is_file(), f"missing language model table: {table}")

    def test_hidden_imports_are_real_modules(self):
        # A HIDDEN name that is a typo is invisible until the day the bundle is
        # opened and the thing it was standing in for turns out not to be there.
        missing = [name for name in self.namespace["HIDDEN"] if not _importable(name)]
        if not _importable("tkinter"):
            # This suite runs on machines whose Python was built without tcl/tk
            # (including this repository's CI container), where tkinter is
            # legitimately unimportable.  build.ps1 refuses to build in that
            # situation, so there is nothing to catch -- but every other HIDDEN
            # name still has to resolve.
            missing = [name for name in missing if not name.startswith("tkinter")]
        self.assertEqual(missing, [], f"buttcrack.spec HIDDEN names modules that do not exist: {missing}")

    def test_tkinter_is_declared_because_the_desktop_window_needs_it(self):
        # A silently missing Tk downgrades the app to a console loop with no
        # error anywhere, which is precisely the regression worth catching here.
        self.assertIn("tkinter", self.namespace["HIDDEN"])


class TestBuildOutputShape(unittest.TestCase):
    """The spec and the installer have to agree about what was built."""

    def setUp(self) -> None:
        self.namespace, self.calls = execute_spec()

    def _kinds(self, kind: str) -> list:
        return [call for call in self.calls if call.kind == kind]

    def test_the_build_produces_exactly_two_executables(self):
        exes = self._kinds("EXE")
        self.assertEqual(len(exes), 2)
        self.assertEqual({call.kwargs["name"] for call in exes}, {"Buttcrack Desktop", "buttcrack"})

    def test_the_two_executable_names_differ_by_more_than_case(self):
        # The bug this exists for: the first Windows build named them
        # Buttcrack.exe and buttcrack.exe.  On a case-insensitive filesystem --
        # Windows, and macOS by default -- those are the same file, so COLLECT
        # kept one and discarded the other, both of build.ps1's existence checks
        # still passed, and the Start-menu shortcut launched the console program.
        # Nothing in the repository noticed until an installer test read the
        # shortcut's target back on a real Windows machine.
        names = [call.kwargs["name"] for call in self._kinds("EXE")]
        self.assertEqual(
            len({name.lower() for name in names}),
            len(names),
            f"executable names collide on a case-insensitive filesystem: {names}",
        )

    def test_the_windowed_executable_has_no_console_and_the_cli_does(self):
        by_name = {call.kwargs["name"]: call.kwargs for call in self._kinds("EXE")}
        self.assertFalse(by_name["Buttcrack Desktop"]["console"], "the desktop app must be windowed")
        self.assertTrue(by_name["buttcrack"]["console"], "buttcrack.exe must be a console app")

    def test_upx_is_off_because_it_gets_flagged_by_antivirus(self):
        for call in self._kinds("EXE"):
            self.assertFalse(call.kwargs["upx"])

    def test_one_collect_holds_both_executables_so_they_share_a_runtime(self):
        collects = self._kinds("COLLECT")
        self.assertEqual(len(collects), 1, "a second COLLECT would duplicate the runtime and the model")
        self.assertEqual(collects[0].kwargs["name"], "Buttcrack")

    def test_the_installer_looks_for_the_directory_the_spec_builds(self):
        # {#SourceDir} is "..\..\dist\Buttcrack" relative to packaging\windows.
        iss = ISS.read_text(encoding="utf-8")
        self.assertIn('#define SourceDir     "..\\..\\dist\\Buttcrack"', iss)
        self.assertEqual(self._kinds("COLLECT")[0].kwargs["name"], "Buttcrack")

    def test_the_installer_installs_the_executables_the_spec_produces(self):
        iss = ISS.read_text(encoding="utf-8")
        built = {call.kwargs["name"] for call in self._kinds("EXE")}
        # Anchored on the define *name*, not on a line that merely contains
        # "ExeName": the version define interpolates AppExeName inside
        # GetStringFileInfo(...) and would otherwise be read as a filename.
        declared = set(re.findall(r"^#define\s+\w*ExeName\s+\"([^\"]+)\"", iss, re.MULTILINE))
        # "Buttcrack Desktop.exe" has a space in it, so the define has to be read
        # as a whole quoted value rather than split on the first space.
        self.assertIn('AppExeName    "Buttcrack Desktop.exe"', iss)
        self.assertEqual(declared, {f"{name}.exe" for name in built})

    def test_the_installer_and_the_app_agree_about_the_display_name(self):
        iss = ISS.read_text(encoding="utf-8")
        self.assertIn('#define AppName       "Buttcrack"', iss)
        self.assertEqual(self._kinds("COLLECT")[0].kwargs["name"], "Buttcrack")


def call_order(path: Path) -> list[str]:
    """Names of the calls made inside ``main()``, in source order.

    Parsed rather than searched: the comment above these calls discusses them by
    name, so a substring search cannot tell the call from the sentence about it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    calls: list[tuple[int, str]] = []
    for node in ast.walk(main):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            calls.append((node.lineno, func.attr))
        elif isinstance(func, ast.Name):
            calls.append((node.lineno, func.id))
    return [name for _line, name in sorted(calls)]


class TestEntryPoints(unittest.TestCase):
    """The two things a frozen process must do before anything else."""

    def _source(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_both_entry_points_call_freeze_support(self):
        # Without it a spawned Windows worker re-runs main() instead of the
        # worker body: a new app window per worker, recursively.
        for path in ENTRY_POINTS:
            self.assertIn("freeze_support()", self._source(path), f"{path.name} never calls freeze_support()")

    def test_the_windowed_entry_point_fixes_the_streams_before_freezing(self):
        # In a spawned child freeze_support() *is* the worker, so anything after
        # it in main() never runs there -- and a windowed build has no streams
        # for the worker's traceback to land in.
        order = call_order(PACKAGING / "entry_gui.py")
        self.assertIn("ensure_streams", order, "entry_gui.py never calls ensure_streams()")
        self.assertIn("freeze_support", order, "entry_gui.py never calls freeze_support()")
        self.assertLess(
            order.index("ensure_streams"),
            order.index("freeze_support"),
            "ensure_streams() must run before freeze_support(), or a dying worker reports nothing",
        )

    def test_the_console_entry_point_runs_the_real_cli(self):
        self.assertIn("from buttcrack.cli import main as cli_main", self._source(PACKAGING / "entry_cli.py"))


class TestTraySurvivesTheShell(unittest.TestCase):
    """The one Win32 message the tray cannot do without.

    Explorer owns the notification area and rebuilds it after a crash, an update
    or a "restart Explorer".  Every icon in the old one is gone, and the only
    notice is a broadcast message -- so an app that does not listen for it keeps
    running with no icon at all.  For this app that is worse than cosmetic:
    closing the window hides it when the tray is up, so the process would be
    left invisible with no way back except Task Manager.

    The tray cannot be exercised off Windows, so this is the cheap structural
    check in the style of the rest of this file.
    """

    SOURCE = ROOT / "buttcrack" / "_wintray.py"

    def test_the_tray_listens_for_the_shell_being_rebuilt(self):
        source = self.SOURCE.read_text(encoding="utf-8")
        self.assertIn('RegisterWindowMessageW("TaskbarCreated")', source)
        self.assertIn("taskbar_created", source)

    def test_the_icon_can_be_installed_twice(self):
        # Adding the icon at startup and again after the shell comes back has to
        # be one code path, or the second one drifts and stops working.
        import buttcrack._wintray as tray

        self.assertTrue(hasattr(tray.TrayIcon, "_add_icon"))

    def test_the_windowed_entry_point_hides_rather_than_quits_only_with_a_tray(self):
        # desktop.py must keep tying the close button to whether there is an
        # icon to bring the window back from.
        source = (ROOT / "buttcrack" / "desktop.py").read_text(encoding="utf-8")
        self.assertIn('root.protocol("WM_DELETE_WINDOW", hide if tray.active else shutdown)', source)


class TestVersionAgreement(unittest.TestCase):
    """One version, in the places that are read by a person or a program."""

    def test_pyproject_matches_the_package(self):
        import buttcrack

        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        declared = next(
            line.split("=")[1].strip().strip('"') for line in pyproject.splitlines() if line.startswith("version =")
        )
        self.assertEqual(
            declared,
            buttcrack.__version__,
            "pyproject.toml and buttcrack.__version__ disagree; the installer "
            "takes its version from the built exe, so this would ship a "
            "mislabelled download",
        )

    def test_the_version_is_a_release_version(self):
        import buttcrack

        parts = buttcrack.__version__.split(".")
        self.assertGreaterEqual(len(parts), 3, buttcrack.__version__)
        self.assertTrue(all(part.isdigit() for part in parts[:3]), buttcrack.__version__)

    def test_the_download_page_advertises_the_version_being_built(self):
        # The storefront is a separate artefact from the installer and drifts
        # quietly.  A buyer told they are getting 1.1.0 while the file is named
        # 1.2.0 cannot tell whether they downloaded the right thing, and the
        # SHA-256 published beside the link stops matching the name beside it.
        import json

        import buttcrack

        site = ROOT / "ventures" / "cipher-solver-web" / "site.json"
        if not site.is_file():
            self.skipTest("this checkout does not include the storefront")
        advisory = (json.loads(site.read_text(encoding="utf-8")).get("windows_app") or {}).get("version")
        if not advisory:
            self.skipTest("the storefront does not advertise a Windows version")
        self.assertEqual(
            advisory,
            buttcrack.__version__,
            "site.json advertises a different Windows version than the package "
            "builds; bump both together and regenerate the pages",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
