"""
Outlook COM interface service using pywin32.
Detects Microsoft Outlook, MAPI namespaces, stores, and folder hierarchy.
"""
import sys
from typing import Dict, Any, List, Optional
from utils.logging_utils import get_logger

logger = get_logger('outlook_service')

class OutlookService:
    """Service for interfacing with local Microsoft Outlook installation."""
    def __init__(self):
        self._outlook_app = None
        self._namespace = None
        self._is_available = False
        self._status_message_fa = ''

    def detect_outlook(self) -> Dict[str, Any]:
        """
        Detects if classic Microsoft Outlook is installed and accessible via COM.
        Returns a dict with availability status and Persian description.
        """
        if sys.platform != 'win32':
            self._is_available = False
            self._status_message_fa = 'سیستم‌عامل ویندوز شناسایی نشد. اوت‌لوک تنها در ویندوز پشتیبانی می‌شود.'
            return {
                'available': False,
                'version': None,
                'profile': None,
                'message_fa': self._status_message_fa,
            }

        try:
            import win32com.client
            # Connect or dispatch Outlook Application
            try:
                self._outlook_app = win32com.client.GetActiveObject('Outlook.Application')
            except Exception:
                self._outlook_app = win32com.client.Dispatch('Outlook.Application')

            if self._outlook_app:
                version = getattr(self._outlook_app, 'Version', 'نامشخص')
                self._namespace = self._outlook_app.GetNamespace('MAPI')
                current_profile = getattr(self._namespace, 'CurrentProfileName', 'پیش‌فرض')
                self._is_available = True
                self._status_message_fa = f'اوت‌لوک فعال است (نسخه {version}، پروفایل {current_profile})'
                logger.info(f'Outlook detected successfully: {self._status_message_fa}')
                return {
                    'available': True,
                    'version': version,
                    'profile': current_profile,
                    'message_fa': self._status_message_fa,
                }
        except Exception as e:
            self._is_available = False
            self._status_message_fa = f'برنامه مایکروسافت اوت‌لوک یافت نشد یا در دسترس نیست: {str(e)}'
            logger.error(f'Outlook detection failed: {e}')
            return {
                'available': False,
                'version': None,
                'profile': None,
                'message_fa': self._status_message_fa,
            }

    def get_mailboxes_and_folders(self) -> List[Dict[str, Any]]:
        """
        Reads real Outlook stores and returns mailbox trees with nested folders.
        """
        if not self._is_available or not self._namespace:
            self.detect_outlook()
            if not self._is_available:
                return []

        stores_data = []
        try:
            stores = self._namespace.Stores
            for i in range(1, stores.Count + 1):
                store = stores.Item(i)
                display_name = store.DisplayName
                try:
                    root_folder = store.GetRootFolder()
                    folders = self._parse_folder_recursive(root_folder)
                    stores_data.append({
                        'name': display_name,
                        'entry_id': store.StoreID,
                        'is_data_file': getattr(store, 'IsDataFileStore', False),
                        'folders': folders
                    })
                except Exception as ex:
                    logger.warning(f'Error reading root folder for store {display_name}: {ex}')
        except Exception as e:
            logger.error(f'Error fetching Outlook stores: {e}')

        return stores_data

    def _parse_folder_recursive(self, folder) -> List[Dict[str, Any]]:
        """Recursively traverses Outlook folder hierarchy."""
        subfolders = []
        try:
            folders = folder.Folders
            for i in range(1, folders.Count + 1):
                sub = folders.Item(i)
                # Count items in folder
                item_count = getattr(sub, 'Items', None)
                count = item_count.Count if item_count else 0
                subfolders.append({
                    'name': sub.Name,
                    'entry_id': sub.EntryID,
                    'count': count,
                    'children': self._parse_folder_recursive(sub)
                })
        except Exception as e:
            logger.warning(f'Error traversing folder: {e}')
        return subfolders
