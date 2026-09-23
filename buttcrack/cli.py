"""Command line interface.

``python3 -m buttcrack`` (or the ``buttcrack`` script once installed) with a
ciphertext is the whole point of the tool::

    buttcrack "Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj"
    buttcrack --file puzzle.txt --budget 60 --json
    cat puzzle.txt | buttcrack -v
    buttcrack encrypt vigenere --key LEMON "meet me at noon"
    buttcrack identify --file puzzle.txt
    buttcrack ciphers
    buttcrack serve

The output is written for a terminal: colour when stdout is a tty (and never when
``NO_COLOR`` is set), plain text when it is redirected, ``--json`` for machines.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
import time
from typing import Any, Callable, Iterable, Sequence

from . import __version__
from .ciphers import ALL_CIPHERS, by_family, get, layer_ciphers, try_get
from .ciphers.base import Cipher
from .detect import characterise, identify
from .engine import Solver, solve
from .results import CrackReport
from .text import letters_only

PROGRAM = "buttcrack"

# --------------------------------------------------------------------------- #
# terminal presentation
# --------------------------------------------------------------------------- #


class Palette:
    """ANSI colour, disabled automatically when it would only make noise."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled and text else text

    def bold(self, text: str) -> str:
        return self._wrap("1", text)

    def dim(self, text: str) -> str:
        return self._wrap("2", text)

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def yellow(self, text: str) -> str:
        return self._wrap("33", text)

    def red(self, text: str) -> str:
        return self._wrap("31", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)

    def magenta(self, text: str) -> str:
        return self._wrap("35", text)


def make_palette(args: argparse.Namespace) -> Palette:
    if getattr(args, "no_color", False) or os.environ.get("NO_COLOR"):
        return Palette(False)
    if getattr(args, "json", False) or getattr(args, "quiet", False):
        return Palette(False)
    return Palette(sys.stdout.isatty())


def terminal_width(default: int = 100) -> int:
    try:
        return max(60, min(shutil.get_terminal_size((default, 24)).columns, 120))
    except Exception:  # pragma: no cover - very exotic environments
        return default


def rule(pal: Palette, title: str = "") -> str:
    width = terminal_width()
    if not title:
        return pal.dim("\u2500" * width)
    label = f" {title} "
    return pal.dim("\u2500" * 2 + label + "\u2500" * max(0, width - len(label) - 2))


def wrap_block(text: str, indent: str = "  ", width: int | None = None) -> str:
    width = width or terminal_width()
    limit = max(20, width - len(indent))
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, limit) or [""])
    return "\n".join(indent + line for line in lines)


def pad(text: str, width: int, colour: Callable[[str], str] | None = None) -> str:
    """Pad first, colour second: ANSI escapes are invisible but not zero-length."""
    padded = text if len(text) >= width else text + " " * (width - len(text))
    return colour(padded) if colour else padded


def truncate(text: str, limit: int) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


# --------------------------------------------------------------------------- #
# input handling
# --------------------------------------------------------------------------- #


def read_input(args: argparse.Namespace) -> str:
    """Ciphertext from the arguments, ``--file`` or stdin (in that order)."""
    explicit: Sequence[str] = getattr(args, "text", ()) or ()
    if explicit and list(explicit) != ["-"]:
        return " ".join(explicit).strip()
    path = getattr(args, "file", None)
    if path:
        if path == "-":
            return sys.stdin.read().strip()
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    if explicit:  # "-" with an interactive stdin
        raise SystemExit(f"{PROGRAM}: nothing to read from the terminal; pipe text in or pass --file")
    return ""


