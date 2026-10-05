"""
Windows-specific system, domain, and drive mapping utilities.
Safely detects Windows domain, logon server, and drive letters.
"""
import os
import sys
import string
from pathlib import Path
from typing import Dict, Any, List

def is_windows() -> bool:
    """Checks if running on Windows OS."""
    return sys.platform == 'win32'

def get_app_dir() -> Path:
    """Returns the application configuration directory (%APPDATA%\OutlookShareManager)."""
    if is_windows():
        appdata = os.environ.get('APPDATA')
        if appdata:
            p = Path(appdata) / 'OutlookShareManager'
            p.mkdir(parents=True, exist_ok=True)
            return p
    # Fallback for Linux or testing
    p = Path.home() / '.outlooksharemanager'
    p.mkdir(parents=True, exist_ok=True)
    return p

def detect_domain_info() -> Dict[str, Any]:
    """
    Detects Windows domain environment information using official Windows environment variables
    and system APIs without user input.
    """
    domain = os.environ.get('USERDNSDOMAIN') or os.environ.get('USERDOMAIN') or ''
    dc = os.environ.get('LOGONSERVER') or ''
    user = os.environ.get('USERNAME') or ''
    computer = os.environ.get('COMPUTERNAME') or ''
    
    # Strip leading backslashes from LOGONSERVER (e.g., \DC01 -> DC01)
    if dc.startswith('\\'):
        dc = dc[2:]
        
    is_domain_joined = False
    dns_domain = os.environ.get('USERDNSDOMAIN', '')
    if dns_domain:
        is_domain_joined = True
    elif domain and domain.upper() != computer.upper():
        is_domain_joined = True

    # Real Windows Win32 API detection if pywin32 is present
    if is_windows():
        try:
            import win32api
            import win32net
            try:
                join_status = win32net.NetGetJoinInformation()
                if join_status and len(join_status) >= 2:
                    joined_domain, join_type = join_status[0], join_status[1]
                    if joined_domain:
                        domain = joined_domain
                        # 3 = NetSetupDomainName (joined to domain)
                        if join_type == 3:
                            is_domain_joined = True
            except Exception:
                pass
        except ImportError:
            pass

    return {
        'domain': domain if domain else 'شناسایی نشد (Standalone / Workgroup)',
        'domain_controller': dc if dc else 'مشخص نشده',
        'current_user': user,
        'computer_name': computer,
        'is_domain_joined': is_domain_joined,
    }

def get_occupied_drive_letters() -> List[str]:
    """
    Returns a list of drive letters currently in use on the system (e.g. ['C:', 'D:', 'Z:']).
    """
    occupied = []
    if is_windows():
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                occupied.append(f'{letter}:')
            bitmask >>= 1
    return occupied

def get_available_drive_letters() -> List[str]:
    """
    Returns a list of drive letters available for network mapping, in reverse alphabetical order (Z: to D:).
    """
    occupied = set(get_occupied_drive_letters())
    # Exclude A and B (floppy), and C (usually system drive)
    all_letters = [f'{letter}:' for letter in string.ascii_uppercase if letter not in ('A', 'B', 'C')]
    available = [l for l in all_letters if l not in occupied]
    # Reverse sort so Z: is first
    available.sort(reverse=True)
    return available
