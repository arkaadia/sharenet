"""
Windows Network Drive Mapping Service.
Maps and disconnects network drives using real Windows WNetAddConnection2 and WNetCancelConnection2 APIs.
"""
import sys
from typing import List, Dict, Any, Tuple
from utils.windows_utils import is_windows, get_occupied_drive_letters, get_available_drive_letters
from utils.logging_utils import get_logger

logger = get_logger('drive_mapping_service')

class DriveMappingService:
    """Service for mapping and unmapping SMB network drives on Windows."""
    def get_existing_network_drives(self) -> List[Dict[str, str]]:
        """
        Lists all current mapped network drives and their UNC remote paths.
        """
        mappings = []
        if not is_windows():
            return mappings

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
                            mappings.append({
                                'drive_letter': local_name,
                                'unc_path': remote_name
                            })
            finally:
                win32wnet.WNetCloseEnum(handle)
        except Exception as e:
            logger.warning(f'Could not enumerate connected network drives: {e}')

        return mappings

    def map_drive(self, drive_letter: str, unc_path: str, username: str = None, password: str = None) -> Tuple[bool, str]:
        """
        Maps UNC path to a local drive letter using WNetAddConnection2.
        """
        if not is_windows():
            return False, 'اتصال درایو شبکه تنها در ویندوز پشتیبانی می‌شود.'

        # Ensure drive letter format (e.g. 'Z:')
        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(':'):
            clean_drive = f'{clean_drive}:'

        try:
            import win32wnet
            import win32netcon

            net_resource = {
                'dwType': win32netcon.RESOURCETYPE_DISK,
                'lpLocalName': clean_drive,
                'lpRemoteName': unc_path,
                'lpProvider': None
            }

            # Map the drive
            win32wnet.WNetAddConnection2(
                net_resource,
                password if password else None,
                username if username else None,
                0  # flags
            )
            logger.info(f'Drive {clean_drive} mapped successfully to {unc_path}.')
            return True, f'درایو شبکه {clean_drive} با موفقیت به مسیر {unc_path} متصل شد.'
        except Exception as e:
            logger.error(f'Failed to map drive {clean_drive} to {unc_path}: {e}')
            return False, f'خطا در اتصال درایو شبکه: {str(e)}'

    def disconnect_drive(self, drive_letter: str, force: bool = True) -> Tuple[bool, str]:
        """
        Disconnects an active mapped network drive using WNetCancelConnection2.
        """
        if not is_windows():
            return False, 'قطع درایو شبکه تنها در ویندوز امکان‌پذیر است.'

        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(':'):
            clean_drive = f'{clean_drive}:'

        try:
            import win32wnet
            win32wnet.WNetCancelConnection2(clean_drive, 0, 1 if force else 0)
            logger.info(f'Drive {clean_drive} disconnected.')
            return True, f'درایو {clean_drive} با موفقیت قطع شد.'
        except Exception as e:
            logger.error(f'Failed to disconnect drive {clean_drive}: {e}')
            return False, f'خطا در قطع درایو {clean_drive}: {str(e)}'
