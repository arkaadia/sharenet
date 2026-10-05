# OutlookShareManager

**نرم‌افزار جامع مدیریت آرشیو اوت‌لوک و پوشه‌های اشتراکی شبکه در محیط ویندوز**  
**Enterprise Windows Desktop Application for Microsoft Outlook Archive & Active Directory SMB Share Management**

---

## 🌟 معرفی پروژه (Overview)

**OutlookShareManager** یک نرم‌افزار دسکتاپ بومی ویندوز بر پایه **Python 3.12** و **PySide6 (Qt)** است که به منظور برطرف کردن دو نیاز حیاتی سازمان‌ها و کاربران شرکتی در محیط Active Directory طراحی شده است:

1. **📧 آرشیو امن مایکروسافت اوت‌لوک (Outlook Archive):**
   - اتصال مستقیم به Classic Microsoft Outlook از طریق رابط COM MAPI.
   - استخراج و کپی امن ایمیل‌ها در قالب فایل‌های استاندارد PST.
   - فیلتر بر اساس بازه تاریخ شمسی و ساعت دریافت واقعی (`ReceivedTime`).
   - قانون ایمنی اجباری: **Copy Only** (عدم حذف، جابجایی یا دستکاری ایمیل‌های اصلی).

2. **📁 مدیریت پوشه‌های اشتراکی و اکتیودایرکتوری (SMB Shares & Active Directory):**
   - شناسایی خودکار دامین ویندوز، دامین کنترلر و نام کاربر بدون نیاز به ورود دستی.
   - احراز هویت واقعی با Active Directory از طریق مکانیزم‌های بومی ویندوز و LDAP.
   - کشف پوشه‌های اشتراکی فعال سرورهای فایل SMB (`NetShareEnum`).
   - اتصال و قطع درایوهای شبکه با استفاده از توابع ویندوز (`WNetAddConnection2` و `WNetCancelConnection2`).

---

## 🏗 ساختار پروژه (Architecture)

```text
OutlookShareManager/
│
├── main.py                     # نقطه ورود برنامه و مدیریت رویدادهای Qt
├── requirements.txt             # نیازمندی‌های پایتون
├── README.md                    # مستندات کامل برنامه
├── build.bat                    # اسکریپت کامپایل و ساخت اجرایی و نصاب ویندوز
│
├── installer/
│   └── OutlookShareManager.iss  # اسکریپت ساخت نصاب Inno Setup 6
│
├── .github/
│   └── workflows/
│       └── windows-build.yml    # پایپ‌لاین ساخت خودکار CI/CD در Windows Runner
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # پنجره اصلی برنامه با چیدمان راست‌به‌چپ (RTL)
│   ├── outlook_page.py          # صفحه آرشیو اوت‌لوک
│   ├── share_page.py            # صفحه پوشه‌های اشتراکی و احراز هویت دامین
│   └── settings_page.py         # صفحه تنظیمات و ذخیره‌سازی پیکربندی‌ها
│
├── services/
│   ├── __init__.py
│   ├── settings_service.py      # مدیریت تنظیمات کاربر بدون ذخیره رمز عبور
│   ├── outlook_service.py       # اتصال به رابط COM اوت‌لوک و استخراج پوشه‌ها
│   ├── archive_service.py       # سرویس کپی امن ایمیل‌ها در PST
│   ├── ad_service.py            # شناسایی دامین و احراز هویت Active Directory
│   ├── smb_service.py           # کشف و استخراج پوشه‌های اشتراکی SMB
│   └── drive_mapping_service.py # اتصال و قطع درایوهای شبکه ویندوز
│
├── utils/
│   ├── __init__.py
│   ├── persian_date.py          # مدیریت تاریخ‌های شمسی با jdatetime
│   ├── windows_utils.py         # شناسایی ویژگی‌های سیستم‌عامل و دامین ویندوز
│   └── logging_utils.py         # ثبت وقایع ایمن با حذف داده‌های حساس و رمز عبور
│
└── tests/
    └── test_foundation.py       # آزمون‌های خودکار ساختار، تاریخ، تنظیمات و لاگ
```

---

## 🔒 امنیت و حریم خصوصی (Security & Compliance)

- **عدم ذخیره‌سازی رمز عبور:** برنامه تحت هیچ شرایطی رمز عبور، کلیدهای دسترسی یا توکن‌های هویتی کاربران را روی دیسک ذخیره نمی‌کند.
- **ثبت وقایع ایمن (Safe Logging):** تمامی پیام‌های ثبت‌شده در لاگ از طریق فیلتر حساسیت بررسی شده و هرگونه فیلد حاوی اطلاعات هویتی به عنوان `***REDACTED***` ماسک می‌شود.
- **عملیات آرشیو کاملاً کپی (Copy Only):** فرآیند آرشیو هیچ‌گاه پیام‌های صندوق پستی اوت‌لوک کاربر را دستکاری یا حذف نمی‌کند.

---

## 🚀 راهنمای نصب و راه‌اندازی (Installation & Build)

### پیش‌نیازها
- سیستم‌عامل: Windows 10 یا Windows 11 (64-bit)
- نسخه پایتون: Python 3.12 (یا بالاتر)
- مایکروسافت اوت‌لوک (Classic Outlook 2016 / 2019 / 2021 / Microsoft 365)
- کامپایلر Inno Setup 6 (اختیاری - برای ساخت فایل Setup نصبی)

### راه‌اندازی محیط توسعه
```bash
git clone https://github.com/arkaadia/sharenet.git
cd sharenet
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### اجرای برنامه در حالت توسعه
```bash
python main.py
```

### اجرای تست‌های خودکار
```bash
pytest tests/ -v
```

### ساخت فایل اجرایی و نصاب ویندوز
کافیست اسکریپت `build.bat` را در ترمینال یا با دو بار کلیک اجرا کنید:
```cmd
build.bat
```
خروجی‌ها در مسیرهای زیر ایجاد خواهند شد:
- برنامه مستقل: `dist\OutlookShareManager\OutlookShareManager.exe`
- نصاب ویندوز: `installer_output\OutlookShareManager-Setup.exe`

---

## 📋 گزارش فازهای توسعه (Development Phases)

- **فاز ۱ (تکمیل شده):** زیرساخت و معماری پایه، واسط کاربری فارسی و راست‌به‌چپ (PySide6 RTL)، تنظیمات ایمن، ثبت وقایع محافظت‌شده، تقویم شمسی (`jdatetime`)، اسکریپت `build.bat`، ساختار Inno Setup و پایپ‌لاین CI/CD در GitHub Actions Windows.
- **فاز ۲:** پیاده‌سازی کامل و آزموده شده آرشیو اوت‌لوک با رابط واقعی COM، ایجاد PST واقعی و فیلتر دریافت پیام‌ها.
- **فاز ۳:** اتصال کامل Active Directory، کشف پیشرفته پوشه‌های SMB، بررسی دسترسی‌ها و مدیریت اتصالات درایو شبکه (`WNetAddConnection2`).
- **فاز ۴:** مقاوم‌سازی نهایی، کنترل خطا، انتشار نسخه v1.0.0 و ایجاد Release رسمی در گیت‌هاب.
