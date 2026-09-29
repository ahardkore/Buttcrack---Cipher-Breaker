"""Tests for the M-94 wheel cipher: data, keys, likelihood, and the attack.

The disk set is the standard 25-disk Mauborgne set (disks identified by the
letter that follows their ``A``, running ``B``-``Z``; disk 17 carries the
famous ``ARMY OF THE US`` rim).  The cipher is position-preserving with period
25, and the attack is a hill climb over spindle-slot swaps scored by
n-grams, so these tests pin down:

* the data files load and are what they claim (25 permutation disks);
* every documented key format parses, and malformed ones are rejected;
* encrypt/decrypt round-trip across block boundaries (period 25);
* the likelihood hook separates wheel text from flat/monoalphabetic text;
* the hinted-key path is exact, and the full search (slow suite only)
  recovers a genuinely secret order.
"""

from __future__ import annotations

import os
import unittest

from buttcrack.ciphers import ALL_CIPHERS, get, try_get
from buttcrack.ciphers.base import CrackContext, Family
from buttcrack.ciphers.wheel import DISK_IDS, M94, disks, parse_key
from buttcrack.lang import get_model
from buttcrack.text import letters_only

SLOW = os.environ.get("BUTTCRACK_SLOW") == "1"

PROSE = (
    "The railway station at Ashford was crowded with travellers waiting for the delayed "
    "express and the station master walked up and down the platform with his hands behind "
    "his back muttering about the weather and the coal shortage while a young woman in a "
    "grey coat stood near the book stall reading a letter that she had just received."
)

ORDER = "YRNCIXDULPTWFZHVMQBOKJEGS"
EXAMPLE_KEY = {"order": ORDER, "row": 9}


class TestDiskData(unittest.TestCase):
    def test_twenty_five_permutation_disks(self):
        table = disks()
        self.assertEqual(len(table), 25)
        for disk in table:
            self.assertEqual(sorted(disk), list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))

    def test_disks_are_identified_by_the_letter_after_a(self):
        table = disks()
        for index, disk in enumerate(table):
            self.assertTrue(disk.startswith("A"), f"disk {index} is not A-normalised")
            self.assertEqual(disk[1], DISK_IDS[index])

    def test_standard_army_disk_is_present(self):
        # Disk 17 of the historical device spells ARMY OF THE US around its
        # rim (prc68.com/I/M94.shtml); if this moves, the shipped data is no
        # longer the standard Mauborgne set.
        self.assertIn("ARMYOFTHEUS", disks()[16])

    def test_disks_are_cached(self):
        self.assertIs(disks(), disks())


class TestParseKey(unittest.TestCase):
    def test_dict_form(self):
        self.assertEqual(parse_key({"order": ORDER, "row": 4}), (ORDER, 4))

    def test_dict_row_defaults_to_one(self):
        self.assertEqual(parse_key({"order": ORDER}), (ORDER, 1))

    def test_bare_letter_string(self):
        self.assertEqual(parse_key(ORDER), (ORDER, 1))

    def test_number_list_form(self):
        numbers = [DISK_IDS.index(ch) + 1 for ch in ORDER]
        self.assertEqual(parse_key(numbers), (ORDER, 1))
        self.assertEqual(parse_key(list(numbers)), (ORDER, 1))

    def test_separated_numbers_form(self):
        numbers = [DISK_IDS.index(ch) + 1 for ch in ORDER]
        self.assertEqual(parse_key(" ".join(str(n) for n in numbers)), (ORDER, 1))
        self.assertEqual(parse_key(",".join(str(n) for n in numbers)), (ORDER, 1))

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            parse_key("ABC")

    def test_rejects_repeated_disk(self):
        with self.assertRaises(ValueError):
            parse_key("A" * 25 if "A" in DISK_IDS else ORDER[:-1] + ORDER[0])

    def test_rejects_non_disk_letters(self):
        with self.assertRaises(ValueError):
            parse_key("A" + ORDER[1:])  # there is no disk A

    def test_rejects_bad_numbers(self):
        with self.assertRaises(ValueError):
            parse_key([1] * 25)
        with self.assertRaises(ValueError):
            parse_key(list(range(1, 26))[::-1] + [1])  # 26 entries

    def test_rejects_bad_row(self):
        with self.assertRaises(ValueError):
            parse_key({"order": ORDER, "row": 26})
        with self.assertRaises(ValueError):
            parse_key({"order": ORDER, "row": -1})


