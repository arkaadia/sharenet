"""
Persian (Jalali / Solar Hijri) date utilities using jdatetime with mathematical fallback.
Provides conversions between Gregorian and Jalali, validation, and Persian formatting.
"""
import re
from datetime import date, datetime
from typing import Tuple, Optional

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False

JALALI_DATE_PATTERN = re.compile(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$')

def _gregorian_to_jalali_algo(gy: int, gm: int, gd: int) -> Tuple[int, int, int]:
    """Mathematical conversion of Gregorian to Jalali date."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if (gm > 2) else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return (jy, jm, jd)

def _jalali_to_gregorian_algo(jy: int, jm: int, jd: int) -> Tuple[int, int, int]:
    """Mathematical conversion of Jalali to Gregorian date."""
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd + ((jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186)
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [0, 31, 29 if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return (gy, gm, gd)

def get_current_jalali_date() -> str:
    """Returns today's Jalali date formatted as YYYY/MM/DD."""
    if HAS_JDATETIME:
        today = jdatetime.date.today()
        return today.strftime('%Y/%m/%d')
    now = datetime.now()
    jy, jm, jd = _gregorian_to_jalali_algo(now.year, now.month, now.day)
    return f'{jy}/{jm:02d}/{jd:02d}'

def validate_jalali_date(date_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a Jalali date string (YYYY/MM/DD).
    Returns (True, None) if valid, or (False, error_message_fa).
    """
    if not date_str or not isinstance(date_str, str):
        return False, 'تاریخ نمی‌تواند خالی باشد.'

    match = JALALI_DATE_PATTERN.match(date_str.strip())
    if not match:
        return False, 'فرمت تاریخ نامعتبر است. فرمت صحیح: 1405/07/13'

    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))

    if year < 1300 or year > 1500:
        return False, f'سال نامعتبر است ({year}). سال باید بین ۱۳۰۰ تا ۱۵۰۰ باشد.'

    if month < 1 or month > 12:
        return False, f'ماه نامعتبر است ({month}). ماه باید بین ۱ تا ۱۲ باشد.'

    if month <= 6 and (day < 1 or day > 31):
        return False, f'روز نامعتبر است ({day}). در ۶ ماه اول سال، روز باید بین ۱ تا ۳۱ باشد.'

    if month > 6 and month <= 11 and (day < 1 or day > 30):
        return False, f'روز نامعتبر است ({day}). در ماه‌های ۷ تا ۱۱، روز باید بین ۱ تا ۳۰ باشد.'

    if month == 12:
        if HAS_JDATETIME:
            try:
                jdatetime.date(year, month, day)
            except ValueError:
                return False, f'روز نامعتبر است ({day}). اسفند در سال {year} دارای ۲۹ روز است.'
        elif day < 1 or day > 30:
            return False, f'روز نامعتبر است ({day}).'

    return True, None

def jalali_to_gregorian(date_str: str) -> datetime:
    """
    Converts a valid Jalali date string (YYYY/MM/DD) to a Python datetime (start of day).
    Raises ValueError on invalid date.
    """
    is_valid, err = validate_jalali_date(date_str)
    if not is_valid:
        raise ValueError(err)

    match = JALALI_DATE_PATTERN.match(date_str.strip())
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))

    if HAS_JDATETIME:
        jdate = jdatetime.date(year, month, day)
        gdate = jdate.togregorian()
        return datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
    else:
        gy, gm, gd = _jalali_to_gregorian_algo(year, month, day)
        return datetime(gy, gm, gd, 0, 0, 0)

def gregorian_to_jalali(dt: datetime) -> str:
    """Converts a Gregorian datetime to Jalali string YYYY/MM/DD."""
    if HAS_JDATETIME:
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        return jdt.strftime('%Y/%m/%d')
    jy, jm, jd = _gregorian_to_jalali_algo(dt.year, dt.month, dt.day)
    return f'{jy}/{jm:02d}/{jd:02d}'

def format_archive_filename(from_date_str: str, to_date_str: str) -> str:
    """
    Generates standard archive filename: Archive_1405-07-01_to_1405-07-13.pst
    """
    from_safe = from_date_str.replace('/', '-').replace(' ', '')
    to_safe = to_date_str.replace('/', '-').replace(' ', '')
    return f'Archive_{from_safe}_to_{to_safe}.pst'
