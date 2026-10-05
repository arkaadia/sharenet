"""
Main Window for OutlookShareManager desktop application.
Provides professional Persian RTL navigation, header status, and page stacking.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QStatusBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont

from services.settings_service import SettingsService
from services.outlook_service import OutlookService
from services.ad_service import ActiveDirectoryService
from services.smb_service import SMBService
from services.drive_mapping_service import DriveMappingService

from ui.outlook_page import OutlookPage
from ui.share_page import SharePage
from ui.settings_page import SettingsPage

APP_STYLE = """
QMainWindow {
    background-color: #f8fafc;
    font-family: 'Segoe UI', 'Tahoma', 'Vazirmatn', sans-serif;
}
#sidebar {
    background-color: #0f172a;
    border-left: 1px solid #1e293b;
    min-width: 220px;
    max-width: 240px;
}
#appTitle {
    color: #f8fafc;
    font-size: 16px;
    font-weight: bold;
    padding: 16px 12px 6px 12px;
}
#appSubtitle {
    color: #94a3b8;
    font-size: 11px;
    padding: 0px 12px 16px 12px;
    border-bottom: 1px solid #334155;
}
QPushButton.navButton {
    background-color: transparent;
    color: #cbd5e1;
    font-size: 14px;
    text-align: right;
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    margin: 4px 8px;
}
QPushButton.navButton:hover {
    background-color: #1e293b;
    color: #ffffff;
}
QPushButton.navButton:checked {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: bold;
}
#pageTitle {
    font-size: 18px;
    font-weight: bold;
    color: #0f172a;
}
#pageSubtitle {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 8px;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 8px;
    color: #0f172a;
}
QLineEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    color: #0f172a;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #0284c7;
}
QPushButton#primaryButton {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#primaryButton:hover {
    background-color: #0369a1;
}
#securityNotice {
    background-color: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 12px;
}
#safetyNotice {
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    padding: 12px;
}
QTableWidget, QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    font-size: 12px;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: bold;
    padding: 8px;
    border: 1px solid #e2e8f0;
}
"""

class MainWindow(QMainWindow):
    """Main application window with Persian RTL navigation."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle('مدیریت آرشیو اوت‌لوک و پوشه‌های اشتراکی شبکه (OutlookShareManager)')
        self.resize(1100, 720)
        self.setMinimumSize(950, 600)

        # Enforce RTL
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(APP_STYLE)

        # Initialize Services
        self.settings_service = SettingsService()
        self.outlook_service = OutlookService()
        self.ad_service = ActiveDirectoryService()
        self.smb_service = SMBService()
        self.drive_service = DriveMappingService()

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Right (RTL Sidebar)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(6)

        # App Brand Header
        app_title = QLabel('OutlookShareManager')
        app_title.setObjectName('appTitle')
        app_sub = QLabel('نسخه ۱.۰.۰ | آرشیو و شبکه')
        app_sub.setObjectName('appSubtitle')
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(app_sub)

        # Navigation Buttons
        self.nav_buttons = []

        self.btn_outlook = QPushButton('📧 آرشیو اوت‌لوک')
        self.btn_outlook.setProperty('class', 'navButton')
        self.btn_outlook.setCheckable(True)
        self.btn_outlook.setChecked(True)
        self.btn_outlook.clicked.connect(lambda: self.switch_page(0))
        sidebar_layout.addWidget(self.btn_outlook)
        self.nav_buttons.append(self.btn_outlook)

        self.btn_share = QPushButton('📁 پوشه‌های اشتراکی')
        self.btn_share.setProperty('class', 'navButton')
        self.btn_share.setCheckable(True)
        self.btn_share.clicked.connect(lambda: self.switch_page(1))
        sidebar_layout.addWidget(self.btn_share)
        self.nav_buttons.append(self.btn_share)

        self.btn_settings = QPushButton('⚙ تنظیمات')
        self.btn_settings.setProperty('class', 'navButton')
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(lambda: self.switch_page(2))
        sidebar_layout.addWidget(self.btn_settings)
        self.nav_buttons.append(self.btn_settings)

        sidebar_layout.addStretch()

        # System info in sidebar
        domain_info = self.ad_service.get_domain_info()
        sys_info = QLabel(f"دامین: {domain_info.get('domain', 'Standalone')}\nکاربر: {domain_info.get('current_user', 'User')}")
        sys_info.setStyleSheet('color: #64748b; font-size: 11px; padding: 12px;')
        sidebar_layout.addWidget(sys_info)

        main_layout.addWidget(sidebar)

        # Stacked Pages
        self.stack = QStackedWidget()
        
        self.outlook_page = OutlookPage(self.outlook_service, self.settings_service)
        self.share_page = SharePage(self.ad_service, self.smb_service, self.drive_service, self.settings_service)
        self.settings_page = SettingsPage(self.settings_service)

        self.stack.addWidget(self.outlook_page)
        self.stack.addWidget(self.share_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('برنامه با موفقیت بارگذاری شد | آماده استفاده')

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        page_names = ['آرشیو اوت‌لوک', 'پوشه‌های اشتراکی', 'تنظیمات']
        self.status_bar.showMessage(f'صفحه فعلی: {page_names[index]}')
