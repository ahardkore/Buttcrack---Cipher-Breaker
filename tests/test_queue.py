import unittest

from buttcrack.queue import AttackQueue


class QueueTests(unittest.TestCase):
    def test_queue_runs_in_order_and_records_failure(self):
        queue = AttackQueue()
        queue.add("first", lambda: {"score": -5})
        queue.add("bad", lambda: 1 / 0)
        self.assertEqual(queue.run_next().status, "completed")
        self.assertEqual(queue.run_next().status, "failed")
        self.assertEqual(queue.checkpoint()[1]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