class TestCipher(unittest.TestCase):
    def setUp(self):
        self.m94 = try_get("m94")  # the registered instance, not a twin
        self.stream = self.m94.prepare(PROSE)

    def test_registered(self):
        self.assertIs(try_get("m94"), self.m94)
        self.assertIn(self.m94, ALL_CIPHERS)
        self.assertEqual(self.m94.info.family, Family.WHEEL)

    def test_aliases_resolve(self):
        for alias in ("m-94", "csp488", "csp-488", "wheel"):
            self.assertIs(get(alias), self.m94)

    def test_round_trip_multiple_blocks(self):
        # 247 letters: ten spindle turns, so the period-25 indexing wraps.
        self.assertGreater(len(self.stream), 200)
        ciphertext = self.m94.encrypt(self.stream, EXAMPLE_KEY)
        self.assertEqual(self.m94.decrypt(ciphertext, EXAMPLE_KEY), self.stream)

    def test_round_trip_every_row(self):
        for row in (0, 1, 9, 25):
            key = {"order": ORDER, "row": row}
            self.assertEqual(self.m94.decrypt(self.m94.encrypt(self.stream, key), key), self.stream)

    def test_each_position_uses_its_own_disk(self):
        ciphertext = self.m94.encrypt("A" * 25, {"order": ORDER, "row": 1})
        # With every disk turned to A on the reading row, one turn of the
        # spindle shows the second letter of each disk in order.
        self.assertEqual(
            ciphertext, "".join(disks()[DISK_IDS.index(ch)][1] for ch in ORDER)
        )

    def test_keys_are_not_enumerable(self):
        with self.assertRaises(NotImplementedError):
            list(self.m94.keys())

    def test_example_key_is_valid(self):
        order, row = parse_key(self.m94.info.example_key)
        self.assertEqual(len(order), 25)
        self.assertTrue(0 <= row < 26)


class TestLikelihood(unittest.TestCase):
    def setUp(self):
        self.m94 = M94()
        self.ctx = CrackContext.create(budget=2.0, workers=1, hints={})

    def test_wheel_ciphertext_is_flagged(self):
        stream = self.m94.prepare(PROSE)
        ciphertext = self.m94.encrypt(stream, EXAMPLE_KEY)
        self.assertGreater(self.m94.likelihood(ciphertext, self.ctx), 0.4)

    def test_plain_text_is_not(self):
        # Monoalphabetic text has no wheel structure to find: the whole-text
        # IC gate must reject it before any period hunting starts.
        self.assertEqual(self.m94.likelihood(PROSE, self.ctx), 0.0)

    def test_short_text_is_not(self):
        ciphertext = self.m94.encrypt(PROSE[:60], EXAMPLE_KEY)
        self.assertEqual(self.m94.likelihood(ciphertext, self.ctx), 0.0)


class TestHintedKey(unittest.TestCase):
    def test_hint_produces_the_exact_plaintext(self):
        m94 = M94()
        stream = m94.prepare(PROSE)
        ciphertext = m94.encrypt(stream, EXAMPLE_KEY)
        ctx = CrackContext.create(budget=2.0, workers=1, hints={"key": EXAMPLE_KEY})
        candidates = list(m94.crack(ciphertext, ctx))
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.plaintext, stream)
        self.assertEqual(candidate.key, {"order": ORDER, "row": 9})
        self.assertEqual(candidate.notes["method"], "hinted key")

    def test_hint_accepts_every_documented_key_form(self):
        m94 = M94()
        stream = m94.prepare(PROSE)
        ciphertext = m94.encrypt(stream, EXAMPLE_KEY)
        numbers = [DISK_IDS.index(ch) + 1 for ch in ORDER]
        for hint in (EXAMPLE_KEY, ORDER, numbers, " ".join(map(str, numbers))):
            with self.subTest(hint=hint):
                ctx = CrackContext.create(budget=2.0, workers=1, hints={"key": hint})
                candidates = list(m94.crack(ciphertext, ctx))
                self.assertEqual(candidates[0].plaintext, stream)


