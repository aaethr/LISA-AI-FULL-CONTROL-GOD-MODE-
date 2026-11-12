import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from system_monitor import (
    analyze_metrics,
    collect_daily_snapshot_if_missing,
    get_daily_history,
    save_daily_snapshot,
)


class SystemAnalysisTests(unittest.TestCase):
    def test_normal_metrics_have_no_findings(self):
        result = analyze_metrics(cpu_percent=25, ram_percent=60, disk_free_percent=40)

        self.assertEqual(result["health_score"], 100)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["findings"], [])

    def test_high_resource_use_produces_actionable_findings(self):
        result = analyze_metrics(cpu_percent=91, ram_percent=86, disk_free_percent=14)

        self.assertEqual(result["health_score"], 40)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(len(result["findings"]), 3)
        self.assertTrue(all(finding["recommendation"] for finding in result["findings"]))

    def test_critical_metrics_are_flagged(self):
        result = analyze_metrics(cpu_percent=99, ram_percent=96, disk_free_percent=5)

        self.assertEqual(result["status"], "attention")
        self.assertTrue(all(item["severity"] == "critical" for item in result["findings"]))


class DailySnapshotTests(unittest.TestCase):
    def test_saves_one_updatable_snapshot_per_day(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "monitor.sqlite3"
            measured_at = datetime.now().astimezone().isoformat(timespec="seconds")
            first = {"measured_at": measured_at, "health_score": 90}
            updated = {"measured_at": measured_at, "health_score": 95}

            save_daily_snapshot(first, database_path)
            save_daily_snapshot(updated, database_path)

            reports = get_daily_history(30, database_path)
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["health_score"], 95)

    def test_history_is_empty_when_no_database_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "missing.sqlite3"

            self.assertEqual(get_daily_history(7, database_path), [])

    def test_existing_daily_snapshot_is_not_collected_again(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "monitor.sqlite3"
            report = {
                "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "health_score": 90,
            }
            with patch("system_monitor.DATABASE_PATH", database_path):
                with patch("system_monitor.collect_system_report", return_value=report) as collect:
                    self.assertTrue(collect_daily_snapshot_if_missing())
                    self.assertFalse(collect_daily_snapshot_if_missing())

            collect.assert_called_once_with()
            self.assertEqual(get_daily_history(1, database_path)[0]["health_score"], 90)


if __name__ == "__main__":
    unittest.main()
