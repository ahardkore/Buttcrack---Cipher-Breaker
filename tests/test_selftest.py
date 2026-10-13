"""The self-test's own guarantees: that its budgets fit the machine it runs on.

The release gate runs ``buttcrack selftest`` inside the installed build on a CI
runner, and every budget in it is wall-clock.  Measured on one machine and spent
on another, two checks crossed their budgets on a slow runner and turned a green
release red -- twice, on code that had not changed.  These tests cover the
measurement that replaced the padding, so the padding cannot come back.
"""

from __future__ import annotations

import unittest
from unittest import mock

from buttcrack import selftest


class BudgetScalingTests(unittest.TestCase):
    def test_a_machine_as_fast_as_the_reference_keeps_the_budgets(self):
        self.assertEqual(selftest._budget(10.0), 10.0)

    def test_the_measurement_stretches_every_budget(self):
        with mock.patch.object(selftest, "_BUDGET_SCALE", 1.5):
            self.assertEqual(selftest._budget(8.0), 12.0)
            self.assertEqual(selftest._budget(30.0), 45.0)

    def test_the_factor_is_clamped_at_both_ends(self):
        with mock.patch.object(selftest, "_calibration", side_effect=[0.0001, 0.0001, 0.0001]):
            self.assertEqual(selftest.speed_factor(), 1.0, "a fast machine must not shrink a budget")
        with mock.patch.object(selftest, "_calibration", side_effect=[9.0, 9.0, 9.0]):
            self.assertEqual(selftest.speed_factor(), 3.0, "three times slower is where stretching stops")

    def test_the_best_of_three_runs_is_used(self):
        # A build runner shares its box with other jobs: one slow run is noise.
        with mock.patch.object(selftest, "_calibration", side_effect=[1.0, 0.27, 0.9]):
            self.assertAlmostEqual(selftest.speed_factor(), 1.0, places=3)

    def test_a_box_without_the_language_model_is_not_an_error(self):
        with mock.patch("buttcrack.lang.get_model", side_effect=OSError("no model")):
            self.assertEqual(selftest.speed_factor(), 1.0)

    def test_the_reference_constant_is_still_about_right(self):
        # The constant was measured on a plain box, not invented.  This is the
        # reminder to re-measure it if the calibration loop ever changes; the
        # tolerance is wide on purpose, because test runners are not idle.
        measured = min(selftest._calibration(selftest.get_model("english")) for _ in range(3))
        self.assertGreater(measured, selftest._REFERENCE_CALIBRATION * 0.5)
        self.assertLess(measured, selftest._REFERENCE_CALIBRATION * 2.0)


if __name__ == "__main__":
    unittest.main()
