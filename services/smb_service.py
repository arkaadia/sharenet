"""
SMB and File Server Share Discovery Service.
Enumerates network shares on file servers using Windows NetShareEnum APIs.
"""
import sys
from typing import List, Dict, Any
from utils.logging_utils import get_logger

logger = get_logger('smb_service')

class SMBService:
    """Service for discovering real SMB shares on Windows file servers."""
    def enumerate_shares(self, server_name: str) -> List[Dict[str, Any]]:
        """
        Discovers active SMB shares on the specified file server using Win32 NetShareEnum.
        """
        if not server_name:
            return []

        # Normalize server name: remove leading slashes
        clean_server = server_name.strip().lstrip('\\')
        shares = []

        if sys.platform == 'win32':
            try:
                import win32net
                import win32netcon
                entries, total, resume = win32net.NetShareEnum(clean_server, 1)
                for entry in entries:
                    share_name = entry['netname']
                    share_type = entry['type'] & 0xFFFF
                    # 0 = STYPE_DISKTREE (Disk drive share)
                    if share_type == win32netcon.STYPE_DISKTREE:
                        # Exclude hidden administrative shares (ending with $)
                        is_admin = share_name.endswith('$')
                        shares.append({
                            'name': share_name,
                            'unc_path': f'\\{clean_server}\{share_name}',
                            'remark': entry.get('remark', ''),
                            'is_admin': is_admin
                        })
                logger.info(f'Discovered {len(shares)} disk shares on {clean_server}.')
                return shares
            except Exception as e:
                logger.error(f'Failed to enumerate shares on {clean_server}: {e}')
                return []
        else:
            logger.info('SMB enumeration requires Windows environment.')
            return []
