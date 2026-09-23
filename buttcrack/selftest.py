"""``buttcrack selftest`` -- verify an installation against known answers.

Three kinds of check, in increasing order of cost:

* **vectors** -- published known-answer tests (``ATTACKATDAWN`` under Caesar 3 is
  ``DWWDFNDWGDZQ``); these catch a broken cipher implementation.
* **round trips** -- every cipher in the registry encrypts and decrypts back to
  the same letters; the handful that cannot are the documented lossy ones
  (Playfair pads with X, Polybius and Bifid merge I/J, Bacon merges U/V).
* **breaks** -- the solver is handed ciphertexts with no hints and must recover
  the plaintext.  This is the check that matters: everything else can pass while
  the search is broken.

``--slow`` adds the searches that need a real budget (substitution, Playfair,
Bifid).  Exit status is 0 when every check passed, 1 otherwise, so this is usable
in CI and in a package post-install smoke test.
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from . import __version__
from .ciphers import ALL_CIPHERS, get, try_get
from .detect import identify
from .engine import solve
from .lang import SOLVED_CONFIDENCE, get_model
from .results import CrackReport
from .text import letters_only

#: Ciphers whose round trip is lossy by design, and why.
LOSSY: dict[str, str] = {
    "playfair": "pads to even length with X and splits doubled letters",
    "bifid": "merges I and J in the 6x6 grid",
    "polybius": "merges I and J in the 5x5 grid",
    "bacon": "merges U/V and I/J in the 5-bit alphabet",
    "bacon_case": "merges U/V and I/J in the 5-bit alphabet",
}

#: Text used for the break checks: long enough for honest statistics, and full of
#: common English structure so a correct solve is unmistakable.
PROSE = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well."
)
LONG_PROSE = PROSE + (
    " Every secret society in the city maintains at least one archive of forbidden documents, and "
    "the committee has decided to postpone the railway conference until further notice is issued "
    "by the board of directors. Mathematics is the language in which nature has chosen to write "
    "the universe, and every equation is a sentence waiting patiently to be understood."
)

#: Published known-answer vectors: (cipher, key, plaintext, expected ciphertext).
VECTORS: tuple[tuple[str, Any, str, str], ...] = (
    ("caesar", 3, "ATTACKATDAWN", "DWWDFNDWGDZQ"),
    ("rot13", None, "HELLO", "URYYB"),
    ("atbash", None, "ABCXYZ", "ZYXCBA"),
    ("affine", {"a": 5, "b": 8}, "AFFINECIPHER", "IHHWVCSWFRCP"),
    ("vigenere", "LEMON", "ATTACKATDAWN", "LXFOPVEFRNHR"),
    ("trithemius", {"start": 0, "step": 1}, "ATTACKATDAWN", "AUVDGPGALJGY"),
    ("rail_fence", 3, "WEAREDISCOVEREDFLEEATONCE", "WECRLTEERDSOEEFEAOCAIVDEN"),
    ("skip", 3, "ABCDEFGHIJKL", "ADGJBEHKCFIL"),
    ("rot47", 47, "Hello!", "w6==@P"),
    ("morse", None, "SOS", "... --- ..."),
    ("a1z26", None, "ABC", "1 2 3"),
    ("polybius", None, "HI", "23 24"),
    ("bacon", None, "AB", "aaaaa aaaab"),
    ("base64", None, "hello", "aGVsbG8="),
    ("base16", None, "hi", "6869"),
    ("binary", None, "hi", "01101000 01101001"),
    ("xor_single", 0x42, "hi", "2a2b"),
    ("bifid", {"key": "MONARCHY", "period": 7}, "ATTACKATDAWN", "ALYAZLXPRRXG"),
)

#: Identification spot-checks: (cipher, key, expected top hypothesis).
IDENTIFICATION: tuple[tuple[str, Any, str], ...] = (
    ("caesar", 7, "caesar"),
    ("rot13", None, "rot13"),
    ("atbash", None, "substitution"),
    ("vigenere", "SECRET", "vigenere"),
    ("columnar", "SPIES", "columnar"),
    ("rail_fence", 4, "columnar"),
    ("playfair", "MONARCHY", "playfair"),
    ("morse", None, "morse"),
    ("base64", None, "base64"),
    ("base16", None, "base16"),
)


@dataclass
class Check:
    """One self-test result."""

    section: str
    name: str
    ok: bool
    detail: str = ""
    elapsed: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "elapsed": round(self.elapsed, 3),
        }


@dataclass
class SelfTestReport:
    """Everything the self-test did, for ``--json`` and for the exit status."""

    checks: list[Check] = field(default_factory=list)
    started: float = field(default_factory=time.time)
    finished: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.ok)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    @property
    def ok(self) -> bool:
        return not self.failed

    @property
    def elapsed(self) -> float:
        return (self.finished or time.time()) - self.started

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": __version__,
            "ok": self.ok,
            "passed": self.passed,
            "failed": len(self.failed),
            "total": len(self.checks),
            "elapsed": round(self.elapsed, 3),
            "checks": [c.as_dict() for c in self.checks],
        }


class _Palette:
    """ANSI colours, switched off when the output is not a terminal."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def red(self, text: str) -> str:
        return self._wrap("31", text)

    def yellow(self, text: str) -> str:
        return self._wrap("33", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)

    def dim(self, text: str) -> str:
        return self._wrap("2", text)

    def bold(self, text: str) -> str:
        return self._wrap("1", text)


