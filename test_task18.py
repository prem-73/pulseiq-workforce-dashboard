import unittest
import pandas as pd

from role_permissions import (
    can_access_metric,
    get_minimum_group_size,
    is_group_visible,
    suppress_small_groups,
)

class Task18PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.dictionary = pd.DataFrame([
            {"metric_id": "M01", "minimum_group_size": 5},
            {"metric_id": "M04", "minimum_group_size": 10},
            {"metric_id": "M22", "minimum_group_size": "5 tasks"},
            {"metric_id": "M16", "minimum_group_size": ""},
        ])

    def test_role_boundaries(self):
        self.assertTrue(can_access_metric("ADMIN", "M07", "company"))
        self.assertTrue(can_access_metric("HR", "M07", "department"))
        self.assertFalse(can_access_metric("HR", "M07", "company"))
        self.assertTrue(can_access_metric("MANAGER", "M22", "team"))
        self.assertFalse(can_access_metric("MANAGER", "M22", "company"))
        self.assertTrue(can_access_metric("EXECUTIVE", "M01", "company"))
        self.assertFalse(can_access_metric("EXECUTIVE", "M01", "department"))

    def test_thresholds_fail_closed(self):
        self.assertEqual(get_minimum_group_size("M01", self.dictionary), 5)
        self.assertEqual(get_minimum_group_size("M04", self.dictionary), 10)
        self.assertEqual(get_minimum_group_size("M22", self.dictionary), 5)
        self.assertEqual(get_minimum_group_size("M16", self.dictionary), 5)
        self.assertEqual(get_minimum_group_size("UNKNOWN", self.dictionary), 5)

    def test_small_groups_hidden(self):
        self.assertFalse(is_group_visible("M04", 9, self.dictionary))
        self.assertTrue(is_group_visible("M04", 10, self.dictionary))
        self.assertFalse(is_group_visible("M01", 4, self.dictionary))
        self.assertTrue(is_group_visible("M01", 5, self.dictionary))

    def test_complementary_suppression(self):
        frame = pd.DataFrame({
            "label": ["A", "B", "C"],
            "population": [2, 20, 30],
            "value": [100, 200, 300],
        })
        safe, suppressed = suppress_small_groups(
            frame, "M01", "population", "value", "label", self.dictionary
        )
        self.assertTrue(suppressed)
        self.assertEqual((safe["KPI value"].isna()).sum(), 2)
        self.assertEqual((safe["Group"] == "Suppressed group").sum(), 2)
        self.assertNotIn(100, safe["KPI value"].dropna().tolist())

if __name__ == "__main__":
    unittest.main(verbosity=2)
