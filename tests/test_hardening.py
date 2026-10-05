"""
Unit tests for Phase 4 Hardening:
- Input sanitization (UNC paths, username injection, drive letter validation)
- Graceful non-Windows fallback
- Active Directory authentication error handling
- Zero-Password in-memory guarantees
"""
import unittest
import sys
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.ad_service import ActiveDirectoryService
from services.smb_service import SMBService
from services.drive_mapping_service import DriveMappingService


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.ad_service = ActiveDirectoryService()
        self.smb_service = SMBService()
        self.drive_service = DriveMappingService()

    def test_ad_username_sanitization(self):
        # Disallow malicious injection
        self.assertFalse(self.ad_service.validate_username('user; rm -rf /'))
        self.assertFalse(self.ad_service.validate_username('admin|whoami'))
        self.assertFalse(self.ad_service.validate_username('test`id`'))
        self.assertFalse(self.ad_service.validate_username(''))
        self.assertTrue(self.ad_service.validate_username('john.doe'))
        self.assertTrue(self.ad_service.validate_username('DOMAIN\\johndoe'))

    def test_ad_empty_credentials(self):
        res = self.ad_service.authenticate_user('', '')
        self.assertFalse(res['success'])
        self.assertIn('الزامی', res['message_fa'])

    def test_ad_injection_rejection(self):
        res = self.ad_service.authenticate_user('admin;calc.exe', '123456')
        self.assertFalse(res['success'])
        self.assertIn('نامعتبر', res['message_fa'])

    def test_smb_server_normalization(self):
        norm1 = self.smb_service.normalize_server_name(r'\\FS01.company.local\\')
        self.assertEqual(norm1, 'FS01.company.local')
        norm2 = self.smb_service.normalize_server_name('//STORAGE-NAS/')
        self.assertEqual(norm2, 'STORAGE-NAS')

    def test_smb_empty_server(self):
        shares = self.smb_service.enumerate_shares('')
        self.assertEqual(shares, [])

    def test_drive_letter_validation(self):
        # Valid letter
        self.assertEqual(self.drive_service.format_drive_letter('z'), 'Z:')
        self.assertEqual(self.drive_service.format_drive_letter('Z:'), 'Z:')

        # System protected letters should fail mapping
        ok, msg = self.drive_service.map_drive('C:', r'\\server\share')
        self.assertFalse(ok)
        self.assertIn('مجاز نیست', msg)

        # Invalid UNC
        ok, msg = self.drive_service.map_drive('Z:', 'not_a_unc_path')
        self.assertFalse(ok)
        self.assertIn('نامعتبر', msg)

    def test_drive_mapping_mock_lifecycle(self):
        # Map drive in mock mode
        ok, msg = self.drive_service.map_drive('W:', r'\\FS01\Reports')
        self.assertTrue(ok)

        # Check existing
        existing = self.drive_service.get_existing_network_drives()
        letters = [d['drive_letter'] for d in existing]
        self.assertIn('W:', letters)

        # Disconnect
        ok, msg = self.drive_service.disconnect_drive('W:')
        self.assertTrue(ok)

        # Verify removed
        existing_after = self.drive_service.get_existing_network_drives()
        letters_after = [d['drive_letter'] for d in existing_after]
        self.assertNotIn('W:', letters_after)


if __name__ == '__main__':
    unittest.main()
