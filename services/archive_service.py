"""
Outlook Archive Service.
Handles copying emails into PST archives filtered strictly by ReceivedTime.
MANDATORY SAFETY: COPY ONLY. Never move, delete, or modify original messages.
"""
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from utils.logging_utils import get_logger

logger = get_logger('archive_service')

class ArchiveProgress:
    """Data transfer object for progress updates."""
    def __init__(self, current_folder: str = '', current_item: str = '',
                 processed_count: int = 0, total_count: int = 0,
                 success_count: int = 0, failed_count: int = 0):
        self.current_folder = current_folder
        self.current_item = current_item
        self.processed_count = processed_count
        self.total_count = total_count
        self.success_count = success_count
        self.failed_count = failed_count

    @property
    def percentage(self) -> int:
        if self.total_count <= 0:
            return 0
        return min(100, int((self.processed_count / self.total_count) * 100))