def parse_key(cipher: Cipher, raw: str | None) -> Any:
    """Turn ``--key`` into the type the cipher actually wants.

    The example key in a cipher's metadata doubles as its type signature: an
    ``int`` example means a numeric key (``0x42`` is understood), a ``dict``
    example means ``a=5,b=8`` or JSON, anything else is a keyword.
    """
    example = cipher.info.example_key
    if raw is None:
        return example
    if raw.startswith("hex:") or raw.startswith("bytes:"):
        return bytes.fromhex(raw.split(":", 1)[1])
    if isinstance(example, bool):
        return raw.lower() in ("1", "true", "yes")
    if isinstance(example, int):
        try:
            return int(raw, 0)
        except ValueError:
            raise SystemExit(f"{PROGRAM}: {cipher.info.name} wants a number, got {raw!r}")
    if isinstance(example, dict):
        values: dict[str, Any] = dict(example)
        text = raw.strip()
        if text.startswith("{"):
            try:
                values.update(json.loads(text))
            except json.JSONDecodeError as error:
                raise SystemExit(f"{PROGRAM}: bad JSON key: {error}")
        else:
            for part in text.split(","):
                name, _, value = part.partition("=")
                name, value = name.strip(), value.strip()
                if not name:
                    continue
                values[name] = int(value, 0) if _is_number(value) else value
        return values
    if isinstance(example, (tuple, list)):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return tuple(int(p, 0) if _is_number(p) else p for p in parts)
    return raw


def _is_number(value: str) -> bool:
    try:
        int(value, 0)
    except (TypeError, ValueError):
        return False
    return True


# --------------------------------------------------------------------------- #
# crack
# --------------------------------------------------------------------------- #


def hint_value(raw: str) -> Any:
    """Coerce a ``--hint`` value: integers for counts, text for keys.

    ``hex:`` is left alone on purpose -- :mod:`buttcrack.ciphers.xor` treats that
    prefix as raw bytes, which is the only way to hint a key that is not
    printable text.
    """
    text = raw.strip()
    if text.startswith("hex:") or not re.fullmatch(r"-?\d+", text):
        return text
    return int(text)


def build_hints(args: argparse.Namespace) -> dict[str, Any]:
    hints: dict[str, Any] = {}
    for item in getattr(args, "hint", None) or ():
        if "=" not in item:
            raise SystemExit(f"{PROGRAM}: --hint wants name=value, got {item!r}")
        name, _, value = item.partition("=")
        name = name.strip().lower().replace("-", "_")
        if not name:
            raise SystemExit(f"{PROGRAM}: --hint wants name=value, got {item!r}")
        hints[name] = hint_value(value)
    if getattr(args, "key", None):
        hints["key"] = args.key
    if getattr(args, "key_length", None):
        hints["key_length"] = int(args.key_length)
    if getattr(args, "width", None):
        hints["width"] = int(args.width)
    if getattr(args, "seed", None) is not None:
        hints["seed"] = int(args.seed)
    if getattr(args, "crib", None):
        hints["crib"] = args.crib
    return hints


def make_progress(pal: Palette, verbose: bool, started: float) -> Callable[[str, float, dict], None]:
    """Live progress for ``--verbose``; silence otherwise."""

    def progress(message: str, fraction: float, extra: dict) -> None:
        if not verbose:
            return
        stamp = f"{time.time() - started:5.1f}s"
        prefix = pal.dim(f"[{stamp}]")
        print(f"{prefix} {message}", flush=True)

    return progress


def verdict_line(report: CrackReport, pal: Palette) -> str:
    if report.solved and report.confidence >= 0.86:
        badge = pal.green(pal.bold("SOLVED"))
    elif report.solved:
        badge = pal.green(pal.bold("SOLVED"))
    elif report.best is not None and report.confidence >= 0.35:
        badge = pal.yellow(pal.bold("BEST GUESS"))
    else:
        badge = pal.red(pal.bold("NOT BROKEN"))
    return f"{badge}  confidence {report.confidence:.2f}  in {report.elapsed:.2f}s"