def _colour_requested(explicit: bool | None) -> bool:
    if explicit is False or os.environ.get("NO_COLOR"):
        return False
    if explicit is True:
        return True
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


# --------------------------------------------------------------------------- #
# check sections
# --------------------------------------------------------------------------- #
def check_installation(report: SelfTestReport, verbose: bool) -> None:
    """The language model and the registry have to be there at all."""
    started = time.time()
    try:
        model = get_model()
        quadgrams = model.ngram_count(4)
        words = len(model.words)
        ok = quadgrams > 100_000 and words > 10_000
        detail = f"{quadgrams:,} quadgrams, {words:,} dictionary words"
        if not ok:
            detail += " -- expected a full model; run scripts/build_language_model.py"
    except Exception as error:  # pragma: no cover - a broken install
        ok, detail = False, f"{type(error).__name__}: {error}"
    report.checks.append(
        Check("installation", "language model", ok, detail, time.time() - started)
    )

    started = time.time()
    names = {c.info.name for c in ALL_CIPHERS}
    missing = {"caesar", "vigenere", "columnar", "xor_repeating", "base64"} - names
    report.checks.append(
        Check(
            "installation",
            "cipher registry",
            not missing,
            f"{len(ALL_CIPHERS)} ciphers" + (f", missing {sorted(missing)}" if missing else ""),
            time.time() - started,
        )
    )

    started = time.time()
    keyless = [c.info.name for c in ALL_CIPHERS if c.info.keyed and c.info.example_key is None]
    report.checks.append(
        Check(
            "installation",
            "every keyed cipher ships an example key",
            not keyless,
            "all keyed ciphers have one" if not keyless else f"missing: {keyless}",
            time.time() - started,
        )
    )


def check_vectors(report: SelfTestReport, verbose: bool) -> None:
    """Published known-answer tests, cipher by cipher."""
    for name, key, plaintext, expected in VECTORS:
        started = time.time()
        cipher = try_get(name)
        if cipher is None:
            report.checks.append(Check("vectors", name, False, "cipher not in registry"))
            continue
        try:
            produced = cipher.encrypt(plaintext, key)
            ok = produced.strip() == expected.strip()
            detail = "" if ok else f"expected {expected!r}, got {produced!r}"
            if ok and verbose:
                detail = f"{plaintext!r} -> {produced!r}"
        except Exception as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        report.checks.append(
            Check("vectors", f"{name}({key!r})" if key is not None else name, ok, detail,
                  time.time() - started)
        )


