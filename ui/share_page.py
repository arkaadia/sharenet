"""
Share Folders and Active Directory Page.
Provides domain detection display, authentication, share discovery, and drive mapping.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QComboBox, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt
from services.ad_service import ActiveDirectoryService
from services.smb_service import SMBService
from services.drive_mapping_service import DriveMappingService
from services.settings_service import SettingsService
from utils.windows_utils import get_available_drive_letters

class SharePage(QWidget):
    """Persian RTL Active Directory and Share Folder Management Page."""
    def __init__(self, ad_service: ActiveDirectoryService, smb_service: SMBService,
                 drive_service: DriveMappingService, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.ad_service = ad_service
        self.smb_service = smb_service
        self.drive_service = drive_service
        self.settings_service = settings_service
        self._init_ui()
        self.load_domain_info()
        self.refresh_existing_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_label = QLabel('📁 مدیریت پوشه‌های اشتراکی شبکه و اکتیودایرکتوری (Share Folders & AD)')
        title_label.setObjectName('pageTitle')
        subtitle_label = QLabel('شناسایی دامین ویندوز، کشف پوشه‌های اشتراکی SMB و اتصال درایوهای شبکه (Drive Mapping)')
        subtitle_label.setObjectName('pageSubtitle')
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Domain Detection Banner (Read-only as required)
        domain_group = QGroupBox('اطلاعات محیط دامین ویندوز (شناسایی خودکار - فقط خواندنی)')
        domain_layout = QHBoxLayout(domain_group)
        domain_layout.setSpacing(20)

        d_col1 = QVBoxLayout()
        d_col1.addWidget(QLabel('نام دامین (Windows Domain):'))
        self.domain_field = QLineEdit()
        self.domain_field.setReadOnly(True)
        self.domain_field.setStyleSheet('background-color: #f1f5f9; font-weight: bold;')
        d_col1.addWidget(self.domain_field)
        domain_layout.addLayout(d_col1)

        d_col2 = QVBoxLayout()
        d_col2.addWidget(QLabel('دامین کنترلر (Domain Controller):'))
        self.dc_field = QLineEdit()
        self.dc_field.setReadOnly(True)
        self.dc_field.setStyleSheet('background-color: #f1f5f9; font-weight: bold;')
        d_col2.addWidget(self.dc_field)
        domain_layout.addLayout(d_col2)

        d_col3 = QVBoxLayout()
        d_col3.addWidget(QLabel('کاربر فعلی سیستم:'))
        self.user_field = QLineEdit()
        self.user_field.setReadOnly(True)
        self.user_field.setStyleSheet('background-color: #f1f5f9; font-weight: bold;')
        d_col3.addWidget(self.user_field)
        domain_layout.addLayout(d_col3)

        layout.addWidget(domain_group)

        # Authentication Group
        auth_group = QGroupBox('احراز هویت اکتیودایرکتوری (Active Directory Credentials)')
        auth_layout = QHBoxLayout(auth_group)
        auth_layout.setSpacing(16)

        auth_layout.addWidget(QLabel('نام کاربری:'))
        self.auth_user_input = QLineEdit()
        self.auth_user_input.setPlaceholderText('مثال: john.doe')
        auth_layout.addWidget(self.auth_user_input)

        auth_layout.addWidget(QLabel('کلمه عبور:'))
        self.auth_pass_input = QLineEdit()
        self.auth_pass_input.setEchoMode(QLineEdit.Password)
        self.auth_pass_input.setPlaceholderText('••••••••')
        auth_layout.addWidget(self.auth_pass_input)

        self.auth_btn = QPushButton('🔑 احراز هویت')
        self.auth_btn.setObjectName('primaryButton')
        self.auth_btn.clicked.connect(self._on_authenticate)
        auth_layout.addWidget(self.auth_btn)

        layout.addWidget(auth_group)

        # Splitter: Upper = Discovered Shares, Lower = Existing Mapped Drives
        splitter = QSplitter(Qt.Vertical)

        # Discovered Shares Section
        shares_group = QGroupBox('پوشه‌های اشتراکی کشف‌شده (Discovered SMB Shares)')
        shares_layout = QVBoxLayout(shares_group)
        
        # Server input and search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('سرور فایل:'))
        self.server_input = QLineEdit(self.settings_service.default_file_server)
        self.server_input.setPlaceholderText('\\FS01.company.local')
        search_layout.addWidget(self.server_input, 1)

        self.discover_btn = QPushButton('🔍 جستجو و کشف پوشه‌ها')
        self.discover_btn.clicked.connect(self._on_discover_shares)
        search_layout.addWidget(self.discover_btn)
        shares_layout.addLayout(search_layout)

        # Shares Table
        self.shares_table = QTableWidget(0, 3)
        self.shares_table.setHorizontalHeaderLabels(['نام پوشه (Share)', 'مسیر کامل UNC', 'توضیحات'])
        self.shares_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.shares_table.setSelectionBehavior(QTableWidget.SelectRows)
        shares_layout.addWidget(self.shares_table)

        # Drive Map Controls
        map_h_layout = QHBoxLayout()
        map_h_layout.addWidget(QLabel('اتصال پوشه انتخاب‌شده به درایو:'))
        self.drive_select_combo = QComboBox()
        self._populate_free_drives()
        map_h_layout.addWidget(self.drive_select_combo)

        self.map_drive_btn = QPushButton('🔗 اتصال درایو شبکه (Map Drive)')
        self.map_drive_btn.setObjectName('primaryButton')
        self.map_drive_btn.clicked.connect(self._on_map_drive)
        map_h_layout.addWidget(self.map_drive_btn)
        map_h_layout.addStretch()
        shares_layout.addLayout(map_h_layout)

        splitter.addWidget(shares_group)

        # Existing Mapped Drives Section
        drives_group = QGroupBox('درایوهای شبکه فعال و متصل فعلی (Current Mapped Network Drives)')
        drives_layout = QVBoxLayout(drives_group)

        self.drives_table = QTableWidget(0, 3)
        self.drives_table.setHorizontalHeaderLabels(['حرف درایو', 'مسیر شبکه (UNC)', 'عملیات'])
        self.drives_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        drives_layout.addWidget(self.drives_table)

        btn_drives_layout = QHBoxLayout()
        self.refresh_drives_btn = QPushButton('🔄 بروزرسانی لیست درایوها')
        self.refresh_drives_btn.clicked.connect(self.refresh_existing_drives)
        btn_drives_layout.addWidget(self.refresh_drives_btn)
        btn_drives_layout.addStretch()
        drives_layout.addLayout(btn_drives_layout)

        splitter.addWidget(drives_group)

        layout.addWidget(splitter, 1)

    def load_domain_info(self):
        """Loads detected domain information without manual input."""
        info = self.ad_service.get_domain_info()
        self.domain_field.setText(info.get('domain', ''))
        self.dc_field.setText(info.get('domain_controller', ''))
        self.user_field.setText(info.get('current_user', ''))
        if not self.auth_user_input.text():
            self.auth_user_input.setText(info.get('current_user', ''))

    def _populate_free_drives(self):
        self.drive_select_combo.clear()
        free_letters = get_available_drive_letters()
        if not free_letters:
            free_letters = ['Z:', 'Y:', 'X:', 'W:', 'V:', 'U:']
        for l in free_letters:
            self.drive_select_combo.addItem(l)

    def _on_authenticate(self):
        user = self.auth_user_input.text().strip()
        pwd = self.auth_pass_input.text()
        if not user or not pwd:
            QMessageBox.warning(self, 'خطا', 'لطفاً نام کاربری و کلمه عبور را وارد کنید.')
            return

        result = self.ad_service.authenticate_user(user, pwd)
        if result['success']:
            QMessageBox.information(self, 'موفقیت', result['message_fa'])
        else:
            QMessageBox.warning(self, 'خطای احراز هویت', result['message_fa'])

    def _on_discover_shares(self):
        server = self.server_input.text().strip()
        if not server:
            QMessageBox.warning(self, 'نام سرور', 'لطفاً نام یا آدرس سرور فایل را وارد کنید.')
            return

        shares = self.smb_service.enumerate_shares(server)
        self.shares_table.setRowCount(0)
        for row, s in enumerate(shares):
            self.shares_table.insertRow(row)
            self.shares_table.setItem(row, 0, QTableWidgetItem(s['name']))
            self.shares_table.setItem(row, 1, QTableWidgetItem(s['unc_path']))
            self.shares_table.setItem(row, 2, QTableWidgetItem(s.get('remark', '')))

        if not shares:
            QMessageBox.information(self, 'نتیجه جستجو', f'پوشه اشتراکی فعالی بر روی سرور {server} یافت نشد یا دسترسی مجاز نیست.')

    def _on_map_drive(self):
        selected_rows = self.shares_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, 'انتخاب پوشه', 'لطفاً یک پوشه اشتراکی را از جدول انتخاب کنید.')
            return

        row = selected_rows[0].row()
        unc_path = self.shares_table.item(row, 1).text()
        drive_letter = self.drive_select_combo.currentText()
        user = self.auth_user_input.text().strip()
        pwd = self.auth_pass_input.text()

        success, msg = self.drive_service.map_drive(drive_letter, unc_path, user if user else None, pwd if pwd else None)
        if success:
            QMessageBox.information(self, 'اتصال درایو', msg)
            self.refresh_existing_drives()
            self._populate_free_drives()
        else:
            QMessageBox.critical(self, 'خطای اتصال درایو', msg)

    def refresh_existing_drives(self):
        """Refreshes the table of connected network drives."""
        drives = self.drive_service.get_existing_network_drives()
        self.drives_table.setRowCount(0)
        for row, d in enumerate(drives):
            self.drives_table.insertRow(row)
            self.drives_table.setItem(row, 0, QTableWidgetItem(d['drive_letter']))
            self.drives_table.setItem(row, 1, QTableWidgetItem(d['unc_path']))
            
            # Disconnect button in cell
            disconnect_btn = QPushButton('قطع درایو (Disconnect)')
            letter = d['drive_letter']
            disconnect_btn.clicked.connect(lambda checked=False, l=letter: self._on_disconnect_drive(l))
            self.drives_table.setCellWidget(row, 2, disconnect_btn)

    def _on_disconnect_drive(self, drive_letter: str):
        reply = QMessageBox.question(
            self, 'قطع اتصال درایو', f'آیا از قطع اتصال درایو شبکه {drive_letter} مطمئن هستید؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = self.drive_service.disconnect_drive(drive_letter)
            if ok:
                QMessageBox.information(self, 'موفقیت', msg)
                self.refresh_existing_drives()
                self._populate_free_drives()
            else:
                QMessageBox.critical(self, 'خطا', msg)
