"""
Application settings management.
Persists configuration in %APPDATA%/OutlookShareManager/settings.json.
Security rule: NEVER store passwords or user credentials in settings.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from utils.windows_utils import get_app_dir
from utils.logging_utils import get_logger

logger = get_logger('settings_service')

DEFAULT_SETTINGS: Dict[str, Any] = {
    'default_archive_dir': '',
    'default_file_server': '',
    'default_drive_letter': 'Z:',
    'theme': 'light',
    'language': 'fa',
}

class SettingsService:
    """Manages user preferences and defaults without storing credentials."""
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or get_app_dir()
        self.settings_file = self.config_dir / 'settings.json'
        self._settings = self._load()

    def _load(self) -> Dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        # Default archive directory if empty
        user_profile = os.environ.get('USERPROFILE') or str(Path.home())
        default_archive = os.path.join(user_profile, 'Documents', 'Outlook Archives')
        settings['default_archive_dir'] = default_archive

        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Scrub any accidental password key if present
                    data.pop('password', None)
                    data.pop('credentials', None)
                    settings.update(data)
            except Exception as e:
                logger.error(f'Failed to load settings file: {e}')
        return settings

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # Enforce security: reject any password storage attempt
        if any(s in key.lower() for s in ['pass', 'pwd', 'secret', 'token', 'cred']):
            logger.warning(f'Attempted to store prohibited key {key}. Request rejected.')
            return
        self._settings[key] = value

    def save(self) -> bool:
        """Saves current settings to disk safely."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # Ensure no credentials before saving
            clean_settings = {
                k: v for k, v in self._settings.items()
                if not any(s in k.lower() for s in ['pass', 'pwd', 'secret', 'token', 'cred'])
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(clean_settings, f, ensure_ascii=False, indent=2)
            logger.info('Settings saved successfully.')
            return True
        except Exception as e:
            logger.error(f'Failed to save settings: {e}')
            return False

    @property
    def default_archive_dir(self) -> str:
        return self.get('default_archive_dir', '')

    @default_archive_dir.setter
    def default_archive_dir(self, val: str) -> None:
        self.set('default_archive_dir', val)

    @property
    def default_file_server(self) -> str:
        return self.get('default_file_server', '')

    @default_file_server.setter
    def default_file_server(self, val: str) -> None:
        self.set('default_file_server', val)

    @property
    def default_drive_letter(self) -> str:
        return self.get('default_drive_letter', 'Z:')

    @default_drive_letter.setter
    def default_drive_letter(self, val: str) -> None:
        self.set('default_drive_letter', val)
