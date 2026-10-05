import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "ble"
    / "xiaomi_scanner.py"
)

spec = importlib.util.spec_from_file_location("xiaomi_scanner", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ScannerTests(unittest.TestCase):
    def test_candidate_matching(self):
        self.assertTrue(module.is_candidate("Xiaomi Band 11", "AA:BB"))
        self.assertTrue(module.is_candidate("Redmi Watch 5", "CC:DD"))
        self.assertFalse(module.is_candidate("Bluetooth Speaker", "EE:FF"))

    def test_sort_matches(self):
        matches = [
            {"name": "unknown", "address": "1", "rssi": None},
            {"name": "strong", "address": "2", "rssi": -40},
            {"name": "weak", "address": "3", "rssi": -80},
        ]
        ordered = module.sort_matches(matches)
        self.assertEqual([item["address"] for item in ordered], ["2", "3", "1"])

    def test_sort_does_not_mutate_input(self):
        matches = [
            {"name": "a", "address": "1", "rssi": -80},
            {"name": "b", "address": "2", "rssi": -40},
        ]
        original = list(matches)
        module.sort_matches(matches)
        self.assertEqual(matches, original)


if __name__ == "__main__":
    unittest.main()