def check_round_trips(report: SelfTestReport, verbose: bool) -> None:
    """Every cipher must give its letters back; the lossy ones must say so."""
    for cipher in ALL_CIPHERS:
        name = cipher.info.name
        started = time.time()
        key = cipher.info.example_key
        try:
            produced = cipher.encrypt(PROSE, key)
            back = cipher.decrypt(produced, key)
            if name in LOSSY:
                # Documented loss: the letters must still line up once the
                # cipher's own normalisation is applied.
                expected = letters_only(cipher.prepare(PROSE))
                got = letters_only(back)
                ok = got == expected or _lossy_match(name, expected, got)
                detail = f"lossy by design: {LOSSY[name]}"
            else:
                ok = letters_only(back) == letters_only(cipher.prepare(PROSE))
                detail = "" if ok else f"got {letters_only(back)[:48]!r}"
        except Exception as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        if not ok and verbose:
            detail = detail or "round trip failed"
        report.checks.append(Check("round trip", name, ok, detail, time.time() - started))


def _lossy_match(name: str, expected: str, got: str) -> bool:
    """Compare round trips for the ciphers that cannot be exact."""
    if not got:
        return False
    folded_expected = expected.replace("J", "I").replace("V", "U")
    folded_got = got.replace("J", "I").replace("V", "U")
    if name == "playfair":
        # X padding and split doubles: compare with X removed from both sides.
        return folded_got.replace("X", "") == folded_expected.replace("X", "")
    return folded_got == folded_expected


def check_detection(report: SelfTestReport, verbose: bool) -> None:
    """The identifier has to point at the right family before anything is attacked."""
    model = get_model()
    for name, key, expected in IDENTIFICATION:
        started = time.time()
        cipher = try_get(name)
        if cipher is None:
            report.checks.append(Check("detection", name, False, "cipher not in registry"))
            continue
        text = cipher.encrypt(LONG_PROSE, key)
        try:
            hypotheses, _stats = identify(text, model)
            top = hypotheses[0].cipher if hypotheses else "none"
            ok = top == expected
            detail = (
                f"top hypothesis {top} ({hypotheses[0].likelihood:.2f})"
                if hypotheses
                else "no hypotheses"
            )
            if not ok:
                detail += f", expected {expected}"
        except Exception as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        report.checks.append(Check("detection", f"{name} -> {expected}", ok, detail,
                                   time.time() - started))


#: Break checks: (label, cipher, key, plaintext, budget, expected chain or None).
QUICK_BREAKS: tuple[tuple[str, str, Any, str, float, str | None], ...] = (
    ("caesar over prose", "caesar", 7, PROSE, 10.0, "caesar"),
    ("ROT13", "rot13", None, PROSE, 10.0, "rot13"),
    ("atbash", "atbash", None, PROSE, 10.0, None),
    ("affine", "affine", {"a": 5, "b": 8}, PROSE, 10.0, None),
    ("Vigenere", "vigenere", "SECRET", PROSE, 15.0, "vigenere"),
    ("Beaufort", "beaufort", "LANTERN", PROSE, 15.0, None),
    ("variant Beaufort", "variant_beaufort", "KEYS", PROSE, 15.0, None),
    ("Gronsfeld", "gronsfeld", "31415", PROSE, 15.0, None),
    ("Trithemius", "trithemius", {"start": 2, "step": 3}, PROSE, 15.0, None),
    ("autokey", "autokey", "PRIMER", PROSE, 20.0, None),
    ("columnar transposition", "columnar", "SPIES", PROSE, 20.0, None),
    ("rail fence", "rail_fence", 4, PROSE, 15.0, None),
    ("route transposition", "route", {"width": 7, "pattern": "spiral"}, PROSE, 20.0, None),
    ("skip / scytale", "skip", 3, PROSE, 15.0, None),
    ("Morse code", "morse", None, PROSE, 15.0, "morse"),
    ("A1Z26", "a1z26", None, PROSE, 15.0, "a1z26"),
    ("Polybius square", "polybius", None, PROSE, 15.0, None),
    ("Bacon cipher", "bacon", None, PROSE, 15.0, "bacon"),
    ("base64", "base64", None, PROSE, 10.0, "base64"),
    ("base32", "base32", None, PROSE, 10.0, "base32"),
    ("hex", "base16", None, PROSE, 10.0, "base16"),
    ("base58", "base58", None, PROSE, 10.0, "base58"),
    ("base85", "base85", None, PROSE, 10.0, "base85"),
    ("URL encoding", "url", None, PROSE, 10.0, "url"),
    ("binary", "binary", None, PROSE, 15.0, "binary"),
    ("single-byte XOR", "xor_single", 0x42, PROSE, 15.0, "base16 -> xor_single"),
    ("repeating-key XOR", "xor_repeating", "KEY", PROSE, 20.0, "base16 -> xor_repeating"),
    ("binary XOR", "xor_repeating", b"\xff\x10", PROSE, 20.0, "base16 -> xor_repeating"),
)

