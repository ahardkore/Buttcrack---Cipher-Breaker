"""The self-test's own guarantees: that its budgets fit the machine it runs on.

The release gate runs ``buttcrack selftest`` inside the installed build on a CI
runner, and every budget in it is wall-clock.  Measured on one machine and spent
on another, two checks crossed their budgets on a slow runner and turned a green
release red -- twice, on code that had not changed.  These tests cover the
measurement that replaced the padding, so the padding cannot come back.

Nothing here measures the machine it is running on: a test that passes on a fast
box and fails on a slow one is the bug this module exists to remove.
"""

from __future__ import annotations

import unittest
from unittest import mock

from buttcrack import selftest


def _always(seconds: float):
    """A ``_calibration`` that reports the same number of seconds every time."""

    def calibration(_model):  # noqa: ANN001, ANN202 - stands in for the real one
        return seconds

    return calibration


class BudgetScalingTests(unittest.TestCase):
    def tearDown(self) -> None:
        # Nothing here may leave a stretched scale behind for the next test.
        selftest._BUDGET_SCALE = 1.0

    def test_the_budgets_are_as_measured_when_the_machine_is_as_fast(self) -> None:
        with mock.patch.object(selftest, "_BUDGET_SCALE", 1.0):
            self.assertEqual(selftest._budget(10.0), 10.0)
            self.assertEqual(selftest._budget(30.0), 30.0)

    def test_a_slower_machine_gets_more_room(self) -> None:
        with mock.patch.object(selftest, "_BUDGET_SCALE", 1.5):
            self.assertEqual(selftest._budget(8.0), 12.0)
            self.assertEqual(selftest._budget(30.0), 45.0)

    def test_the_factor_is_never_below_one(self) -> None:
        with mock.patch.object(selftest, "_calibration", _always(0.0001)):
            self.assertEqual(selftest.speed_factor(), 1.0, "a fast machine must not shrink a budget")

    def test_the_factor_stops_at_three(self) -> None:
        with mock.patch.object(selftest, "_calibration", _always(9.0)):
            self.assertEqual(selftest.speed_factor(), 3.0, "three times slower is where stretching stops")

    def test_the_best_of_three_runs_is_used(self) -> None:
        # A build runner shares its box with other jobs: one slow run is noise.
        seen: list[float] = []

        def varied(_model):  # noqa: ANN001, ANN202 - stands in for the real one
            seen.append(1.0)
            return (1.0, 0.27, 0.9)[len(seen) - 1]

        with mock.patch.object(selftest, "_calibration", varied):
            self.assertAlmostEqual(selftest.speed_factor(), 1.0, places=3)
        self.assertEqual(len(seen), 3, "the factor should be the best of three runs")

    def test_a_box_without_the_language_model_is_not_an_error(self) -> None:
        # Patched where speed_factor looks it up -- the module's own name, not
        # buttcrack.lang's: patching the latter leaves the real model loading,
        # so this test measured the machine instead of the error path and then
        # passed or failed on how fast that machine was.
        with mock.patch.object(selftest, "get_model", side_effect=OSError("no model")):
            self.assertEqual(selftest.speed_factor(), 1.0)

    def test_every_break_budget_goes_through_the_scale(self) -> None:
        # The wiring rather than the arithmetic: all forty-seven budgeted
        # searches have to be stretched, because the one that is not is the one
        # that fails on the runner.
        asked: list[float | None] = []

        def refuse(_ciphertext, budget=None, **_kwargs):  # noqa: ANN001, ANN202 - the seam under test
            asked.append(budget)
            raise RuntimeError("not solving anything today")

        table = [case[4] for case in selftest.QUICK_BREAKS] + [case[3] for case in selftest.STACK_BREAKS]
        with mock.patch.object(selftest, "solve", refuse), mock.patch.object(selftest, "_BUDGET_SCALE", 1.25):
            selftest.check_breaks(selftest.SelfTestReport(), False, True, 1, progress=None)
        self.assertEqual(asked, [budget * 1.25 for budget in table])

    def test_the_other_budgeted_checks_go_through_it_too(self) -> None:
        asked: list[float | None] = []

        def refuse(_ciphertext, budget=None, **_kwargs):  # noqa: ANN001, ANN202 - the seam under test
            asked.append(budget)
            raise RuntimeError("not solving anything today")

        with mock.patch.object(selftest, "solve", refuse), mock.patch.object(selftest, "_BUDGET_SCALE", 2.0):
            selftest.check_languages(selftest.SelfTestReport(), False)
            selftest.check_report_shape(selftest.SelfTestReport(), False)
        self.assertTrue(asked, "the language and report checks should be budgeted too")
        for budget in asked:
            self.assertIsNotNone(budget)
            self.assertTrue(
                any(abs(budget - candidate * 2.0) < 1e-9 for candidate in (8.0, 10.0, 30.0)),
                f"{budget} is not one of the scaled budgets",
            )


if __name__ == "__main__":
    unittest.main()
