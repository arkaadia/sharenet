"""
Unit test suite for Phase 1: Windows application foundation, safe logging, settings, and Persian date.
"""
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.persian_date import (
    get_current_jalali_date, validate_jalali_date,
    jalali_to_gregorian, gregorian_to_jalali, format_archive_filename
)
from utils.logging_utils import setup_logging, get_logger, SensitiveDataFilter
from utils.windows_utils import detect_domain_info
from services.settings_service import SettingsService

class TestPersianDateUtils(unittest.TestCase):
    def test_current_jalali_date_format(self):
        curr = get_current_jalali_date()
        self.assertTrue(curr.startswith('14') or curr.startswith('13') or curr.startswith('20'))
        is_valid, err = validate_jalali_date(curr)
        self.assertTrue(is_valid, f'Validation failed for current date: {err}')

    def test_validate_jalali_date_valid(self):
        valid_dates = ['1405/07/13', '1402/01/01', '1403/06/31', '1404/11/30']
        for d in valid_dates:
            valid, err = validate_jalali_date(d)
            self.assertTrue(valid, f'Expected valid date for {d}, got error: {err}')

    def test_validate_jalali_date_invalid(self):
        invalid_dates = [
            ('', 'خالی'),
            ('invalid', 'فرمت'),
            ('1405/13/01', 'ماه'),
            ('1405/07/32', 'روز'),
            ('1200/01/01', 'سال'),
        ]
        for d, reason in invalid_dates:
            valid, err = validate_jalali_date(d)
            self.assertFalse(valid, f'Expected invalid date for {d} ({reason})')

    def test_jalali_conversion_roundtrip(self):
        greg = jalali_to_gregorian('1403/01/01')
        self.assertEqual(greg.year, 2024)
        self.assertEqual(greg.month, 3)
        self.assertEqual(greg.day, 20)

    def test_archive_filename_formatting(self):
        fname = format_archive_filename('1405/07/01', '1405/07/13')
        self.assertEqual(fname, 'Archive_1405-07-01_to_1405-07-13.pst')

class TestSafeLogging(unittest.TestCase):
    def test_sensitive_filter_redaction(self):
        s_filter = SensitiveDataFilter()
        redacted = s_filter.redact('User login with password=SuperSecret123! and token: abcxyz')
        self.assertNotIn('SuperSecret123!', redacted)
        self.assertNotIn('abcxyz', redacted)
        self.assertIn('***REDACTED***', redacted)

    def test_logger_creation(self):
        logger = get_logger('test_unit')
        self.assertIsNotNone(logger)

class TestSettingsService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.settings = SettingsService(config_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_values(self):
        self.assertEqual(self.settings.default_drive_letter, 'Z:')
        self.assertTrue(len(self.settings.default_archive_dir) > 0)

    def test_set_and_save(self):
        self.settings.default_file_server = '\\\\FS01.test.local'
        self.settings.default_drive_letter = 'Y:'
        self.assertTrue(self.settings.save())

        # Reload from disk
        reloaded = SettingsService(config_dir=self.test_dir)
        self.assertEqual(reloaded.default_file_server, '\\\\FS01.test.local')
        self.assertEqual(reloaded.default_drive_letter, 'Y:')

    def test_never_store_passwords(self):
        self.settings.set('password', 'ShouldNotBeSaved')
        self.settings.set('user_password', 'Forbidden123')
        self.settings.save()

        with open(self.settings.settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('ShouldNotBeSaved', content)
        self.assertNotIn('Forbidden123', content)

class TestDomainInfo(unittest.TestCase):
    def test_detect_domain_info_structure(self):
        info = detect_domain_info()
        self.assertIn('domain', info)
        self.assertIn('domain_controller', info)
        self.assertIn('current_user', info)
        self.assertIn('computer_name', info)
        self.assertIn('is_domain_joined', info)

if __name__ == '__main__':
    unittest.main()
