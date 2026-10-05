"""
Logging utility for OutlookShareManager.
Ensures thread-safe, rotating file logging and strict redaction of sensitive credentials.
"""
import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

SENSITIVE_PATTERNS = [
    re.compile(r'(password|passwd|pwd|secret|token|cred|credential)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE),
    re.compile(r'("password"\s*:\s*")[^"]+(")', re.IGNORECASE),
]

class SensitiveDataFilter(logging.Filter):
    """Filter that redacts passwords and sensitive tokens from log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                redacted_args = {}
                for k, v in record.args.items():
                    if any(s in k.lower() for s in ['pass', 'pwd', 'secret', 'token', 'cred']):
                        redacted_args[k] = '***REDACTED***'
                    else:
                        redacted_args[k] = v
                record.args = redacted_args
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    '***REDACTED***' if isinstance(a, str) and any(s in a.lower() for s in ['pass', 'secret']) else a
                    for a in record.args
                )
        return True

    @staticmethod
    def redact(text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(r'\1: ***REDACTED***', text)
        return text

def get_log_dir() -> Path:
    """Returns the application log directory."""
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            log_dir = Path(appdata) / 'OutlookShareManager' / 'logs'
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                return log_dir
            except Exception:
                pass
    local_dir = Path(__file__).resolve().parent.parent / 'logs'
    local_dir.mkdir(parents=True, exist_ok=True)
    return local_dir

_is_configured = False

def setup_logging(level: int = logging.INFO, log_filename: str = 'app.log') -> logging.Logger:
    """Initializes the logging system with rotating file and console output."""
    global _is_configured
    root_logger = logging.getLogger('OutlookShareManager')
    
    if _is_configured:
        return root_logger

    root_logger.setLevel(level)
    redact_filter = SensitiveDataFilter()

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] [%(name)s:%(threadName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redact_filter)
    root_logger.addHandler(console_handler)

    try:
        log_dir = get_log_dir()
        log_file = log_dir / log_filename
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redact_filter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f'Failed to initialize file logger: {e}\n')

    _is_configured = True
    root_logger.info('OutlookShareManager logging initialized.')
    return root_logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Returns a child logger or root logger."""
    if not _is_configured:
        setup_logging()
    if name:
        return logging.getLogger(f'OutlookShareManager.{name}')
    return logging.getLogger('OutlookShareManager')
