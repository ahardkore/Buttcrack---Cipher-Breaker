"""The package claims to run on Python 3.9; this test keeps that claim honest.

``requires-python = ">=3.9"`` in ``pyproject.toml`` is a promise, and the ways it
breaks are invisible on a modern interpreter:

* a PEP 604 union (``str | None``) in an annotation is *evaluated at import time*
  unless the module has ``from __future__ import annotations``, and on 3.9 that
  raises ``TypeError: unsupported operand type(s) for |``. It happened here once,
  in the public ``encrypt()`` helper, and took a CI run on 3.9 to find;
* syntax added in 3.10 and later parses fine on the interpreter running the
  tests and fails to parse on the oldest one supported.

Both are checked statically with ``ast``, in well under a second, so the answer
does not depend on having a 3.9 interpreter to hand.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MINIMUM = (3, 9)

#: Directories that ship with the project and are run by users or by CI.
SCANNED = ("buttcrack", "tests", "scripts", "examples")


def python_files() -> list[Path]:
    out: list[Path] = []
    for name in SCANNED:
        out.extend(p for p in (ROOT / name).rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def has_future_annotations(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def pep604_lines(tree: ast.AST) -> list[int]:
    """Lines where an annotation uses ``X | Y`` -- deferred only by the future import."""
    found: list[int] = []
    for node in ast.walk(tree):
        annotations = []
        if isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        elif isinstance(node, ast.arg):
            annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotations.append(node.returns)
        for annotation in annotations:
            if annotation is None:
                continue
            if any(isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr) for sub in ast.walk(annotation)):
                found.append(getattr(node, "lineno", 0))
    return sorted(set(found))


class TestSupportedInterpreterFloor(unittest.TestCase):
    def test_every_file_parses_as_the_oldest_supported_version(self):
        for path in python_files():
            with self.subTest(file=str(path.relative_to(ROOT))):
                source = path.read_text(encoding="utf-8")
                try:
                    ast.parse(source, filename=str(path), feature_version=MINIMUM)
                except SyntaxError as error:
                    self.fail(f"{path.relative_to(ROOT)}:{error.lineno}: {error.msg}")

    def test_pep604_annotations_are_deferred(self):
        offenders = []
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            lines = pep604_lines(tree)
            if lines and not has_future_annotations(tree):
                offenders.append(f"{path.relative_to(ROOT)}:{lines[0]}")
        self.assertEqual(
            offenders,
            [],
            "these modules evaluate `X | Y` annotations at import time, which raises "
            f"TypeError on Python {MINIMUM[0]}.{MINIMUM[1]}; add "
            "`from __future__ import annotations`",
        )

    def test_pyproject_agrees_with_the_floor_tested_here(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'requires-python\s*=\s*">=\s*(\d+)\.(\d+)"', text)
        self.assertIsNotNone(match, "pyproject.toml has no requires-python")
        declared = (int(match.group(1)), int(match.group(2)))
        self.assertEqual(
            declared,
            MINIMUM,
            f"pyproject.toml promises >={declared[0]}.{declared[1]} but this file checks "
            f"{MINIMUM[0]}.{MINIMUM[1]}; update both, and the CI matrix, together",
        )

    def test_ci_matrix_covers_the_floor(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        match = re.search(r"python-version:\s*\[([^\]]+)\]", workflow)
        self.assertIsNotNone(match, "no python-version matrix in ci.yml")
        versions = re.findall(r'"(\d+)\.(\d+)"', match.group(1))
        self.assertIn(
            (str(MINIMUM[0]), str(MINIMUM[1])),
            versions,
            "CI does not test the oldest interpreter the package claims to support",
        )


if __name__ == "__main__":
    unittest.main()