#: Stacks: encodings wrapped around a cipher, the case that needs the peeler.
#: The spec reads outside-in, so ``base64+base16+xor_repeating`` is a repeating-key
#: XOR payload, written as hex, then base64'd -- three layers, no hints.
STACK_BREAKS: tuple[tuple[str, str, Any, float], ...] = (
    ("base64 over Caesar", "base64+caesar", 11, 15.0),
    ("hex over Vigenere", "base16+vigenere", "LAMP", 20.0),
    ("base32 over base64", "base32+base64", None, 15.0),
    # XOR already writes its payload as hex, so this is base64 over hex over XOR.
    ("base64 over hex over XOR", "base64+xor_repeating", "LAMP", 25.0),
    ("base64 over Morse", "base64+morse", None, 20.0),
    ("hex over Atbash", "base16+atbash", None, 15.0),
)

#: Expensive searches, only run with ``--slow``.  The last field is what the
#: check demands: ``exact`` means the plaintext must come back letter for letter,
#: ``partial`` means the cipher must be named and the reading must beat noise --
#: with a hinted run proving the exact answer is reachable.  Playfair and Bifid
#: are ``partial`` because no pure-Python search finishes a 25-cell grid or a
#: fractionated 6x6 one from scratch inside a two-minute budget; see
#: :func:`buttcrack.ciphers.polygraphic._playfair_worker` for the measurements.
SLOW_BREAKS: tuple[tuple[str, str, Any, str, float, str | None, str], ...] = (
    ("keyword substitution", "keyword_substitution", "GALAXY", LONG_PROSE, 60.0, None, "exact"),
    ("Playfair", "playfair", "MONARCHY", LONG_PROSE * 3, 120.0, None, "partial"),
    # "hinted": the unhinted search is experimental and may return nothing
    # useful; what must hold is that the cipher is named and that handing over
    # the key produces the exact plaintext.
    ("Bifid", "bifid", {"key": "MONARCHY", "period": 7}, LONG_PROSE * 2, 90.0, None, "hinted"),
)


def _squash(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalnum())


def _fold_lossy(name: str, text: str) -> str:
    out = _squash(text)
    if name in LOSSY:
        out = out.replace("J", "I").replace("V", "U")
        if name == "playfair":
            out = out.replace("X", "")
    return out


