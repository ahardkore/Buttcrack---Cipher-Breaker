"""Dependency-free manuscript and evidence audit."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
text = (ROOT / "KRYPTOS_SCHOLARLY_MANUSCRIPT.md").read_text(encoding="utf-8")
words = len(re.findall(r"\b[\w’'-]+\b", text))
errors = []
if words < 75_000:
    errors.append(f"manuscript has {words} words; minimum is 75000")
for phrase in ("PK9", "PK10"):
    if phrase not in text:
        errors.append(f"missing open-work marker: {phrase}")
if "PROVISIONAL" not in text:
    errors.append("K4 provisional status marker missing")
pdf = ROOT / "KRYPTOS_SCHOLARLY_MANUSCRIPT.pdf"
if not pdf.exists() or pdf.read_bytes()[:5] != b"%PDF-":
    errors.append("generated PDF missing or invalid header")
print(f"words={words}")
print(f"pdf_bytes={pdf.stat().st_size if pdf.exists() else 0}")
if errors:
    for error in errors: print("FAIL:", error)
    raise SystemExit(1)
print("PASS: manuscript evidence and production audit")