def render_report(report: CrackReport, args: argparse.Namespace, pal: Palette) -> None:
    width = terminal_width()
    stats = report.stats or {}

    print(rule(pal))
    summary = (
        f"input     {stats.get('length', 0)} characters"
        f" \u00b7 IC {stats.get('index_of_coincidence', 0.0):.4f}"
        f" \u00b7 entropy {stats.get('entropy', 0.0):.2f}"
        f" \u00b7 {stats.get('charset', '?')}"
    )
    print(pal.dim(summary))
    if report.hypotheses and not args.quiet:
        top = report.hypotheses[0]
        others = ", ".join(h.cipher for h in report.hypotheses[1:3])
        print(pal.dim(f"identified {pal.cyan(top.cipher)} ({top.likelihood:.0%})"
                      + (f" \u00b7 also considered: {others}" if others else "")))
        if args.verbose:
            for hypothesis in report.hypotheses:
                print(pal.dim(f"           {hypothesis.cipher:<22} {hypothesis.likelihood:>5.0%}  {hypothesis.reason}"))
    print(rule(pal))
    print()
    print(verdict_line(report, pal))

    if report.best is None:
        print()
        print(wrap_block("No candidate could be produced from this input.", "  "))
        return

    shown = report.formatted if report.formatted.strip() else report.plaintext
    print()
    print(pal.bold("  plaintext"))
    limit = max(200, int(args.limit)) if getattr(args, "limit", 0) else None
    body = shown if limit is None else truncate(shown, limit)
    print(wrap_block(body, "    "))
    if report.notes.get("respaced") and report.notes["respaced"] != shown:
        print()
        print(pal.dim("  word breaks recovered"))
        print(wrap_block(truncate(str(report.notes["respaced"]), limit or 400), "    "))

    print()
    print(pal.bold("  explanation"))
    rows = [
        ("cipher", report.cipher if report.cipher != "none" else "none \u2014 the text was not encrypted"),
        ("key", report.key_repr),
    ]
    if len(report.steps) > 0:
        rows.append(("decode chain", report.path))
    method = report.notes.get("method")
    if method:
        rows.append(("method", str(method)))
    keyword = report.notes.get("keyword")
    if keyword and keyword != report.key_repr:
        rows.append(("keyword", str(keyword)))
    rows.append(("evidence", f"fitness {report.best.fitness:.2f} log10/char"
                             + (f", words {report.best.score.words:.0%}" if report.best.score else "")))
    for note_key in ("key_length", "period_quality", "column_ic", "restarts", "evaluations", "iterations"):
        if note_key in report.notes:
            rows.append((note_key.replace("_", " "), str(report.notes[note_key])))
    if report.notes.get("evidence"):
        rows.append(("caveat", str(report.notes["evidence"])))
    if report.notes.get("key_note"):
        rows.append(("note", str(report.notes["key_note"])))
    label = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"    {pal.dim(name.ljust(label))}  {value}")

    alternatives = [
        c
        for c in report.candidates[1:]
        if c.plaintext != report.plaintext and c.confidence >= 0.05
    ]
    if alternatives and args.candidates > 0:
        print()
        print(pal.bold(f"  alternatives ({len(alternatives[:args.candidates])} of {len(alternatives)})"))
        for index, candidate in enumerate(alternatives[: args.candidates], start=2):
            chain = candidate.path if candidate.steps else candidate.cipher
            print(
                f"    {pal.dim(f'{index:>2}.')} {candidate.confidence:.2f} "
                f"{pal.cyan(chain):<{28}} key={truncate(candidate.key_repr, 24):<24} "
                f"{pal.dim(truncate(candidate.plaintext, max(24, width - 78)))}"
            )

    if args.verbose and report.attacks:
        print()
        print(pal.bold("  attack log"))
        for attack in report.attacks:
            colour = {"solved": pal.green, "improved": pal.yellow, "budget": pal.red}.get(
                attack.status, pal.dim
            )
            print(
                f"    {attack.cipher:<22} {pad(attack.status, 10, colour)} {attack.elapsed:6.2f}s "
                f"tried={attack.tried:<6} best={attack.best_confidence:.3f} {pal.dim(attack.detail)}"
            )

    if not report.solved:
        print()
        print(wrap_block(hint_text(report), "  ", width))
    print()


