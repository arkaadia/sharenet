"""
Share Folders and Active Directory Page (Phase 3).
Provides domain detection display, latency testing, Active Directory user profile,
SMB share discovery with ACL permission evaluation, storage meters,
persistent drive mapping (WNetAddConnection2), and corporate preset mappings.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QComboBox, QMessageBox, QFrame, QSplitter,
    QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt
from services.ad_service import ActiveDirectoryService
from services.smb_service import SMBService
from services.drive_mapping_service import DriveMappingService
from services.settings_service import SettingsService
from utils.windows_utils import get_available_drive_letters

class SharePage(QWidget):
    """Persian RTL Active Directory and Share Folder Management Page (Phase 3)."""
    def __init__(self, ad_service: ActiveDirectoryService, smb_service: SMBService,
                 drive_service: DriveMappingService, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.ad_service = ad_service
        self.smb_service = smb_service
        self.drive_service = drive_service
        self.settings_service = settings_service
        self._current_shares = []

        self._init_ui()
        self.load_domain_info()
        self.refresh_existing_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title_label = QLabel('📁 مدیریت پیشرفته پوشه‌های اشتراکی شبکه و اکتیودایرکتوری (فاز ۳)')
        title_label.setObjectName('pageTitle')
        subtitle_label = QLabel('احراز هویت AD، بررسی دسترسی‌ها (ACL)، کشف پویای SMB و اتصال پایدار درایوهای شبکه (WNetAddConnection2)')
        subtitle_label.setObjectName('pageSubtitle')
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Domain Detection Banner (Read-only) + DC Ping
        domain_group = QGroupBox('اطلاعات محیط دامین ویندوز و وضعیت ارتباط (شناسایی خودکار - فقط خواندنی)')
        domain_layout = QHBoxLayout(domain_group)
        domain_layout.setSpacing(16)

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

        d_col4 = QVBoxLayout()
        d_col4.addWidget(QLabel('وضعیت اتصال DC:'))
        self.dc_status_btn = QPushButton('⚡ بررسی پینگ و اتصال DC')
        self.dc_status_btn.clicked.connect(self._on_check_dc_ping)
        d_col4.addWidget(self.dc_status_btn)
        domain_layout.addLayout(d_col4)

        layout.addWidget(domain_group)

        # Authentication Group
        auth_group = QGroupBox('احراز هویت Active Directory و استعلام گروه‌های امنیتی')
        auth_layout = QHBoxLayout(auth_group)
        auth_layout.setSpacing(12)

        auth_layout.addWidget(QLabel('نام کاربری دامین:'))
        self.auth_user_input = QLineEdit()
        self.auth_user_input.setPlaceholderText('مثال: john.doe')
        auth_layout.addWidget(self.auth_user_input, 1)

        auth_layout.addWidget(QLabel('کلمه عبور:'))
        self.auth_pass_input = QLineEdit()
        self.auth_pass_input.setEchoMode(QLineEdit.Password)
        self.auth_pass_input.setPlaceholderText('••••••••')
        auth_layout.addWidget(self.auth_pass_input, 1)

        self.auth_btn = QPushButton('🔑 احراز هویت و استعلام نقش‌ها')
        self.auth_btn.setObjectName('primaryButton')
        self.auth_btn.clicked.connect(self._on_authenticate)
        auth_layout.addWidget(self.auth_btn)

        layout.addWidget(auth_group)

        # Splitter: Upper = Discovered Shares, Lower = Existing Mapped Drives
        splitter = QSplitter(Qt.Vertical)

        # Discovered Shares Section
        shares_group = QGroupBox('کشف پوشه‌های اشتراکی SMB و بررسی سطح دسترسی (ACL & Storage)')
        shares_layout = QVBoxLayout(shares_group)

        # Server input and search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('سرور فایل:'))
        self.server_input = QLineEdit(self.settings_service.default_file_server)
        self.server_input.setPlaceholderText('\\\\FS01.company.local')
        search_layout.addWidget(self.server_input, 2)

        self.ping_server_btn = QPushButton('📡 پینگ پورت SMB (445)')
        self.ping_server_btn.clicked.connect(self._on_ping_smb_server)
        search_layout.addWidget(self.ping_server_btn)

        self.discover_btn = QPushButton('🔍 جستجو و کشف پوشه‌ها')
        self.discover_btn.clicked.connect(self._on_discover_shares)
        search_layout.addWidget(self.discover_btn)

        self.show_admin_check = QCheckBox('نمایش پوشه‌های سیستمی ($)')
        self.show_admin_check.stateChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.show_admin_check)

        shares_layout.addLayout(search_layout)

        # Shares Filter Box
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel('فیلتر سریع:'))
        self.share_filter_input = QLineEdit()
        self.share_filter_input.setPlaceholderText('جستجو در نام، مسیر یا توضیحات...')
        self.share_filter_input.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.share_filter_input, 1)
        shares_layout.addLayout(filter_layout)

        # Shares Table (Columns: Share Name, UNC Path, Description, Permissions, Storage)
        self.shares_table = QTableWidget(0, 5)
        self.shares_table.setHorizontalHeaderLabels([
            'نام پوشه (Share)', 'مسیر کامل UNC', 'توضیحات و کاربرد', 'سطح دسترسی (ACL)', 'فضای دیسک (آزاد/کل)'
        ])
        self.shares_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.shares_table.setSelectionBehavior(QTableWidget.SelectRows)
        shares_layout.addWidget(self.shares_table)

        # Drive Map Controls
        map_h_layout = QHBoxLayout()
        map_h_layout.addWidget(QLabel('اتصال پوشه انتخاب‌شده به درایو:'))
        self.drive_select_combo = QComboBox()
        self._populate_free_drives()
        map_h_layout.addWidget(self.drive_select_combo)

        self.persistent_check = QCheckBox('اتصال پایدار (Reconnect at sign-in)')
        self.persistent_check.setChecked(True)
        map_h_layout.addWidget(self.persistent_check)

        self.map_drive_btn = QPushButton('🔗 اتصال درایو شبکه (Map Drive)')
        self.map_drive_btn.setObjectName('primaryButton')
        self.map_drive_btn.clicked.connect(self._on_map_drive)
        map_h_layout.addWidget(self.map_drive_btn)

        # Presets
        map_h_layout.addSpacing(16)
        map_h_layout.addWidget(QLabel('پیش‌تنظیم سازمانی:'))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem('انتخاب پیش‌تنظیم...', None)
        presets = self.drive_service.get_recommended_presets()
        for p in presets:
            self.preset_combo.addItem(f"{p['drive_letter']} ← {p['label_fa']}", p)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        map_h_layout.addWidget(self.preset_combo)

        map_h_layout.addStretch()
        shares_layout.addLayout(map_h_layout)

        splitter.addWidget(shares_group)

        # Existing Mapped Drives Section
        drives_group = QGroupBox('درایوهای شبکه فعال و متصل ویندوز (Current Mapped Network Drives)')
        drives_layout = QVBoxLayout(drives_group)

        self.drives_table = QTableWidget(0, 4)
        self.drives_table.setHorizontalHeaderLabels(['حرف درایو', 'مسیر شبکه (UNC)', 'نوع اتصال', 'عملیات'])
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
        letters = self.drive_service.get_available_letters()
        if not letters:
            letters = ['Z:', 'Y:', 'X:', 'W:', 'V:', 'U:']
        for l in letters:
            self.drive_select_combo.addItem(l)

    def _on_check_dc_ping(self):
        dc = self.dc_field.text().strip() or self.domain_field.text().strip()
        res = self.ad_service.test_dc_connectivity(dc)
        if res.get('online'):
            QMessageBox.information(self, 'اتصال دامین کنترلر', res.get('message_fa', 'ارتباط با موفقیت برقرار شد.'))
        else:
            QMessageBox.warning(self, 'خطای ارتباط', res.get('message_fa', 'ارتباط با دامین کنترلر برقرار نشد.'))

    def _on_ping_smb_server(self):
        srv = self.server_input.text().strip()
        if not srv:
            QMessageBox.warning(self, 'نام سرور', 'لطفاً نام یا آدرس سرور فایل را وارد کنید.')
            return
        res = self.smb_service.ping_smb_server(srv)
        if res.get('online'):
            QMessageBox.information(self, 'پینگ پورت SMB', res.get('message_fa', 'پورت 445 در دسترس است.'))
        else:
            QMessageBox.warning(self, 'خطا در ارتباط SMB', res.get('message_fa', 'پورت SMB مسدود است.'))

    def _on_authenticate(self):
        user = self.auth_user_input.text().strip()
        pwd = self.auth_pass_input.text()
        if not user or not pwd:
            QMessageBox.warning(self, 'خطا', 'لطفاً نام کاربری و کلمه عبور را وارد کنید.')
            return

        result = self.ad_service.authenticate_user(user, pwd)
        if result['success']:
            details = result.get('user_details', {})
            groups_str = ', '.join(details.get('groups', []))
            dept = details.get('department', 'سازمانی')
            msg = (f"{result['message_fa']}\n\n"
                   f"👤 نام کامل: {details.get('display_name')}\n"
                   f"🏢 دپارتمان: {dept}\n"
                   f"🛡 گروه‌های امنیتی: {groups_str}")
            QMessageBox.information(self, 'موفقیت در احراز هویت', msg)
        else:
            QMessageBox.warning(self, 'خطای احراز هویت', result['message_fa'])

    def _on_discover_shares(self):
        server = self.server_input.text().strip()
        if not server:
            QMessageBox.warning(self, 'نام سرور', 'لطفاً نام یا آدرس سرور فایل را وارد کنید.')
            return

        include_admin = self.show_admin_check.isChecked()
        self._current_shares = self.smb_service.enumerate_shares(server, include_admin=include_admin, auto_check_permissions=True)
        self._render_shares_table()

    def _on_filter_changed(self):
        self._render_shares_table()

    def _render_shares_table(self):
        q = self.share_filter_input.text().strip()
        include_admin = self.show_admin_check.isChecked()
        filtered = self.smb_service.filter_shares(self._current_shares, query=q, show_admin=include_admin)

        self.shares_table.setRowCount(0)
        for row, s in enumerate(filtered):
            self.shares_table.insertRow(row)
            self.shares_table.setItem(row, 0, QTableWidgetItem(s['name']))
            self.shares_table.setItem(row, 1, QTableWidgetItem(s['unc_path']))
            self.shares_table.setItem(row, 2, QTableWidgetItem(s.get('remark', '')))

            # Permissions label
            perm = s.get('permissions') or {}
            lvl = perm.get('access_level', 'read_write')
            if lvl == 'read_write':
                perm_text = '🟢 خواندن و نوشتن'
            elif lvl == 'read_only':
                perm_text = '🟡 فقط خواندنی'
            elif lvl == 'denied':
                perm_text = '🔴 عدم دسترسی'
            else:
                perm_text = '⚪ آفلاین'
            self.shares_table.setItem(row, 3, QTableWidgetItem(perm_text))

            # Storage label
            st = s.get('storage') or {}
            st_text = f"{st.get('free_gb', 0)} GB آزاد از {st.get('total_gb', 0)} GB"
            self.shares_table.setItem(row, 4, QTableWidgetItem(st_text))

    def _on_preset_selected(self, idx):
        preset = self.preset_combo.currentData()
        if not preset:
            return
        # Find drive letter in combo
        target_letter = preset['drive_letter']
        idx = self.drive_select_combo.findText(target_letter)
        if idx >= 0:
            self.drive_select_combo.setCurrentIndex(idx)

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
        persistent = self.persistent_check.isChecked()

        success, msg = self.drive_service.map_drive(
            drive_letter, unc_path,
            user if user else None,
            pwd if pwd else None,
            persistent=persistent
        )

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

            persist_str = 'دائمی (Persistent)' if d.get('is_persistent', True) else 'موقتی (Session)'
            self.drives_table.setItem(row, 2, QTableWidgetItem(persist_str))

            # Action buttons cell (Disconnect & Explore)
            btn_cell = QWidget()
            btn_layout = QHBoxLayout(btn_cell)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            disconnect_btn = QPushButton('قطع درایو')
            letter = d['drive_letter']
            disconnect_btn.clicked.connect(lambda checked=False, l=letter: self._on_disconnect_drive(l))
            btn_layout.addWidget(disconnect_btn)

            self.drives_table.setCellWidget(row, 3, btn_cell)

    def _on_disconnect_drive(self, drive_letter: str):
        reply = QMessageBox.question(
            self, 'قطع اتصال درایو', f'آیا از قطع اتصال درایو شبکه {drive_letter} مطمئن هستید؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = self.drive_service.disconnect_drive(drive_letter, force=True, update_profile=True)
            if ok:
                QMessageBox.information(self, 'موفقیت', msg)
                self.refresh_existing_drives()
                self._populate_free_drives()
            else:
                QMessageBox.critical(self, 'خطا', msg)
