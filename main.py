"""
OutlookShareManager
Main application entry point for Windows Desktop application.
Handles DPI scaling, RTL layout direction, and QApplication event loop.
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.logging_utils import setup_logging, get_logger

logger = setup_logging()

def main():
    parser = argparse.ArgumentParser(description='OutlookShareManager Desktop Application')
    parser.add_argument('--test-mode', action='store_true', help='Smoke test mode: initializes and exits immediately with code 0')
    parser.add_argument('--version', action='store_true', help='Show application version')
    parser.add_argument('--diagnostics', action='store_true', help='Run complete Phase 4 system diagnostics and exit')
    args = parser.parse_args()

    if args.version:
        print('OutlookShareManager v1.0.0 (Phase 4 Final Hardening)')
        return 0

    if args.diagnostics:
        from utils.windows_utils import detect_domain_info, get_available_drive_letters
        from services.outlook_service import OutlookService
        from services.archive_service import ArchiveService

        print('=== OutlookShareManager v1.0.0 Phase 4 Diagnostics ===')
        dom = detect_domain_info()
        print(f'[*] Domain: {dom.get("domain")}')
        print(f'[*] Domain Controller: {dom.get("domain_controller")}')
        print(f'[*] User: {dom.get("current_user")}')
        print(f'[*] Is Domain Joined: {dom.get("is_domain_joined")}')

        out = OutlookService().detect_outlook()
        print(f'[*] Outlook Available: {out.get("available")} ({out.get("message_fa")})')

        free_drives = get_available_drive_letters()
        print(f'[*] Available Network Drive Letters: {len(free_drives)} ({", ".join(free_drives[:5])}...)')

        arch = ArchiveService()
        space_ok, space_msg = arch.check_disk_space(str(Path.home()), min_mb=200)
        print(f'[*] Disk Storage Space: {"PASS" if space_ok else "WARN"} - {space_msg}')
        print('=== Diagnostics Completed Successfully ===')
        return 0

    logger.info('Starting OutlookShareManager application...')

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from ui.main_window import MainWindow

        # Support High DPI displays
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName('OutlookShareManager')
        app.setOrganizationName('OutlookShareManager')
        app.setLayoutDirection(Qt.RightToLeft)

        window = MainWindow()

        if args.test_mode:
            logger.info('Smoke test mode active: verifying window initialization...')
            window.show()
            window.close()
            logger.info('Smoke test passed successfully.')
            return 0

        window.show()
        return app.exec()

    except Exception as e:
        logger.critical(f'Unhandled exception during startup: {e}', exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