class TestBestReading(unittest.TestCase):
    def test_true_order_and_row_win(self):
        from buttcrack.ciphers.wheel import best_reading

        m94 = M94()
        stream = m94.prepare(PROSE)
        row = 17
        ciphertext = m94.encrypt(stream, {"order": ORDER, "row": row})
        model = get_model("english")
        fitness, best_row, plain = best_reading(ciphertext, ORDER, model)
        self.assertEqual(best_row, row)
        self.assertEqual(plain, stream)
        # A wrong order has no row that reads this well.
        wrong = ORDER[1:] + ORDER[0]
        wrong_fitness, _, _ = best_reading(ciphertext, wrong, model)
        self.assertGreater(fitness, wrong_fitness + 0.5)


class TestCrackBelowMinimum(unittest.TestCase):
    def test_hinted_plaintext_is_not_truncated_at_the_scoring_window(self):
        # The search scores a 400-letter window; the answer must not inherit
        # that cap.  644 letters is the length of the shipped example puzzle.
        m94 = M94()
        text = PROSE * 2
        stream = m94.prepare(text)
        self.assertGreater(len(stream), 400)
        ciphertext = m94.encrypt(stream, EXAMPLE_KEY)
        ctx = CrackContext.create(budget=2.0, workers=1, hints={"key": ORDER})
        candidates = list(m94.crack(ciphertext, ctx))
        self.assertEqual(candidates[0].plaintext, stream)
        self.assertEqual(len(candidates[0].plaintext), len(stream))

    def test_short_input_is_skipped_unless_exhaustive(self):
        m94 = M94()
        ciphertext = m94.encrypt(PROSE[:80], EXAMPLE_KEY)
        ctx = CrackContext.create(budget=2.0, workers=1, hints={})
        self.assertEqual(list(m94.crack(ciphertext, ctx)), [])


@unittest.skipUnless(SLOW, "the unhinted wheel search is a hill climb with restarts")
class TestCrackSlow(unittest.TestCase):
    def test_recovers_a_secret_order(self):
        # 247 letters: inside the honest-evidence range, below the 400-letter
        # scoring window.
        m94 = M94()
        stream = m94.prepare(PROSE)
        key = {"order": ORDER, "row": 9}
        ciphertext = m94.encrypt(stream, key)
        ctx = CrackContext.create(budget=30.0, workers=2, hints={})
        candidates = list(m94.crack(ciphertext, ctx))
        self.assertTrue(candidates)
        best = candidates[0]
        self.assertEqual(best.key, key)
        self.assertEqual(best.plaintext, stream)

    def test_recovers_a_secret_order_past_the_scoring_window(self):
        # 644 letters: past the 400-letter scoring window, so a cap leaking
        # into the reported plaintext (the bug the example-puzzle checker
        # caught) would truncate the answer.  Measured 3/3 exact solves at
        # this length inside a 20 s slice.
        m94 = M94()
        stream = m94.prepare(PROSE * 2)
        key = {"order": ORDER, "row": 4}
        ciphertext = m94.encrypt(stream, key)
        ctx = CrackContext.create(budget=25.0, workers=2, hints={})
        candidates = list(m94.crack(ciphertext, ctx))
        self.assertTrue(candidates)
        best = candidates[0]
        self.assertEqual(best.key, key)
        self.assertEqual(best.plaintext, stream)
        self.assertEqual(len(best.plaintext), len(stream))

    def test_engine_names_the_wheel_cipher(self):
        from buttcrack.engine import solve

        m94 = M94()
        stream = m94.prepare(PROSE)
        key = {"order": ORDER, "row": 4}
        report = solve(m94.encrypt(stream, key), budget=90.0, workers=2)
        self.assertTrue(report.solved)
        self.assertEqual(report.cipher, "m94")
        self.assertEqual(letters_only(report.plaintext), stream)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
