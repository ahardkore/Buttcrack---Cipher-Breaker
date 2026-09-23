"""The command line is the interface most people will use, so it is tested.

These are end-to-end: real argument vectors in, exit code and printed text out.
The budgets are small and the model is loaded once per process, so the whole
file costs a few seconds.
"""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from buttcrack import cli
from buttcrack.ciphers import ALL_CIPHERS

CAESAR = "Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj, dqg wkh frpplwwhh gholehudwhg."
PLAIN = "The quick brown fox jumps over the lazy dog, and the committee deliberated."


class FakeStdin(io.StringIO):
    """``sys.stdin`` stand-in: the CLI asks whether it is a terminal."""

    def __init__(self, text: str, tty: bool = False) -> None:
        super().__init__(text)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def run(*argv: str) -> tuple[int, str, str]:
    """Run the CLI in-process and capture what it printed."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def squash(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalnum())


class TestCrack(unittest.TestCase):
    def test_positional_ciphertext_is_cracked(self):
        code, out, _ = run(CAESAR, "--budget", "8")
        self.assertEqual(code, 0)
        self.assertIn("caesar", out.lower())
        self.assertIn("SOLVED", out)
        self.assertIn("quick brown fox jumps over the lazy dog", out)

    def test_json_report_is_machine_readable(self):
        code, out, _ = run(CAESAR, "--budget", "8", "--json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertTrue(report["solved"])
        self.assertIn(report["best"]["cipher"], ("caesar", "rot13"))
        self.assertEqual(report["best"]["key"], "3")
        self.assertEqual(squash(report["best"]["plaintext"]), squash(PLAIN))
        self.assertIn("hypotheses", report)
        self.assertIn("stats", report)

    def test_stdin_is_read_when_no_text_is_given(self):
        with mock.patch("sys.stdin", FakeStdin(CAESAR, tty=False)):
            code, out, _ = run("--budget", "8", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["solved"])

    def test_dash_reads_stdin(self):
        with mock.patch("sys.stdin", FakeStdin(CAESAR, tty=False)):
            code, out, _ = run("-", "--budget", "8", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["solved"])

    def test_dash_on_a_terminal_says_so_instead_of_hanging(self):
        # Reading from an interactive terminal would block forever, so the CLI
        # refuses and says what to do instead.
        with mock.patch("sys.stdin", FakeStdin("", tty=True)):
            with self.assertRaises(SystemExit) as caught:
                run("-", "--budget", "2")
        self.assertIn("nothing to read", str(caught.exception.code))

    def test_a_hint_that_does_not_fit_is_survived(self):
        code, out, err = run(CAESAR, "--budget", "6", "--hint", "key=nonsense", "--json")
        self.assertEqual(code, 0, err)
        json.loads(out)

    def test_hint_syntax_is_checked(self):
        with self.assertRaises(SystemExit) as caught:
            run(CAESAR, "--budget", "2", "--hint", "nonsense")
        self.assertIn("name=value", str(caught.exception.code))

    def test_a_real_hint_shortcuts_the_search(self):
        code, out, _ = run(CAESAR, "--budget", "10", "--key", "3", "--json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertTrue(report["solved"])
        self.assertEqual(squash(report["best"]["plaintext"]), squash(PLAIN))


class TestTransform(unittest.TestCase):
    def test_encrypt_with_text_after_the_key(self):
        # argparse cannot interleave a nargs="*" positional with optionals, and
        # this is the order the help text advertises -- it used to be rejected.
        code, out, _ = run("encrypt", "vigenere", "--key", "LEMON", "Meet me at noon.")
        self.assertEqual(code, 0)
        self.assertIn("Xiqh zp ef bbzr.", out)

    def test_encrypt_with_text_before_the_key(self):
        code, out, _ = run("encrypt", "vigenere", "Meet me at noon.", "--key", "LEMON")
        self.assertEqual(code, 0)
        self.assertIn("Xiqh zp ef bbzr.", out)

    def test_round_trip_keeps_the_layout(self):
        _, encrypted, _ = run("encrypt", "caesar", "--key", "7", "Meet me at noon.")
        code, out, _ = run("decrypt", "caesar", "--key", "7", encrypted.strip().splitlines()[-1])
        self.assertEqual(code, 0)
        self.assertIn("Meet me at noon.", out)

    def test_unknown_cipher_is_reported(self):
        with self.assertRaises(SystemExit) as caught:
            run("encrypt", "not-a-cipher", "--key", "X", "hello")
        self.assertIn("unknown cipher", str(caught.exception.code))


class TestRegistryCommands(unittest.TestCase):
    def test_ciphers_lists_everything(self):
        code, out, _ = run("ciphers")
        self.assertEqual(code, 0)
        self.assertIn(f"{len(ALL_CIPHERS)} ciphers", out)
        for name in ("caesar", "vigenere", "playfair", "xor_repeating", "base64"):
            self.assertIn(name, out)

    def test_ciphers_json(self):
        code, out, _ = run("ciphers", "--json")
        self.assertEqual(code, 0)
        listing = json.loads(out)
        entries = listing if isinstance(listing, list) else listing.get("ciphers", [])
        self.assertEqual(len(entries), len(ALL_CIPHERS))

    def test_show_explains_one_cipher(self):
        code, out, _ = run("show", "playfair")
        self.assertEqual(code, 0)
        self.assertIn("Playfair", out)
        self.assertIn("MONARCHY", out)

    def test_identify_names_the_family(self):
        code, out, _ = run("identify", CAESAR)
        self.assertEqual(code, 0)
        self.assertIn("caesar", out.lower())

    def test_identify_json(self):
        code, out, _ = run("identify", CAESAR, "--json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertTrue(any(h["cipher"] == "caesar" for h in report["hypotheses"]))
        self.assertIn("index_of_coincidence", report["stats"])


class TestSelfTestFlags(unittest.TestCase):
    """Parsed, not run: the quick self-test alone takes twenty seconds."""

    def test_quick_and_slow_are_both_spellable(self):
        # CI runs `selftest --quick`; the flag did not exist and argparse exited 2.
        parser = cli.build_parser()
        self.assertTrue(parser.parse_args(["selftest", "--quick"]).quick)
        self.assertTrue(parser.parse_args(["selftest", "--slow"]).slow)
        self.assertFalse(parser.parse_args(["selftest"]).slow)

    def test_quick_and_slow_are_mutually_exclusive(self):
        parser = cli.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["selftest", "--quick", "--slow"])


class TestTopLevel(unittest.TestCase):
    def test_no_arguments_prints_help(self):
        code, out, _ = run()
        self.assertEqual(code, 0)
        self.assertIn("usage:", out)
        self.assertIn("crack", out)

    def test_version(self):
        code, out, _ = run("--version")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"\d+\.\d+\.\d+")

    def test_unrecognised_option_is_an_error(self):
        with self.assertRaises(SystemExit) as caught:
            run("ciphers", "--nope")
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
