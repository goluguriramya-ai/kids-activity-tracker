"""Unit tests for kids-activity-tracker.

Run from the project folder with:
    python3 -m unittest discover -s tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

# Make `import tracker` work no matter where the tests are run from.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import tracker  # noqa: E402  (import after path setup)


class TrackerTest(unittest.TestCase):
    """Each test gets a fresh, empty data file in a temp folder."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmpdir.name, "activities.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_assigns_incrementing_ids(self):
        first = tracker.add_activity(self.data, "Aarav", "Soccer", "2026-10-08", 60, "")
        second = tracker.add_activity(self.data, "Diya", "Piano", "2026-10-08", 45, "")
        self.assertEqual((first["id"], second["id"]), (1, 2))
        self.assertFalse(first["done"])
        self.assertEqual(first["kid"], "Aarav")

    def test_list_filters_by_kid(self):
        tracker.add_activity(self.data, "Aarav", "Soccer", "2026-10-08", 60, "")
        tracker.add_activity(self.data, "Diya", "Piano", "2026-10-08", 45, "")
        only_aarav = tracker.list_activities(self.data, kid="Aarav")
        self.assertEqual(len(only_aarav), 1)
        self.assertEqual(only_aarav[0]["activity"], "Soccer")

    def test_mark_done(self):
        tracker.add_activity(self.data, "Aarav", "Soccer", "2026-10-08", 60, "")
        record = tracker.mark_done(self.data, 1)
        self.assertTrue(record["done"])
        # Unknown id returns None instead of crashing.
        self.assertIsNone(tracker.mark_done(self.data, 99))

    def test_remove(self):
        tracker.add_activity(self.data, "Aarav", "Soccer", "2026-10-08", 60, "")
        removed = tracker.remove_activity(self.data, 1)
        self.assertEqual(removed["activity"], "Soccer")
        self.assertIsNone(tracker.find_by_id(tracker.load_activities(self.data), 1))
        self.assertIsNone(tracker.remove_activity(self.data, 99))

    def test_summarize_groups_by_kid_and_date(self):
        tracker.add_activity(self.data, "Aarav", "Soccer", "2026-10-08", 60, "")
        tracker.add_activity(self.data, "Aarav", "Reading", "2026-10-08", 30, "")
        tracker.add_activity(self.data, "Diya", "Piano", "2026-10-07", 45, "")
        summary = tracker.summarize(tracker.load_activities(self.data), "2026-10-08")
        self.assertEqual(summary["Aarav"], {"total": 2, "done": 0, "minutes": 90})
        self.assertNotIn("Diya", summary)  # different day -> excluded

    def test_cli_add_and_list_end_to_end(self):
        """Full CLI round-trip: add via the real command, then list."""
        env = dict(os.environ, KIDS_TRACKER_DATA=self.data)
        script = os.path.join(PROJECT_DIR, "tracker.py")
        subprocess.run(
            [sys.executable, script, "add", "--kid", "Aarav",
             "--activity", "Soccer", "--minutes", "60"],
            check=True, env=env, capture_output=True, text=True,
        )
        result = subprocess.run(
            [sys.executable, script, "list"],
            check=True, env=env, capture_output=True, text=True,
        )
        self.assertIn("Aarav", result.stdout)
        self.assertIn("Soccer", result.stdout)


if __name__ == "__main__":
    unittest.main()
