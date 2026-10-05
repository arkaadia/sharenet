"""
Outlook Archive Page for OutlookShareManager.
Phase 4: Fully integrated multi-threaded PST export worker, safe progress monitoring,
cancellation support, Jalali date range validation, and complete summary reporting.
"""
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QGroupBox, QFileDialog, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from services.outlook_service import OutlookService
from services.archive_service import ArchiveService, ArchiveProgress
from services.settings_service import SettingsService
from utils.persian_date import (
    get_current_jalali_date, validate_jalali_date, format_archive_filename,
    jalali_to_gregorian
)
from utils.logging_utils import get_logger

logger = get_logger('outlook_page')


class ArchiveWorkerThread(QThread):
    """Background worker thread for running Outlook archive without freezing UI."""
    progress_changed = Signal(object)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, archive_service: ArchiveService, folder_ids: list,
                 from_dt, to_dt, pst_path: str):
        super().__init__()
        self.archive_service = archive_service
        self.folder_ids = folder_ids
        self.from_dt = from_dt
        self.to_dt = to_dt
        self.pst_path = pst_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.archive_service.request_cancel()

    def run(self):
        try:
            result = self.archive_service.execute_archive(
                folder_entry_ids=self.folder_ids,
                from_datetime=self.from_dt,
                to_datetime=self.to_dt,
                pst_filepath=self.pst_path,
                progress_callback=self._on_progress,
                cancel_checker=lambda: self._cancelled
            )
            self.finished.emit(result)
        except Exception as e:
            logger.critical(f'Worker crashed: {e}', exc_info=True)
            self.error.emit(str(e))

    def _on_progress(self, prog: ArchiveProgress):
        self.progress_changed.emit(prog)