def check_breaks(
    report: SelfTestReport,
    verbose: bool,
    quick: bool,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Hand the solver ciphertexts with no hints and demand the plaintext back."""
    cases: list[tuple[str, str, Any, str, float, str | None, str]] = [
        (label, name, key, text, budget, chain, "exact") for label, name, key, text, budget, chain in QUICK_BREAKS
    ]
    for label, spec, key, budget in STACK_BREAKS:
        cases.append((label, spec, key, PROSE, budget, None, "exact"))
    if not quick:
        cases.extend(SLOW_BREAKS)

    for label, name, key, text, budget, chain, expect in cases:
        started = time.time()
        ciphertext = _build(name, text, key)
        if ciphertext is None:
            report.checks.append(Check("break", label, False, "could not build the ciphertext"))
            continue
        if progress:
            progress(label)
        try:
            result = solve(ciphertext, budget=budget, workers=workers)
            if expect == "exact":
                ok = result.solved and _fold_lossy(_inner(name), result.formatted) == _fold_lossy(_inner(name), text)
            else:
                ok, extra = _check_partial(name, key, text, ciphertext, result, workers, expect)
            detail = (
                f"{result.path} key={result.key_repr} confidence={result.confidence:.3f} "
                f"in {result.elapsed:.1f}s"
            )
            if expect != "exact":
                detail += extra
            if chain and result.path != chain:
                ok = ok and False
                detail += f" (expected chain {chain})"
            if not ok and not result.solved:
                detail += f" -- best was {result.path} at {result.confidence:.3f}"
        except Exception as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        report.checks.append(Check("break", label, ok, detail, time.time() - started))


def _similarity(got: str, want: str, name: str) -> float:
    """How much of the message came back, as a 0..1 sequence similarity.

    Position-by-position agreement is the wrong measure for a polygraphic
    cipher: Playfair inserts ``X`` wherever the *recovered* grid splits a doubled
    letter, which is not always where the true grid split it, so every letter
    after the first disagreement is offset -- a reading that is nine letters in
    ten correct measures 22% by position and 90% by similarity.
    """
    import difflib

    left = _fold_lossy(name, got)
    right = _fold_lossy(name, want)
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def _check_partial(
    name: str, key: Any, text: str, ciphertext: str, result: Any, workers: int, expect: str
) -> tuple[bool, str]:
    """Grade a cipher the search is not expected to finish from scratch.

    Two things are always checked: the unhinted run has to name the right cipher,
    and a run handed the true key has to come back letter for letter.  That
    second half is what keeps an honest line between "this solver is weak here"
    and "this cipher is broken".  For ``partial`` the unhinted reading must also
    be recognisably the message rather than noise; for ``hinted`` it is reported
    but not required, because that search is experimental.
    """
    inner = _inner(name)
    named = result.cipher == inner or inner in result.path
    similarity = _similarity(result.plaintext, text, inner)
    hints = dict(key) if isinstance(key, dict) else {"key": key}
    hinted = solve(ciphertext, budget=30.0, workers=workers, hints=hints)
    hinted_ok = hinted.solved and _fold_lossy(inner, hinted.formatted) == _fold_lossy(inner, text)
    progress_ok = expect != "partial" or similarity > 0.5
    ok = bool(named and hinted_ok and progress_ok)
    extra = (
        f" (unhinted: {similarity * 100:.0f}% of the message recovered, "
        f"confidence {result.confidence:.3f}"
        + ("; exact with the key)" if hinted_ok else "; the key did NOT reproduce the plaintext)")
    )
    if not named:
        extra += f" [named {result.path}, expected {inner}]"
    return ok, extra


def _inner(name: str) -> str:
    """The cipher that actually did the encrypting in a ``outer+inner`` label."""
    return name.split("+")[-1]


def _build(name: str, text: str, key: Any) -> str | None:
    """Encrypt ``text``, applying the layers named in ``outer+inner`` labels."""
    if "+" not in name:
        cipher = try_get(name)
        if cipher is None:
            return None
        try:
            return cipher.encrypt(text, key if key is not None else cipher.info.example_key)
        except Exception:
            return None
    parts = name.split("+")
    inner = try_get(parts[-1])
    if inner is None:
        return None
    try:
        # The innermost cipher gets the case key (or its own example key); the
        # rest are encodings applied outside-in.
        payload: str = inner.encrypt(text, key if key is not None else inner.info.example_key)
    except Exception:
        return None
    for part in reversed(parts[:-1]):
        if part == "hex":
            part = "base16"
        layer = try_get(part)
        if layer is None:
            return None
        try:
            payload = layer.encrypt(payload)
        except Exception:
            return None
    return payload


def check_report_shape(report: SelfTestReport, verbose: bool) -> None:
    """The report has to survive JSON, because the CLI and the web UI both emit it."""
    started = time.time()
    try:
        result = solve(get("caesar").encrypt(PROSE, 9), budget=10.0, workers=1)
        payload = result.as_dict(max_candidates=4)
        text = json.dumps(payload, default=str)
        reloaded = json.loads(text)
        ok = bool(reloaded["solved"]) and reloaded["confidence"] > SOLVED_CONFIDENCE
        detail = f"{len(text):,} bytes of JSON"
        if not isinstance(result, CrackReport):  # pragma: no cover - type sanity
            ok, detail = False, "solve() did not return a CrackReport"
    except Exception as error:
        ok, detail = False, f"{type(error).__name__}: {error}"
    report.checks.append(Check("report", "JSON round trip", ok, detail, time.time() - started))


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def run_selftest(
    *,
    verbose: bool = False,
    quick: bool = True,
    json_output: bool = False,
    color: bool | None = None,
    workers: int | None = None,
    stream: io.TextIOBase | None = None,
) -> int:
    """Run every check and report.  Returns a process exit status."""
    out = stream if stream is not None else sys.stdout
    pal = _Palette(False if json_output else _colour_requested(color))
    workers = workers or (os.cpu_count() or 1)
    report = SelfTestReport()

    def note(message: str) -> None:
        if not json_output:
            print(f"  {pal.dim('...')} {message}", file=out, flush=True)

    sections: list[tuple[str, Callable[[], None]]] = [
        ("installation", lambda: check_installation(report, verbose)),
        ("vectors", lambda: check_vectors(report, verbose)),
        ("round trips", lambda: check_round_trips(report, verbose)),
        ("detection", lambda: check_detection(report, verbose)),
        ("report", lambda: check_report_shape(report, verbose)),
    ]
    if not json_output:
        print(pal.bold(f"buttcrack {__version__} self-test"), file=out)
        print(
            pal.dim(
                f"python {sys.version.split()[0]}, {workers} worker(s), "
                f"{'quick' if quick else 'slow'} mode"
            ),
            file=out,
        )
        print(file=out)
    for title, section in sections:
        section()
        if not json_output:
            _render_section(report, title, pal, out, verbose)

    started = time.time()
    check_breaks(
        report,
        verbose,
        quick,
        workers,
        progress=None if json_output else note,
    )
    _render_section(report, "break", pal, out, verbose, elapsed=time.time() - started)

    report.finished = time.time()
    if json_output:
        print(json.dumps(report.as_dict(), indent=2 if verbose else None, default=str), file=out)
    else:
        print(file=out)
        total = len(report.checks)
        failed = report.failed
        summary = f"{report.passed}/{total} checks passed in {report.elapsed:.1f}s"
        print(
            "  " + (pal.green(summary) if not failed else pal.red(summary)),
            file=out,
        )
        if failed:
            print(file=out)
            print(pal.red("  failures:"), file=out)
            for check in failed:
                print(f"    {check.section:<11} {check.name}: {check.detail}", file=out)
        print(file=out)
    return 0 if report.ok else 1


def _render_section(
    report: SelfTestReport,
    section: str,
    pal: _Palette,
    out: Any,
    verbose: bool,
    elapsed: float | None = None,
) -> None:
    checks = [c for c in report.checks if c.section == section]
    if not checks:
        return
    failures = [c for c in checks if not c.ok]
    timing = f" ({elapsed:.1f}s)" if elapsed else ""
    head = f"{section}{timing}"
    if not failures:
        print(f"  {pal.green('pass')}  {head} {pal.dim(f'-- {len(checks)} checks')}", file=out)
        if verbose:
            for check in checks:
                print(f"        {pal.dim('-')} {check.name} {pal.dim(check.detail)}", file=out)
        return
    print(
        f"  {pal.red('FAIL')}  {head} -- {len(failures)} of {len(checks)} failed",
        file=out,
    )
    for check in failures:
        print(f"        {pal.red('x')} {check.name}: {check.detail}", file=out)
    if verbose:
        for check in checks:
            if check.ok:
                print(f"        {pal.dim('-')} {check.name} {pal.dim(check.detail)}", file=out)


def main(argv: Iterable[str] | None = None) -> int:  # pragma: no cover - CLI shim
    args = list(argv or sys.argv[1:])
    return run_selftest(
        verbose="-v" in args or "--verbose" in args,
        quick="--slow" not in args,
        json_output="--json" in args,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