def hint_text(report: CrackReport) -> str:
    """What to try next, given what the engine actually saw."""
    stats = report.stats or {}
    letters = stats.get("letters", 0)
    tips = []
    if letters and letters < 60:
        tips.append(
            f"only {letters} letters is thin evidence: a longer ciphertext, or --key if you know it, "
            "changes the answer more than a bigger --budget does"
        )
    if stats.get("entropy", 0) > 7.4 or stats.get("high_bytes"):
        tips.append("the input looks like raw bytes: modern cryptography (AES, RSA) is not brute-forceable here")
    tips.append("try --budget 120 for hard classical ciphers, --hint-key-length N if you know the period, "
                "or --verbose to watch the search")
    return "next: " + "; ".join(tips)


def cmd_crack(args: argparse.Namespace) -> int:
    pal = make_palette(args)
    ciphertext = read_input(args)
    if not ciphertext.strip():
        print(f"{PROGRAM}: no ciphertext given (try --help)", file=sys.stderr)
        return 2

    started = time.time()
    progress = make_progress(pal, args.verbose, started)
    if args.verbose and not args.json:
        print(rule(pal, f"{PROGRAM} {__version__}"), flush=True)
    report = solve(
        ciphertext,
        budget=args.budget,
        workers=args.workers,
        max_depth=args.depth,
        hints=build_hints(args),
        progress=progress if not args.json else None,
        exhaustive=args.exhaustive,
    )

    if args.json:
        payload = report.as_dict(plaintext_limit=args.limit if args.limit else None,
                                 max_candidates=max(args.candidates, 1))
        payload["input"] = {"length": len(ciphertext), "preview": truncate(ciphertext, 200)}
        json.dump(payload, sys.stdout, indent=2 if args.pretty else None, ensure_ascii=False)
        sys.stdout.write("\n")
    elif args.quiet:
        print(report.formatted if report.formatted.strip() else report.plaintext)
    else:
        render_report(report, args, pal)

    if args.set_exit_code:
        return 0 if report.solved else 1
    return 0


# --------------------------------------------------------------------------- #
# identify
# --------------------------------------------------------------------------- #


def cmd_identify(args: argparse.Namespace) -> int:
    pal = make_palette(args)
    text = read_input(args)
    if not text.strip():
        print(f"{PROGRAM}: no text given (try --help)", file=sys.stderr)
        return 2
    hypotheses, stats = identify(text)

    if args.json:
        json.dump(
            {"stats": stats.as_dict(), "hypotheses": [h.as_dict() for h in hypotheses]},
            sys.stdout,
            indent=2 if args.pretty else None,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 0

    print(rule(pal, "characterisation"))
    rows = [
        ("length", f"{stats.length} characters ({stats.letters} letters, {stats.digits} digits, {stats.spaces} spaces)"),
        ("charset", stats.charset),
        ("index of coincidence", f"{stats.ic:.4f}  (English ~0.066, random ~0.038)"),
        ("chi-squared / char", f"{stats.chi2_per_char:.3f}  (English < 0.6)"),
        ("quadgram fitness", f"{stats.fitness:.2f} log10/char  (English > -4.3)"),
        ("entropy", f"{stats.entropy:.2f} bits/byte"),
        ("reads as English", f"{stats.confidence:.0%}"),
    ]
    if stats.extra.get("best_period", 1) > 1:
        rows.append(("best period", f"{stats.extra['best_period']} (coset IC {stats.extra.get('best_period_ic', 0):.4f})"))
    label = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"  {pal.dim(name.ljust(label))}  {value}")
    print()
    print(rule(pal, "hypotheses"))
    if not hypotheses:
        print("  nothing matches: this may not be an English-language cipher text")
    for hypothesis in hypotheses:
        bar = "\u2588" * int(round(hypothesis.likelihood * 20))
        colour = pal.green if hypothesis.likelihood >= 0.75 else (pal.yellow if hypothesis.likelihood >= 0.4 else pal.dim)
        print(f"  {colour(f'{hypothesis.likelihood:>5.0%}')} {pad(hypothesis.cipher, 24, pal.cyan)} {pal.dim(bar)}")
        print(f"         {pal.dim(textwrap.shorten(hypothesis.reason, max(40, terminal_width() - 12)))}")
    print()
    return 0


