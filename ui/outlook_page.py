"""
Outlook Archive Page for OutlookShareManager.
Foundation layout for selecting mailboxes, Persian dates, and initiating safe PST export.
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QGroupBox, QFileDialog, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal
from services.outlook_service import OutlookService
from services.settings_service import SettingsService
from utils.persian_date import get_current_jalali_date, validate_jalali_date, format_archive_filename

class OutlookPage(QWidget):
    """Persian RTL Outlook Archive Management Page."""
    def __init__(self, outlook_service: OutlookService, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.outlook_service = outlook_service
        self.settings_service = settings_service
        self._init_ui()
        self.check_outlook_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_label = QLabel('📧 آرشیو ایمیل‌های مایکروسافت اوت‌لوک (Outlook Archive)')
        title_label.setObjectName('pageTitle')
        subtitle_label = QLabel('استخراج و بایگانی امن ایمیل‌ها در قالب فایل PST بر اساس فیلتر تاریخ شمسی دریافت (ReceivedTime)')
        subtitle_label.setObjectName('pageSubtitle')
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Outlook Detection Status Banner
        self.status_banner = QFrame()
        self.status_banner.setObjectName('statusBanner')
        banner_layout = QHBoxLayout(self.status_banner)
        self.status_icon = QLabel('🔄')
        self.status_text = QLabel('در حال بررسی وضعیت اتصال به Microsoft Outlook...')
        self.refresh_btn = QPushButton('بررسی مجدد اتصال')
        self.refresh_btn.clicked.connect(self.check_outlook_status)
        banner_layout.addWidget(self.status_icon)
        banner_layout.addWidget(self.status_text, 1)
        banner_layout.addWidget(self.refresh_btn)
        layout.addWidget(self.status_banner)

        # Splitter: Left = Mailbox Folders, Right = Archive Settings & Filters
        splitter = QSplitter(Qt.Horizontal)

        # Left / Main Pane: Folder Selection Tree
        folders_group = QGroupBox('انتخاب پوشه‌های اوت‌لوک جهت آرشیو')
        folders_layout = QVBoxLayout(folders_group)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(['نام پوشه اوت‌لوک', 'تعداد پیام'])
        self.folder_tree.setColumnWidth(0, 240)
        folders_layout.addWidget(self.folder_tree)
        splitter.addWidget(folders_group)

        # Right Pane: Date Filters & Archive Configuration
        config_group = QGroupBox('بازه زمانی شمسی و تنظیمات فایل PST')
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(12)

        # Persian Dates
        date_subgroup = QGroupBox('فیلتر تاریخ شمسی دریافت (ReceivedTime)')
        date_layout = QVBoxLayout(date_subgroup)
        date_layout.setSpacing(8)

        today_fa = get_current_jalali_date()
        date_h_layout = QHBoxLayout()
        date_h_layout.addWidget(QLabel('از تاریخ:'))
        self.from_date_input = QLineEdit(today_fa)
        self.from_date_input.setPlaceholderText('1405/07/01')
        date_h_layout.addWidget(self.from_date_input)

        date_h_layout.addWidget(QLabel('تا تاریخ:'))
        self.to_date_input = QLineEdit(today_fa)
        self.to_date_input.setPlaceholderText('1405/07/13')
        date_h_layout.addWidget(self.to_date_input)
        date_layout.addLayout(date_h_layout)

        date_note = QLabel('* توجه: پیام‌ها بر اساس زمان دقیق دریافت (شامل تا پایان روز انتخابی) فیلتر می‌شوند.')
        date_note.setStyleSheet('font-size: 11px; color: #64748b;')
        date_layout.addWidget(date_note)
        config_layout.addWidget(date_subgroup)

        # PST Output Settings
        pst_subgroup = QGroupBox('مشخصات فایل خروجی PST')
        pst_layout = QVBoxLayout(pst_subgroup)
        pst_layout.setSpacing(8)

        pst_layout.addWidget(QLabel('نام فایل آرشیو:'))
        default_filename = format_archive_filename(today_fa, today_fa)
        self.pst_name_input = QLineEdit(default_filename)
        pst_layout.addWidget(self.pst_name_input)

        pst_layout.addWidget(QLabel('مسیر ذخیره‌سازی:'))
        dest_h_layout = QHBoxLayout()
        self.pst_dest_input = QLineEdit(self.settings_service.default_archive_dir)
        self.browse_dest_btn = QPushButton('انتخاب مسیر...')
        self.browse_dest_btn.clicked.connect(self._on_browse_dest)
        dest_h_layout.addWidget(self.pst_dest_input)
        dest_h_layout.addWidget(self.browse_dest_btn)
        pst_layout.addLayout(dest_h_layout)
        config_layout.addWidget(pst_subgroup)

        # Mandatory Safety Notice: COPY ONLY
        safety_box = QFrame()
        safety_box.setObjectName('safetyNotice')
        s_layout = QVBoxLayout(safety_box)
        s_title = QLabel('🛡 امنیت آرشیو: کپی کامل بدون حذف (Copy Only)')
        s_title.setStyleSheet('font-weight: bold; color: #16a34a;')
        s_desc = QLabel('این برنامه صرفاً پیام‌ها را در فایل PST کپی می‌کند و تحت هیچ شرایطی ایمیل‌های اصلی شما را حذف یا جابجا نمی‌نماید.')
        s_desc.setWordWrap(True)
        s_layout.addWidget(s_title)
        s_layout.addWidget(s_desc)
        config_layout.addWidget(safety_box)

        # Action Button
        self.start_archive_btn = QPushButton('🚀 شروع عملیات آرشیو')
        self.start_archive_btn.setObjectName('primaryButton')
        self.start_archive_btn.setMinimumHeight(44)
        self.start_archive_btn.clicked.connect(self._on_start_archive)
        config_layout.addWidget(self.start_archive_btn)

        config_layout.addStretch()
        splitter.addWidget(config_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)

        # Progress Section
        self.progress_group = QGroupBox('پیشرفت عملیات آرشیو')
        prog_layout = QVBoxLayout(self.progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_status_label = QLabel('آماده برای شروع عملیات.')
        prog_layout.addWidget(self.progress_bar)
        prog_layout.addWidget(self.progress_status_label)
        layout.addWidget(self.progress_group)

    def check_outlook_status(self):
        """Checks Outlook COM availability and updates the UI."""
        info = self.outlook_service.detect_outlook()
        if info['available']:
            self.status_icon.setText('✅')
            self.status_text.setText(info['message_fa'])
            self.status_banner.setStyleSheet('background-color: #ecfdf5; border: 1px solid #10b981; border-radius: 6px; padding: 10px;')
            self.load_outlook_folders()
        else:
            self.status_icon.setText('⚠️')
            self.status_text.setText(info['message_fa'])
            self.status_banner.setStyleSheet('background-color: #fff1f2; border: 1px solid #f43f5e; border-radius: 6px; padding: 10px;')

    def load_outlook_folders(self):
        """Populates real Outlook folders into tree."""
        self.folder_tree.clear()
        stores = self.outlook_service.get_mailboxes_and_folders()
        for store in stores:
            store_item = QTreeWidgetItem(self.folder_tree, [store['name'], ''])
            store_item.setFlags(store_item.flags() | Qt.ItemIsUserCheckable)
            store_item.setCheckState(0, Qt.Unchecked)
            self._add_folder_nodes(store_item, store.get('folders', []))
            store_item.setExpanded(True)

    def _add_folder_nodes(self, parent_item: QTreeWidgetItem, folders: list):
        for f in folders:
            item = QTreeWidgetItem(parent_item, [f['name'], str(f['count'])])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, f['entry_id'])
            if f.get('children'):
                self._add_folder_nodes(item, f['children'])

    def _on_browse_dest(self):
        curr = self.pst_dest_input.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, 'انتخاب مسیر ذخیره فایل آرشیو PST', curr)
        if selected:
            self.pst_dest_input.setText(selected)

    def _on_start_archive(self):
        # Validate Persian Dates
        from_date = self.from_date_input.text().strip()
        to_date = self.to_date_input.text().strip()

        ok_from, err_from = validate_jalali_date(from_date)
        if not ok_from:
            QMessageBox.warning(self, 'تاریخ نامعتبر', f'تاریخ شروع نامعتبر است: {err_from}')
            return

        ok_to, err_to = validate_jalali_date(to_date)
        if not ok_to:
            QMessageBox.warning(self, 'تاریخ نامعتبر', f'تاریخ پایان نامعتبر است: {err_to}')
            return

        pst_dir = self.pst_dest_input.text().strip()
        pst_name = self.pst_name_input.text().strip()

        if not pst_dir or not os.path.exists(pst_dir):
            QMessageBox.warning(self, 'مسیر نامعتبر', 'مسیر ذخیره‌سازی فایل آرشیو معتبر نیست.')
            return

        if not pst_name.lower().endswith('.pst'):
            pst_name += '.pst'

        # Confirmation dialog
        confirm_lines = [
            'آیا از شروع عملیات آرشیو اطمینان دارید؟',
            '',
            f'• از تاریخ شمسی: {from_date}',
            f'• تا تاریخ شمسی: {to_date}',
            f'• نام فایل آرشیو: {pst_name}',
            f'• مسیر ذخیره: {pst_dir}',
            '',
            'توجه: هیچ ایمیلی از حساب اوت‌لوک شما حذف نخواهد شد (حالت ایمن کپی).'
        ]
        confirm_text = chr(10).join(confirm_lines)
        reply = QMessageBox.question(
            self, 'تأیید شروع آرشیو', confirm_text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.progress_status_label.setText('در حال آماده‌سازی فرآیند آرشیو...')
