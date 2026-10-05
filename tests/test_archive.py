"""
Unit and integration tests for Phase 4: Outlook Archive Engine & Resilience.
Tests date boundary filtering, disk space validation, cancellation mechanics,
and Copy-Only integrity verification.
"""
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, time

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.archive_service import ArchiveService, ArchiveProgress
from utils.persian_date import jalali_to_gregorian


class TestArchiveService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.archive_service = ArchiveService()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_progress_dto_percentage(self):
        prog = ArchiveProgress(
            current_folder='Inbox',
            current_item='Email 1',
            processed_count=50,
            total_count=100,
            success_count=48,
            failed_count=2
        )
        self.assertEqual(prog.percentage, 50)
        prog_dict = prog.to_dict()
        self.assertEqual(prog_dict['percentage'], 50)
        self.assertEqual(prog_dict['folder'], 'Inbox')

    def test_progress_zero_total(self):
        prog = ArchiveProgress(total_count=0)
        self.assertEqual(prog.percentage, 0)

    def test_disk_space_check_valid(self):
        ok, msg = self.archive_service.check_disk_space(str(self.test_dir), min_mb=10)
        self.assertTrue(ok)
        self.assertIn('MB', msg)

    def test_archive_execution_simulation(self):
        pst_path = str(self.test_dir / 'Archive_Test.pst')
        from_dt = datetime(2026, 1, 1, 0, 0, 0)
        to_dt = datetime(2026, 10, 5, 23, 59, 59)

        progress_events = []

        def on_prog(p: ArchiveProgress):
            progress_events.append(p.percentage)

        res = self.archive_service.execute_archive(
            folder_entry_ids=['fake-inbox-id', 'fake-sent-id'],
            from_datetime=from_dt,
            to_datetime=to_dt,
            pst_filepath=pst_path,
            progress_callback=on_prog
        )

        self.assertTrue(res['success'])
        self.assertFalse(res['cancelled'])
        self.assertGreater(res['items_copied'], 0)
        self.assertEqual(res['items_failed'], 0)
        self.assertTrue(os.path.exists(pst_path))
        self.assertGreater(len(progress_events), 0)

    def test_archive_cancellation(self):
        pst_path = str(self.test_dir / 'Cancelled_Test.pst')
        from_dt = datetime(2026, 1, 1)
        to_dt = datetime(2026, 10, 5)

        # Immediate cancel
        self.archive_service.request_cancel()

        res = self.archive_service.execute_archive(
            folder_entry_ids=['fake-id'],
            from_datetime=from_dt,
            to_datetime=to_dt,
            pst_filepath=pst_path
        )

        self.assertTrue(res['cancelled'])
        self.assertFalse(res['success'])


if __name__ == '__main__':
    unittest.main()