# --------------------------------------------------------------------------- #
# encrypt / decrypt
# --------------------------------------------------------------------------- #


def cmd_transform(args: argparse.Namespace) -> int:
    pal = make_palette(args)
    cipher = resolve_cipher(args.cipher)
    text = read_input(args)
    if not text.strip():
        print(f"{PROGRAM}: no text given (try --help)", file=sys.stderr)
        return 2
    key = parse_key(cipher, args.key)
    try:
        if args.command == "encrypt":
            out = cipher.encrypt(text, key)
        else:
            out = cipher.decrypt(text, key)
    except Exception as error:  # a bad key is a user error, not a traceback
        print(f"{PROGRAM}: {cipher.info.name} could not {args.command}: {error}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(
            {
                "cipher": cipher.info.name,
                "key": cipher.info.example_key if key is None else _jsonable(key),
                "operation": args.command,
                "input": text,
                "output": out,
            },
            sys.stdout,
            indent=2 if args.pretty else None,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
    else:
        print(out)
        if not args.quiet:
            print(
                pal.dim(
                    f"# {cipher.info.title} \u00b7 key={key if key is not None else 'none'} \u00b7 "
                    f"{len(out)} characters out"
                ),
                file=sys.stderr,
            )
    return 0


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def resolve_cipher(name: str) -> Cipher:
    cipher = try_get(name)
    if cipher is None:
        names = ", ".join(sorted(c.info.name for c in ALL_CIPHERS))
        raise SystemExit(f"{PROGRAM}: unknown cipher {name!r}. Available: {names}")
    return cipher


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #


def cmd_ciphers(args: argparse.Namespace) -> int:
    pal = make_palette(args)
    families = by_family()
    if args.json:
        json.dump(
            [c.info.as_dict() for c in ALL_CIPHERS],
            sys.stdout,
            indent=2 if args.pretty else None,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 0

    print(rule(pal, f"{len(ALL_CIPHERS)} ciphers, codes and encodings"))
    for family in sorted(families):
        members = families[family]
        print()
        print(f"  {pal.bold(pal.magenta(family))}")
        for cipher in sorted(members, key=lambda c: (c.info.cost, c.info.name)):
            info = cipher.info
            keyspace = "\u221e" if info.keyspace is None else f"{info.keyspace:,}"
            kind = "layer" if info.layer else ("keyless" if not info.keyed else "keyed")
            print(
                f"    {pad(info.name, 24, pal.cyan)} {pad(info.title, 28)} {pad(kind, 8, pal.dim)} "
                f"keys {keyspace:>10}  cost {info.cost:>4.0f}"
            )
            if args.verbose:
                print(f"      {pal.dim(textwrap.shorten(info.description, terminal_width() - 8))}")
                if info.aliases:
                    print(f"      {pal.dim('aliases: ' + ', '.join(info.aliases))}")
    print()
    print(pal.dim(f"  peelable layers: {', '.join(c.info.name for c in layer_ciphers())}"))
    print(pal.dim("  `buttcrack show <name>` for details on one cipher"))
    print()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    pal = make_palette(args)
    cipher = resolve_cipher(args.cipher)
    info = cipher.info
    if args.json:
        json.dump(info.as_dict(), sys.stdout, indent=2 if args.pretty else None, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    print(rule(pal, info.title))
    rows = [
        ("name", info.name),
        ("family", info.family.value),
        ("aliases", ", ".join(info.aliases) or "\u2014"),
        ("key", f"{info.key_type}" + ("" if info.keyed else " (keyless)")),
        ("keyspace", "\u221e (not enumerable)" if info.keyspace is None else f"{info.keyspace:,}"),
        ("example key", repr(info.example_key)),
        ("min. text", f"{info.min_length} characters"),
        ("search cost", f"{info.cost:.0f}"),
        ("exhaustive", "yes \u2014 the whole keyspace is covered" if info.deterministic else "no \u2014 heuristic search"),
        ("peelable layer", "yes" if info.layer else "no"),
        ("alphabet", info.alphabet if len(info.alphabet) <= 26 else f"{len(info.alphabet)} symbols"),
    ]
    label = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"  {pal.dim(name.ljust(label))}  {value}")
    print()
    print(wrap_block(info.description, "  "))
    print()
    example = "Attack at dawn, and hold the bridge until the relief column arrives."
    try:
        ciphertext = cipher.encrypt(example, info.example_key)
        print(pal.dim("  example"))
        print(wrap_block(f"plain   {example}", "    "))
        print(wrap_block(f"cipher  {truncate(ciphertext, terminal_width() - 12)}", "    "))
        print(wrap_block(f"key     {info.example_key}", "    "))
    except Exception as error:
        print(pal.dim(f"  (no example: {error})"))
    print()
    return 0


# --------------------------------------------------------------------------- #
# demo / selftest / serve
# --------------------------------------------------------------------------- #

DEMO_CASES: tuple[tuple[str, str, Any], ...] = (
    ("caesar", "Meet the courier beside the fountain at noon and bring the second envelope with you.", 7),
    ("vigenere", "The council of Venice has decreed that all merchant vessels must pay the new harbour tax.", "SECRET"),
    ("columnar", "Deliver the sealed package to the contact waiting beneath the clock tower at midnight.", "SPIES"),
    ("keyword_substitution", "Mathematics is the language in which nature has chosen to write the universe, "
                             "and every equation is a sentence waiting to be understood.", "GALAXY"),
    ("morse", "The railway station at Ashford was rebuilt after the war and now houses a small museum.", None),
)


def cmd_demo(args: argparse.Namespace) -> int:
    """Encrypt a few messages, then break them without being told what they are."""
    pal = make_palette(args)
    print(rule(pal, f"{PROGRAM} {__version__} \u2014 demo"))
    print(wrap_block(
        "Each message below is encrypted with a different cipher, wrapped in an encoding where "
        "that is interesting, and then handed to the solver with no hints at all.", "  "))
    print()
    failures = 0
    for name, plaintext, key in DEMO_CASES:
        cipher = get(name)
        ciphertext = cipher.encrypt(plaintext, key)
        if name == "caesar":  # show off a stack on the cheapest case
            ciphertext = get("base64").encode(ciphertext)
            expected_chain = "base64 -> caesar"
        else:
            expected_chain = name
        started = time.time()
        report = solve(ciphertext, budget=args.budget, workers=args.workers)
        elapsed = time.time() - started
        ok = report.solved and letters_only(report.plaintext) == letters_only(plaintext)
        failures += 0 if ok else 1
        mark = pal.green("solved") if ok else pal.red("FAILED")
        print(f"  {pad(cipher.info.title, 22, pal.bold)} {mark} {pal.dim(f'{elapsed:5.2f}s')} "
              f"conf {report.confidence:.2f}  {pal.cyan(report.path)}")
        print(pal.dim(f"    ciphertext  {truncate(ciphertext, terminal_width() - 18)}"))
        print(f"    key         {report.key_repr}   {pal.dim(f'(expected chain: {expected_chain})')}")
        print(f"    plaintext   {truncate(report.formatted, terminal_width() - 18)}")
        print()
    print(rule(pal))
    print(f"  {pal.green('all demos solved') if not failures else pal.red(f'{failures} demo(s) failed')}")
    print()
    return 1 if failures else 0


def cmd_selftest(args: argparse.Namespace) -> int:
    from .selftest import run_selftest

    return run_selftest(
        verbose=args.verbose,
        quick=not args.slow,
        json_output=args.json,
        color=not args.no_color if args.no_color else None,
        workers=args.workers,
    )


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve as serve_web

    return serve_web(host=args.host, port=args.port, open_browser=not args.no_browser)


# --------------------------------------------------------------------------- #
# argument parsing
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Automatic cipher breaker: identifies the cipher, recovers the key, "
                    "reads the plaintext -- including layered puzzles.",
        epilog="examples:\n"
               f"  {PROGRAM} \"Wkh txlfn eurzq ira\"\n"
               f"  {PROGRAM} --file puzzle.txt --budget 60 --verbose\n"
               f"  cat puzzle.txt | {PROGRAM} --json\n"
               f"  {PROGRAM} encrypt vigenere --key LEMON \"meet me at noon\"\n"
               f"  {PROGRAM} --file puzzle.txt --budget 120 --workers 4\n"
               f"  {PROGRAM} --file puzzle.txt --hint key=LEMON\n"
               f"  {PROGRAM} --file puzzle.txt --hint key=hex:ff10 --hint period=7\n"
               f"  {PROGRAM} identify --file puzzle.txt\n"
               f"  {PROGRAM} ciphers --verbose\n"
               f"  {PROGRAM} demo\n"
               f"  {PROGRAM} serve --port 8080\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # -- crack (also the default when no subcommand is given) ---------------- #
    def add_crack_options(target: argparse.ArgumentParser) -> None:
        target.add_argument("text", nargs="*", help="ciphertext (or '-' / omit to read stdin)")
        target.add_argument("--file", "-f", help="read the ciphertext from a file ('-' for stdin)")
        target.add_argument("--budget", "-b", type=float, default=30.0,
                            help="seconds to spend searching (default: 30)")
        target.add_argument("--workers", "-w", type=int, default=os.cpu_count() or 1,
                            help="parallel workers (default: number of CPUs)")
        target.add_argument("--depth", "-d", type=int, default=3,
                            help="how many encoding layers to peel (default: 3)")
        target.add_argument("--key", help="hint: the key, if you already know it")
        target.add_argument("--key-length", type=int, help="hint: period of a repeating key")
        target.add_argument("--width", type=int, help="hint: grid width for a transposition")
        target.add_argument("--seed", type=int, help="hint: fixed search seed (reproducibility)")
        target.add_argument("--crib", help="hint: a phrase you expect in the plaintext")
        target.add_argument("--hint", action="append", metavar="NAME=VALUE",
                            help="hint for the search, repeatable: key=LEMON, key=hex:ff10, "
                                 "period=7, rails=4, width=6, seed=1")
        target.add_argument("--candidates", "-n", type=int, default=5,
                            help="how many alternative readings to show (default: 5)")
        target.add_argument("--limit", type=int, default=0, help="truncate the printed plaintext")
        target.add_argument("--exhaustive", action="store_true",
                            help="enumerate whole keyspaces even where the search would prune")
        target.add_argument("--json", action="store_true", help="machine-readable output")
        target.add_argument("--pretty", action="store_true", help="indent --json output")
        target.add_argument("--quiet", "-q", action="store_true", help="print only the plaintext")
        target.add_argument("--verbose", "-v", action="store_true", help="live progress and attack log")
        target.add_argument("--no-color", action="store_true", help="disable ANSI colour")
        target.add_argument("--set-exit-code", action="store_true",
                            help="exit 1 when the ciphertext was not broken")

    crack = sub.add_parser("crack", help="break a ciphertext (the default command)",
                           formatter_class=argparse.RawDescriptionHelpFormatter)
    add_crack_options(crack)
    crack.set_defaults(func=cmd_crack)

    # -- identify ----------------------------------------------------------- #
    ident = sub.add_parser("identify", help="characterise a ciphertext without breaking it")
    ident.add_argument("text", nargs="*")
    ident.add_argument("--file", "-f")
    ident.add_argument("--json", action="store_true")
    ident.add_argument("--pretty", action="store_true")
    ident.add_argument("--no-color", action="store_true")
    ident.set_defaults(func=cmd_identify)

    # -- encrypt / decrypt -------------------------------------------------- #
    for command in ("encrypt", "decrypt"):
        target = sub.add_parser(command, help=f"{command} text with a chosen cipher")
        target.add_argument("cipher", help="cipher name or alias (`buttcrack ciphers`)")
        target.add_argument("text", nargs="*")
        target.add_argument("--file", "-f")
        target.add_argument("--key", "-k", help="key: a word, a number (0x42 ok), a=5,b=8 or JSON")
        target.add_argument("--json", action="store_true")
        target.add_argument("--pretty", action="store_true")
        target.add_argument("--quiet", "-q", action="store_true")
        target.add_argument("--no-color", action="store_true")
        target.set_defaults(func=cmd_transform, command=command)

    # -- registry ----------------------------------------------------------- #
    listing = sub.add_parser("ciphers", help="list every cipher, code and encoding")
    listing.add_argument("--verbose", "-v", action="store_true", help="include descriptions and aliases")
    listing.add_argument("--json", action="store_true")
    listing.add_argument("--pretty", action="store_true")
    listing.add_argument("--no-color", action="store_true")
    listing.set_defaults(func=cmd_ciphers)

    show = sub.add_parser("show", help="details for one cipher")
    show.add_argument("cipher")
    show.add_argument("--json", action="store_true")
    show.add_argument("--pretty", action="store_true")
    show.add_argument("--no-color", action="store_true")
    show.set_defaults(func=cmd_show)

    # -- extras ------------------------------------------------------------- #
    demo = sub.add_parser("demo", help="encrypt a few messages, then break them with no hints")
    demo.add_argument("--budget", "-b", type=float, default=30.0)
    demo.add_argument("--workers", "-w", type=int, default=os.cpu_count() or 1)
    demo.add_argument("--no-color", action="store_true")
    demo.set_defaults(func=cmd_demo)

    selftest = sub.add_parser("selftest", help="verify the installation against known answers")
    selftest.add_argument("--slow", action="store_true", help="include the expensive searches")
    selftest.add_argument("--verbose", "-v", action="store_true")
    selftest.add_argument("--json", action="store_true")
    selftest.add_argument("--workers", "-w", type=int, default=os.cpu_count() or 1)
    selftest.add_argument("--no-color", action="store_true")
    selftest.set_defaults(func=cmd_selftest)

    serve = sub.add_parser("serve", help="run the web interface")
    serve.add_argument("--host", default="0.0.0.0", help="interface to bind (default: 0.0.0.0)")
    serve.add_argument("--port", "-p", type=int, default=int(os.environ.get("PORT", 8080)))
    serve.add_argument("--no-browser", action="store_true", help="do not try to open a browser")
    serve.add_argument("--no-color", action="store_true")
    serve.set_defaults(func=cmd_serve)

    return parser


SUBCOMMANDS = (
    "crack", "identify", "encrypt", "decrypt", "ciphers", "show", "demo", "selftest", "serve",
)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv or argv[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    if argv[0] in ("-V", "--version"):
        print(f"{PROGRAM} {__version__}")
        return 0
    # `buttcrack "<ciphertext>" --budget 60` is the natural way to call this
    # tool, so anything that is not a known subcommand is a crack.
    if argv[0] not in SUBCOMMANDS:
        argv = ["crack", *argv]
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        # argparse cannot interleave a ``nargs="*"`` positional with optionals, so
        # ``encrypt vigenere --key LEMON "meet me at noon"`` leaves the text
        # unparsed even though that is the order the help advertises.  Take the
        # leftovers as the text when text is the only thing they can be, and keep
        # the ordinary error for anything else.
        if getattr(args, "command", None) in ("encrypt", "decrypt") and all(
            not item.startswith("-") for item in unknown
        ):
            args.text = [*(args.text or []), *unknown]
        else:
            parser.error("unrecognized arguments: " + " ".join(unknown))
    func = getattr(args, "func", None)
    if func is None:  # pragma: no cover - argparse always sets this
        parser.print_help()
        return 0
    try:
        return int(func(args) or 0)
    except KeyboardInterrupt:
        print(f"\n{PROGRAM}: interrupted", file=sys.stderr)
        return 130
    except BrokenPipeError:  # `| head` is a normal thing to do
        try:
            sys.stdout.close()
        finally:
            return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
