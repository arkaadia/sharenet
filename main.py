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
    args = parser.parse_args()

    if args.version:
        print('OutlookShareManager v1.0.0')
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
