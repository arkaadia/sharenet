"""
Settings page for OutlookShareManager.
Allows configuration of default archive directory, file server, and drive letter.
Strictly adheres to privacy: NO passwords stored.
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QGroupBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from services.settings_service import SettingsService
from utils.windows_utils import get_available_drive_letters

class SettingsPage(QWidget):
    """Persian RTL Settings Configuration Page."""
    settings_saved = Signal()

    def __init__(self, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings_service
        self._init_ui()
        self.load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header Title
        title_label = QLabel('⚙ تنظیمات و پیکربندی سامانه')
        title_label.setObjectName('pageTitle')
        subtitle_label = QLabel('پیکربندی مسیرهای پیش‌فرض آرشیو، سرور فایل شبکه و ترجیحات برنامه')
        subtitle_label.setObjectName('pageSubtitle')
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Group 1: Outlook Archive Defaults
        archive_group = QGroupBox('تنظیمات پیش‌فرض آرشیو اوت‌لوک (Outlook Archive)')
        archive_layout = QVBoxLayout(archive_group)
        archive_layout.setSpacing(12)
        archive_layout.setContentsMargins(16, 20, 16, 16)

        archive_dir_label = QLabel('مسیر پیش‌فرض ذخیره‌سازی فایل‌های آرشیو (PST):')
        archive_layout.addWidget(archive_dir_label)

        dir_h_layout = QHBoxLayout()
        self.archive_dir_input = QLineEdit()
        self.archive_dir_input.setPlaceholderText('مثال: C:\Archives یا پوشه اسناد...')
        self.browse_btn = QPushButton('مرور مسیر...')
        self.browse_btn.clicked.connect(self._on_browse_archive_dir)
        dir_h_layout.addWidget(self.archive_dir_input)
        dir_h_layout.addWidget(self.browse_btn)
        archive_layout.addLayout(dir_h_layout)

        layout.addWidget(archive_group)

        # Group 2: Share & Network Defaults
        network_group = QGroupBox('تنظیمات پیش‌فرض شبکه و پوشه‌های اشتراکی (Network & Shares)')
        network_layout = QVBoxLayout(network_group)
        network_layout.setSpacing(12)
        network_layout.setContentsMargins(16, 20, 16, 16)

        server_label = QLabel('آدرس یا نام سرور فایل پیش‌فرض (SMB File Server):')
        network_layout.addWidget(server_label)
        self.file_server_input = QLineEdit()
        self.file_server_input.setPlaceholderText('مثال: \\FS01.company.local یا \\192.168.1.10')
        network_layout.addWidget(self.file_server_input)

        drive_label = QLabel('حرف درایو پیش‌فرض برای اتصال به شبکه (Default Drive Letter):')
        network_layout.addWidget(drive_label)
        self.drive_combo = QComboBox()
        # Populate available drive letters Z: down to D:
        for letter in ['Z:', 'Y:', 'X:', 'W:', 'V:', 'U:', 'T:', 'S:', 'R:', 'Q:', 'P:', 'O:', 'N:', 'M:', 'L:', 'K:', 'J:', 'I:', 'H:', 'G:', 'F:', 'E:', 'D:']:
            self.drive_combo.addItem(letter)
        network_layout.addWidget(self.drive_combo)

        layout.addWidget(network_group)

        # Security & Privacy notice box
        security_box = QFrame()
        security_box.setObjectName('securityNotice')
        sec_layout = QVBoxLayout(security_box)
        sec_title = QLabel('🔒 امنیت و حریم خصوصی')
        sec_title.setStyleSheet('font-weight: bold; color: #0284c7;')
        sec_text = QLabel('این برنامه تحت هیچ شرایطی رمز عبور یا اطلاعات هویتی شما را ذخیره نمی‌کند. احراز هویت مستقیماً با دامین کنترلر انجام می‌گیرد.')
        sec_text.setWordWrap(True)
        sec_layout.addWidget(sec_title)
        sec_layout.addWidget(sec_text)
        layout.addWidget(security_box)

        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton('💾 ذخیره تنظیمات')
        self.save_btn.setObjectName('primaryButton')
        self.save_btn.setMinimumWidth(160)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self._on_save_settings)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def load_values(self):
        """Loads values from settings service into inputs."""
        self.archive_dir_input.setText(self.settings_service.default_archive_dir)
        self.file_server_input.setText(self.settings_service.default_file_server)
        saved_drive = self.settings_service.default_drive_letter
        idx = self.drive_combo.findText(saved_drive)
        if idx >= 0:
            self.drive_combo.setCurrentIndex(idx)

    def _on_browse_archive_dir(self):
        curr = self.archive_dir_input.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, 'انتخاب پوشه پیش‌فرض آرشیو', curr)
        if selected:
            self.archive_dir_input.setText(selected)

    def _on_save_settings(self):
        archive_dir = self.archive_dir_input.text().strip()
        file_server = self.file_server_input.text().strip()
        drive_letter = self.drive_combo.currentText()

        self.settings_service.default_archive_dir = archive_dir
        self.settings_service.default_file_server = file_server
        self.settings_service.default_drive_letter = drive_letter

        if self.settings_service.save():
            QMessageBox.information(self, 'ذخیره شد', 'تنظیمات با موفقیت ذخیره گردید.')
            self.settings_saved.emit()
        else:
            QMessageBox.critical(self, 'خطا', 'خطا در ذخیره‌سازی تنظیمات در دیسک.')
