import unittest
from buttcrack.local_model import LocalModelAdapter
class LocalModelTests(unittest.TestCase):
    def test_planner_is_available_without_external_model(self):
        adapter = LocalModelAdapter()
        self.assertTrue(adapter.capabilities()[0].available)
        self.assertIn("recommendations only", adapter.prompt("KRYPTOS").lower())
    def test_external_provider_is_explicit(self):
        with self.assertRaises(NotImplementedError): LocalModelAdapter().prompt("ABC", "ollama")
if __name__ == '__main__': unittest.main()