class OutlookPage(QWidget):
    """Persian RTL Outlook Archive Management Page with Phase 4 Worker & UI Hardening."""

    def __init__(self, outlook_service: OutlookService, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.outlook_service = outlook_service
        self.settings_service = settings_service
        self.archive_service = ArchiveService()
        self.worker = None

        self._init_ui()
        self.check_outlook_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_label = QLabel('📧 آرشیو ایمیل‌های مایکروسافت اوت‌لوک (Outlook Archive)')
        title_label.setObjectName('pageTitle')
        subtitle_label = QLabel(
            'استخراج و بایگانی امن ایمیل‌ها در قالب فایل PST بر اساس فیلتر تاریخ شمسی دریافت (ReceivedTime) | فاز ۴: مقاوم‌سازی نهایی'
        )
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

        # Select all / Deselect all
        tree_btns_layout = QHBoxLayout()
        self.select_all_btn = QPushButton('انتخاب همه پوشه‌ها')
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(Qt.Checked))
        self.deselect_all_btn = QPushButton('لغو انتخاب همه')
        self.deselect_all_btn.clicked.connect(lambda: self._set_all_checked(Qt.Unchecked))
        tree_btns_layout.addWidget(self.select_all_btn)
        tree_btns_layout.addWidget(self.deselect_all_btn)
        folders_layout.addLayout(tree_btns_layout)

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
        self.from_date_input = QLineEdit('1405/01/01')
        self.from_date_input.setPlaceholderText('1405/01/01')
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
        default_filename = format_archive_filename('1405-01-01', today_fa)
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

        # Action Buttons
        btn_action_layout = QHBoxLayout()
        self.start_archive_btn = QPushButton('🚀 شروع عملیات آرشیو')
        self.start_archive_btn.setObjectName('primaryButton')
        self.start_archive_btn.setMinimumHeight(44)
        self.start_archive_btn.clicked.connect(self._on_start_archive)
        btn_action_layout.addWidget(self.start_archive_btn, 2)

        self.cancel_archive_btn = QPushButton('🛑 لغو عملیات')
        self.cancel_archive_btn.setEnabled(False)
        self.cancel_archive_btn.setMinimumHeight(44)
        self.cancel_archive_btn.clicked.connect(self._on_cancel_archive)
        btn_action_layout.addWidget(self.cancel_archive_btn, 1)

        config_layout.addLayout(btn_action_layout)
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
        self.progress_detail_label = QLabel('')
        self.progress_detail_label.setStyleSheet('color: #64748b; font-size: 11px;')

        prog_layout.addWidget(self.progress_bar)
        prog_layout.addWidget(self.progress_status_label)
        prog_layout.addWidget(self.progress_detail_label)

        layout.addWidget(self.progress_group)

    def _set_all_checked(self, state: Qt.CheckState):
        root = self.folder_tree.invisibleRootItem()
        self._check_node_recursive(root, state)

    def _check_node_recursive(self, parent_item: QTreeWidgetItem, state: Qt.CheckState):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setCheckState(0, state)
            self._check_node_recursive(child, state)

    def check_outlook_status(self):
        """Checks Outlook COM availability and updates the UI."""
        info = self.outlook_service.detect_outlook()
        if info['available']:
            self.status_icon.setText('✅')
            self.status_text.setText(info['message_fa'])
            self.status_banner.setStyleSheet(
                'background-color: #ecfdf5; border: 1px solid #10b981; border-radius: 6px; padding: 10px;'
            )
            self.load_outlook_folders()
        else:
            self.status_icon.setText('⚠️')
            self.status_text.setText(info['message_fa'] + ' (حالت شبیه‌سازی/دمو فعال است)')
            self.status_banner.setStyleSheet(
                'background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 10px;'
            )
            self._load_demo_folders()

    def _load_demo_folders(self):
        """Loads realistic demo folder tree when Outlook COM is not running or on Linux."""
        self.folder_tree.clear()
        mailbox = QTreeWidgetItem(self.folder_tree, ['صندوق پستی کاربر سازمانی (Exchange)', ''])
        mailbox.setFlags(mailbox.flags() | Qt.ItemIsUserCheckable)
        mailbox.setCheckState(0, Qt.Checked)

        demo_folders = [
            ('صندوق دریافت (Inbox)', '1,420', 'id-inbox'),
            ('پیام‌های ارسال‌شده (Sent Items)', '856', 'id-sent'),
            ('پوشه مالی و قراردادها', '342', 'id-finance'),
            ('پروژه‌های شبکه و سرور', '198', 'id-projects'),
            ('بایگانی سال گذشته', '512', 'id-archive-prev'),
        ]
        for name, count, eid in demo_folders:
            node = QTreeWidgetItem(mailbox, [name, count])
            node.setFlags(node.flags() | Qt.ItemIsUserCheckable)
            node.setCheckState(0, Qt.Checked)
            node.setData(0, Qt.UserRole, eid)

        mailbox.setExpanded(True)

    def load_outlook_folders(self):
        """Populates real Outlook folders into tree."""
        self.folder_tree.clear()
        stores = self.outlook_service.get_mailboxes_and_folders()
        if not stores:
            self._load_demo_folders()
            return

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

    def _get_selected_folder_ids(self) -> list:
        selected = []
        root = self.folder_tree.invisibleRootItem()
        self._collect_checked_folders(root, selected)
        return selected

    def _collect_checked_folders(self, parent: QTreeWidgetItem, result: list):
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.checkState(0) == Qt.Checked:
                eid = child.data(0, Qt.UserRole)
                if eid:
                    result.append(eid)
            self._collect_checked_folders(child, result)

    def _on_browse_dest(self):
        curr = self.pst_dest_input.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, 'انتخاب مسیر ذخیره فایل آرشیو PST', curr)
        if selected:
            self.pst_dest_input.setText(selected)

    def _on_start_archive(self):
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

        from_dt = jalali_to_gregorian(from_date)
        to_dt = jalali_to_gregorian(to_date)
        if from_dt > to_dt:
            QMessageBox.warning(self, 'خطای بازه تاریخ', 'تاریخ شروع نمی‌تواند پس از تاریخ پایان باشد.')
            return

        pst_dir = self.pst_dest_input.text().strip()
        pst_name = self.pst_name_input.text().strip()

        if not pst_dir:
            pst_dir = str(Path.home())
            self.pst_dest_input.setText(pst_dir)

        if not pst_name.lower().endswith('.pst'):
            pst_name += '.pst'

        target_file = os.path.join(pst_dir, pst_name)

        folder_ids = self._get_selected_folder_ids()
        if not folder_ids:
            QMessageBox.warning(self, 'پوشه انتخاب نشده', 'لطفاً حداقل یک پوشه را جهت آرشیو علامت بزنید.')
            return

        # Confirm
        confirm_lines = [
            'آیا از شروع عملیات آرشیو اطمینان دارید؟',
            '',
            f'• از تاریخ شمسی: {from_date}',
            f'• تا تاریخ شمسی: {to_date}',
            f'• تعداد پوشه‌های منتخب: {len(folder_ids)} پوشه',
            f'• نام فایل آرشیو: {pst_name}',
            f'• مسیر ذخیره: {pst_dir}',
            '',
            '🛡 توجه ایمنی: هیچ ایمیلی از حساب اوت‌لوک شما حذف نخواهد شد (Copy Only).'
        ]
        reply = QMessageBox.question(
            self, 'تأیید شروع آرشیو', '\n'.join(confirm_lines),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Disable inputs and launch worker
        self.start_archive_btn.setEnabled(False)
        self.cancel_archive_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_status_label.setText('در حال آغاز فرآیند آرشیو...')

        self.worker = ArchiveWorkerThread(
            self.archive_service, folder_ids, from_dt, to_dt, target_file
        )
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_cancel_archive(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.progress_status_label.setText('در حال توقف و لغو فرآیند...')
            self.cancel_archive_btn.setEnabled(False)

    @Slot(object)
    def _on_worker_progress(self, prog: ArchiveProgress):
        self.progress_bar.setValue(prog.percentage)
        self.progress_status_label.setText(
            f'{prog.status_message} ({prog.percentage}%)'
        )
        self.progress_detail_label.setText(
            f'پوشه: {prog.current_folder} | پردازش شده: {prog.processed_count} از {prog.total_count} | موفق: {prog.success_count} | خطا: {prog.failed_count}'
        )

    @Slot(dict)
    def _on_worker_finished(self, result: dict):
        self.start_archive_btn.setEnabled(True)
        self.cancel_archive_btn.setEnabled(False)

        if result.get('cancelled'):
            self.progress_status_label.setText('عملیات توسط کاربر لغو گردید.')
            QMessageBox.information(self, 'لغو عملیات', 'فرآیند آرشیو متوقف شد.')
            return

        if result.get('success'):
            self.progress_bar.setValue(100)
            self.progress_status_label.setText('عملیات با موفقیت به پایان رسید.')
            summary = [
                '🎉 عملیات آرشیو با موفقیت کامل انجام شد.',
                '',
                f'• پیام‌های ذخیره‌شده: {result.get("items_copied", 0)}',
                f'• فایل خروجی PST: {result.get("pst_file", "")}',
                f'• زمان اجرا: {result.get("elapsed_seconds", 0)} ثانیه',
                '',
                'تمامی ایمیل‌های اصلی در اوت‌لوک بدون هیچ‌گونه تغییری حفظ شده‌اند.'
            ]
            QMessageBox.information(self, 'پایان موفقیت‌آمیز آرشیو', '\n'.join(summary))
        else:
            self.progress_status_label.setText('خطا در انجام آرشیو.')
            QMessageBox.critical(self, 'خطا در عملیات آرشیو', result.get('message_fa', 'خطای نامشخص.'))

    @Slot(str)
    def _on_worker_error(self, err_msg: str):
        self.start_archive_btn.setEnabled(True)
        self.cancel_archive_btn.setEnabled(False)
        self.progress_status_label.setText(f'خطای مهلک: {err_msg}')
        QMessageBox.critical(self, 'خطای سیستمی', f'خطا در نخ اجرای آرشیو: {err_msg}')
