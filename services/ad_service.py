"""
Active Directory and Windows Domain Authentication Service.
Detects domain details, authenticates domain users via LDAP / Windows SSPI APIs.
"""
import os
import sys
from typing import Dict, Any, Optional
from utils.windows_utils import detect_domain_info
from utils.logging_utils import get_logger

logger = get_logger('ad_service')

class ActiveDirectoryService:
    """Service for domain environment detection and Active Directory authentication."""
    def __init__(self):
        self._domain_info = detect_domain_info()

    def get_domain_info(self) -> Dict[str, Any]:
        """Returns detected domain, domain controller, and user info (Read-only)."""
        return self._domain_info

    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticates user against Active Directory without storing the password.
        Uses LDAP or Windows LogonUser API.
        """
        if not username or not password:
            return {
                'success': False,
                'message_fa': 'نام کاربری و کلمه عبور الزامی است.'
            }

        domain = self._domain_info.get('domain', '')
        dc = self._domain_info.get('domain_controller', '')

        if sys.platform != 'win32':
            # Testing / Linux fallback
            return {
                'success': False,
                'message_fa': 'احراز هویت Active Directory نیازمند اجرای برنامه در ویندوز عضو دامین است.'
            }

        # Real Windows LogonUser API or LDAP
        try:
            import win32security
            import win32con
            token = win32security.LogonUser(
                username,
                domain if domain else None,
                password,
                win32con.LOGON32_LOGON_NETWORK,
                win32con.LOGON32_PROVIDER_DEFAULT
            )
            if token:
                token.Close()
                logger.info(f'User {username} authenticated successfully against domain {domain}.')
                return {
                    'success': True,
                    'message_fa': f'احراز هویت کاربر {username} با موفقیت انجام شد.'
                }
        except Exception as e:
            logger.warning(f'LogonUser failed for user {username}: {e}')

        # LDAP fallback if ldap3 is present
        try:
            from ldap3 import Server, Connection, ALL, NTLM
            server_target = dc or domain
            if server_target:
                server = Server(server_target, get_info=ALL)
                user_dn = f'{domain}\{username}' if domain else username
                conn = Connection(server, user=user_dn, password=password, authentication=NTLM)
                if conn.bind():
                    conn.unbind()
                    logger.info(f'LDAP authentication succeeded for {username}.')
                    return {
                        'success': True,
                        'message_fa': f'احراز هویت با موفقیت از طریق LDAP دامین انجام شد.'
                    }
        except Exception as ldap_err:
            logger.warning(f'LDAP bind attempt failed: {ldap_err}')

        return {
            'success': False,
            'message_fa': 'نام کاربری یا کلمه عبور اشتباه است، یا ارتباط با دامین کنترلر برقرار نشد.'
        }
