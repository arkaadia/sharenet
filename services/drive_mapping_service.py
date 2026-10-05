"""
Windows Network Drive Mapping Service (Phase 3).
Maps, disconnects, tests, and manages SMB network drives using real Windows
WNetAddConnection2 and WNetCancelConnection2 APIs with persistent profile support,
smart drive-letter assignment, and corporate presets.
"""
import sys
from typing import List, Dict, Any, Tuple, Optional
from utils.windows_utils import is_windows, get_occupied_drive_letters, get_available_drive_letters
from utils.logging_utils import get_logger

logger = get_logger('drive_mapping_service')

# Windows WNet Constants
CONNECT_UPDATE_PROFILE = 0x00000001  # Persist connection across Windows logons
CONNECT_INTERACTIVE    = 0x00000008  # Prompt user if needed
CONNECT_PROMPT         = 0x00000010  # Force credentials dialog
CONNECT_REDIRECT       = 0x00000080

class DriveMappingService:
    """Enterprise service for mapping, unmapping, and maintaining Windows network drives."""

    def __init__(self, mock_mode: Optional[bool] = None):
        self.mock_mode = mock_mode if mock_mode is not None else (sys.platform != 'win32')
        # In-memory mapped drives catalog for testing and non-Windows environments
        self._mock_mappings: Dict[str, Dict[str, Any]] = {
            'Z:': {
                'drive_letter': 'Z:',
                'unc_path': '\\\\FS01.company.local\\Public',
                'status': 'connected',
                'is_persistent': True,
                'total_gb': 1024,
                'free_gb': 382
            },
            'Y:': {
                'drive_letter': 'Y:',
                'unc_path': '\\\\FS01.company.local\\Finance_Reports',
                'status': 'connected',
                'is_persistent': False,
                'total_gb': 512,
                'free_gb': 210
            }
        }

    def get_existing_network_drives(self) -> List[Dict[str, Any]]:
        """
        Lists all currently mapped network drives and their UNC remote paths.
        Includes connection status and persistent reconnect setting.
        """
        mappings = []

        # Real Windows WNetOpenEnum
        if sys.platform == 'win32' and not self.mock_mode:
            try:
                import win32wnet
                import win32netcon
                handle = win32wnet.WNetOpenEnum(
                    win32netcon.RESOURCE_CONNECTED,
                    win32netcon.RESOURCETYPE_DISK,
                    0,
                    None
                )
                try:
                    while True:
                        items = win32wnet.WNetEnumResource(handle, 64)
                        if not items:
                            break
                        for item in items:
                            local_name = getattr(item, 'lpLocalName', '')
                            remote_name = getattr(item, 'lpRemoteName', '')
                            if local_name:
                                clean_local = local_name.strip().upper()
                                if not clean_local.endswith(':'):
                                    clean_local = f'{clean_local}:'
                                mappings.append({
                                    'drive_letter': clean_local,
                                    'unc_path': remote_name,
                                    'status': 'connected',
                                    'is_persistent': True
                                })
                finally:
                    win32wnet.WNetCloseEnum(handle)
            except Exception as e:
                logger.warning(f'Could not enumerate connected network drives: {e}')
            return mappings

        # Mock / Test Fallback
        return list(self._mock_mappings.values())

    def get_available_letters(self) -> List[str]:
        """Returns drive letters not currently in use (ordered Z to D)."""
        if sys.platform == 'win32' and not self.mock_mode:
            free = get_available_drive_letters()
            if free:
                return free
        # Calculate available letters against mock
        occupied = set(self._mock_mappings.keys())
        all_possible = [f'{chr(c)}:' for c in range(ord('Z'), ord('C'), -1)]
        return [l for l in all_possible if l not in occupied]

    def suggest_best_drive_letter(self) -> str:
        """Suggests the highest available drive letter (typically Z:, Y:, etc.)."""
        letters = self.get_available_letters()
        return letters[0] if letters else 'Z:'

    def map_drive(self, drive_letter: str, unc_path: str,
                  username: Optional[str] = None,
                  password: Optional[str] = None,
                  persistent: bool = True) -> Tuple[bool, str]:
        """
        Maps UNC path to a local drive letter using WNetAddConnection2.
        Supports persistent connection profile (CONNECT_UPDATE_PROFILE).
        """
        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(':'):
            clean_drive = f'{clean_drive}:'

        clean_unc = unc_path.strip().replace('/', '\\')
        if not clean_unc.startswith('\\\\'):
            clean_unc = f'\\\\{clean_unc}'

        # Check if already occupied
        current_drives = [d['drive_letter'] for d in self.get_existing_network_drives()]
        if clean_drive in current_drives:
            return False, f'حرف درایو {clean_drive} در حال حاضر توسط منبع دیگری استفاده می‌شود.'

        # Real Windows WNetAddConnection2
        if sys.platform == 'win32' and not self.mock_mode:
            try:
                import win32wnet
                import win32netcon

                flags = CONNECT_UPDATE_PROFILE if persistent else 0
                net_resource = {
                    'dwType': win32netcon.RESOURCETYPE_DISK,
                    'lpLocalName': clean_drive,
                    'lpRemoteName': clean_unc,
                    'lpProvider': None
                }

                # Attempt drive mapping
                win32wnet.WNetAddConnection2(
                    net_resource,
                    password if password else None,
                    username if username else None,
                    flags
                )

                logger.info(f'Drive {clean_drive} mapped successfully to {clean_unc} (persistent={persistent}).')
                persistence_msg = 'دائمی (با راه‌اندازی مجدد سیستم حفظ می‌شود)' if persistent else 'موقتی'
                return True, f'درایو شبکه {clean_drive} با موفقیت به {clean_unc} متصل شد ({persistence_msg}).'
            except Exception as e:
                err_str = str(e)
                logger.error(f'Failed to map drive {clean_drive} to {clean_unc}: {err_str}')
                # Parse common Windows error codes
                if '85' in err_str:
                    return False, f'حرف درایو {clean_drive} قبلاً اختصاص یافته است (خطای ۸۵).'
                elif '67' in err_str or '53' in err_str:
                    return False, f'مسیر سرور شبکه {clean_unc} پیدا نشد یا در دسترس نیست.'
                elif '1326' in err_str or '86' in err_str:
                    return False, 'نام کاربری یا کلمه عبور شبکه برای اتصال به این پوشه نادرست است.'
                elif '1202' in err_str:
                    return False, f'حرف درایو {clean_drive} در حافظه ویندوز ثبت است؛ ابتدا آن را قطع کنید.'
                return False, f'خطا در اتصال درایو شبکه {clean_drive}: {err_str}'

        # Mock / Simulation mode
        self._mock_mappings[clean_drive] = {
            'drive_letter': clean_drive,
            'unc_path': clean_unc,
            'status': 'connected',
            'is_persistent': persistent,
            'total_gb': 1024,
            'free_gb': 450
        }
        logger.info(f'[MOCK] Drive {clean_drive} mapped to {clean_unc} (persistent={persistent}).')
        persistence_msg = 'دائمی (با راه‌اندازی مجدد سیستم حفظ می‌شود)' if persistent else 'موقتی'
        return True, f'درایو شبکه {clean_drive} با موفقیت به مسیر {clean_unc} متصل شد ({persistence_msg}).'

    def disconnect_drive(self, drive_letter: str, force: bool = True, update_profile: bool = True) -> Tuple[bool, str]:
        """
        Disconnects an active mapped network drive using WNetCancelConnection2.
        Optionally removes from persistent user profile.
        """
        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(':'):
            clean_drive = f'{clean_drive}:'

        if sys.platform == 'win32' and not self.mock_mode:
            try:
                import win32wnet
                flags = CONNECT_UPDATE_PROFILE if update_profile else 0
                win32wnet.WNetCancelConnection2(clean_drive, flags, 1 if force else 0)
                logger.info(f'Drive {clean_drive} disconnected successfully.')
                return True, f'اتصال درایو شبکه {clean_drive} با موفقیت قطع گردید.'
            except Exception as e:
                err_str = str(e)
                logger.error(f'Failed to disconnect drive {clean_drive}: {err_str}')
                if '2250' in err_str:
                    return False, f'اتصال شبکه فعالی روی درایو {clean_drive} یافت نشد (خطای ۲۲۵۰).'
                return False, f'خطا در قطع درایو {clean_drive}: {err_str}'

        # Mock / Simulation mode
        if clean_drive in self._mock_mappings:
            del self._mock_mappings[clean_drive]
            logger.info(f'[MOCK] Drive {clean_drive} disconnected.')
            return True, f'اتصال درایو شبکه {clean_drive} با موفقیت قطع گردید.'
        return False, f'درایو {clean_drive} در لیست درایوهای فعال یافت نشد.'

    def get_recommended_presets(self, server_name: str = 'FS01.company.local') -> List[Dict[str, str]]:
        """Returns standard corporate preset mappings for enterprise environments."""
        clean_srv = server_name.strip().lstrip('\\')
        return [
            {'drive_letter': 'P:', 'unc_path': f'\\\\{clean_srv}\\Public', 'label_fa': 'پوشه عمومی (Public Share)'},
            {'drive_letter': 'F:', 'unc_path': f'\\\\{clean_srv}\\Finance_Reports', 'label_fa': 'پوشه مالی و گزارش‌ها (Finance)'},
            {'drive_letter': 'S:', 'unc_path': f'\\\\{clean_srv}\\Software_Repository', 'label_fa': 'نرم‌افزارها و ابزارها (Software)'},
            {'drive_letter': 'H:', 'unc_path': f'\\\\{clean_srv}\\Users\\%USERNAME%', 'label_fa': 'پوشه شخصی پرسنل (Home Drive)'},
        ]
