"""
Unit test suite for Phase 3: Active Directory connection, SMB share discovery & ACL,
and Windows network drive mapping management (WNetAddConnection2).
"""
import sys
import unittest
from pathlib import Path

# Ensure sharenet directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.ad_service import ActiveDirectoryService
from services.smb_service import SMBService
from services.drive_mapping_service import DriveMappingService

class TestActiveDirectoryPhase3(unittest.TestCase):
    def setUp(self):
        self.ad = ActiveDirectoryService(mock_mode=True)

    def test_domain_info_retrieval(self):
        info = self.ad.get_domain_info()
        self.assertIn('domain', info)
        self.assertIn('domain_controller', info)
        self.assertIn('current_user', info)

    def test_dc_connectivity_ping(self):
        res = self.ad.test_dc_connectivity('DC01.company.local')
        self.assertTrue(res['online'])
        self.assertIsNotNone(res['latency_ms'])
        self.assertEqual(res['port'], 389)

    def test_user_account_details(self):
        details = self.ad.get_user_account_details('admin')
        self.assertTrue(details['found'])
        self.assertIn('Domain Admins', details['groups'])
        self.assertTrue(details['is_enabled'])
        self.assertEqual(details['email'], 'admin@company.local')

    def test_group_membership_check(self):
        is_admin = self.ad.check_user_in_group('admin', 'Domain Admins')
        self.assertTrue(is_admin)

        is_finance = self.ad.check_user_in_group('john.doe', 'Finance-Dept')
        self.assertTrue(is_finance)

        is_not_admin = self.ad.check_user_in_group('john.doe', 'Domain Admins')
        self.assertFalse(is_not_admin)

    def test_secure_authentication_success(self):
        res = self.ad.authenticate_user('admin', 'CorrectSecurePass123!')
        self.assertTrue(res['success'])
        self.assertEqual(res['username'], 'admin')
        self.assertIn('user_details', res)

    def test_secure_authentication_failure(self):
        res = self.ad.authenticate_user('admin', 'wrong')
        self.assertFalse(res['success'])

class TestSMBDiscoveryPhase3(unittest.TestCase):
    def setUp(self):
        self.smb = SMBService(mock_mode=True)

    def test_ping_smb_server(self):
        res = self.smb.ping_smb_server('FS01.company.local')
        self.assertTrue(res['online'])
        self.assertEqual(res['port'], 445)
        self.assertIsNotNone(res['latency_ms'])

    def test_enumerate_shares_without_admin(self):
        shares = self.smb.enumerate_shares('FS01.company.local', include_admin=False)
        self.assertTrue(len(shares) > 0)
        for s in shares:
            self.assertFalse(s['is_admin'], f"Admin share found when not requested: {s['name']}")

    def test_enumerate_shares_with_admin(self):
        shares = self.smb.enumerate_shares('FS01.company.local', include_admin=True)
        admin_shares = [s for s in shares if s['is_admin']]
        self.assertTrue(len(admin_shares) > 0)
        names = [s['name'] for s in admin_shares]
        self.assertTrue('C$' in names or 'ADMIN$' in names)

    def test_check_share_permissions(self):
        # Public share should have read/write
        pub_perm = self.smb.check_share_permissions('\\\\FS01.company.local\\Public')
        self.assertEqual(pub_perm['access_level'], 'read_write')
        self.assertTrue(pub_perm['can_read'])
        self.assertTrue(pub_perm['can_write'])

        # Finance share should be read-only
        fin_perm = self.smb.check_share_permissions('\\\\FS01.company.local\\Finance_Reports')
        self.assertEqual(fin_perm['access_level'], 'read_only')
        self.assertTrue(fin_perm['can_read'])
        self.assertFalse(fin_perm['can_write'])

        # HR share should be access denied
        hr_perm = self.smb.check_share_permissions('\\\\FS01.company.local\\HR_Personnel')
        self.assertEqual(hr_perm['access_level'], 'denied')
        self.assertFalse(hr_perm['can_read'])

    def test_share_storage_metrics(self):
        storage = self.smb.get_share_storage('\\\\FS01.company.local\\Public')
        self.assertIn('total_gb', storage)
        self.assertIn('free_gb', storage)
        self.assertIn('used_percent', storage)
        self.assertTrue(storage['total_gb'] > 0)

    def test_filter_shares(self):
        shares = self.smb.enumerate_shares('FS01.company.local', include_admin=True)
        filtered = self.smb.filter_shares(shares, query='finance', show_admin=False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'Finance_Reports')

class TestDriveMappingPhase3(unittest.TestCase):
    def setUp(self):
        self.drive = DriveMappingService(mock_mode=True)

    def test_get_existing_drives(self):
        drives = self.drive.get_existing_network_drives()
        self.assertTrue(len(drives) > 0)
        letters = [d['drive_letter'] for d in drives]
        self.assertIn('Z:', letters)

    def test_suggest_best_drive_letter(self):
        suggested = self.drive.suggest_best_drive_letter()
        # Since Z: and Y: are taken in default mock, should be X:
        self.assertEqual(suggested, 'X:')

    def test_map_drive_persistent(self):
        success, msg = self.drive.map_drive('W:', '\\\\FS01.company.local\\Software_Repository', persistent=True)
        self.assertTrue(success)
        drives = self.drive.get_existing_network_drives()
        mapped_letters = [d['drive_letter'] for d in drives]
        self.assertIn('W:', mapped_letters)

        # Find W: in list and verify persistent
        w_drive = next(d for d in drives if d['drive_letter'] == 'W:')
        self.assertTrue(w_drive.get('is_persistent'))

    def test_prevent_duplicate_mapping(self):
        success, msg = self.drive.map_drive('Z:', '\\\\FS01.company.local\\Duplicate')
        self.assertFalse(success)
        self.assertIn('استفاده می‌شود', msg)

    def test_disconnect_drive(self):
        success, msg = self.drive.disconnect_drive('Y:')
        self.assertTrue(success)
        drives = self.drive.get_existing_network_drives()
        mapped_letters = [d['drive_letter'] for d in drives]
        self.assertNotIn('Y:', mapped_letters)

    def test_recommended_presets(self):
        presets = self.drive.get_recommended_presets('FS01.company.local')
        self.assertEqual(len(presets), 4)
        letters = [p['drive_letter'] for p in presets]
        self.assertIn('P:', letters)
        self.assertIn('F:', letters)

if __name__ == '__main__':
    unittest.main()
