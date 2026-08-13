# راهنمای مستندات FMMS

این صفحه نقطه شروع مستندات پروژه است. برای جلوگیری از پراکندگی، فقط اسناد بخش «اسناد مرجع جاری» باید در توسعه روزمره به‌روزرسانی شوند.

## اسناد مرجع جاری

| سند | کاربرد | مخاطب |
|---|---|---|
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | هدف کسب‌وکار، نقش‌ها، دامنه‌ها و workflowها | همه اعضای تیم |
| [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) | معماری Django، دیتابیس، API، امنیت، deployment و ADRها | Backend/Architecture |
| [SAP_INTEGRATION_GUIDE.md](SAP_INTEGRATION_GUIDE.md) | آموزش مقدماتی SAP و مسیر واقعی OData/BAPI در پروژه | Backend/SAP |
| [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md) | تنها مرجع فعال ایرادها، اولویت‌ها و معیار پذیرش | Tech Lead/Backend |
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | setup، تست، Git، CI و قواعد مستندسازی | توسعه‌دهندگان |

## ترتیب مطالعه پیشنهادی

```text
PROJECT_OVERVIEW
  -> TECHNICAL_ARCHITECTURE
  -> SAP_INTEGRATION_GUIDE
  -> DEVELOPMENT_GUIDE
  -> ENGINEERING_BACKLOG
```

## منابع اصلی و غیرقابل ادغام

| منبع | نقش |
|---|---|
| `Fleet Maintenance Management System.docx` | نیازمندی و معماری هدف Enterprise؛ لزوماً وضعیت فعلی نیست |
| `PM For Distribution Vehicles - Golestan - V2.pdf` | نمودار فرآیند کسب‌وکار |
| `SAP_API_Field_Reference.xlsx` | مرجع فیلدهای SAP؛ همه فیلدها در پروژه مصرف نمی‌شوند |
| `User Journey - Fleet Maintenance GBG.docx` | سند تاریخی پیاده‌سازی Java/Outbox؛ مرجع اجرایی Backend Django نیست |
| [wireframes/](wireframes/) | طرح‌های تصویری UI |
| [prototypes/](prototypes/) | آزمایش‌های فنی؛ کد Production نیست |
| `odata/` | داده خام مرجع؛ **نباید تغییر کند** |

## اسناد آرشیوی

گزارش‌ها، checklistها، tracker تاریخی و نسخه‌های کوتاه قدیمی در [archive/](archive/) نگهداری می‌شوند. آن‌ها فقط برای ردیابی سابقه‌اند و ممکن است شماره خط، endpoint، وضعیت یا تصمیم قدیمی داشته باشند.

## اولویت منابع هنگام تعارض

1. رفتار قابل اثبات کد، migration و تست جاری
2. تصمیم تأییدشده در اسناد مرجع جاری
3. قرارداد رسمی تأییدشده با تیم SAP/کسب‌وکار
4. سند نیازمندی Word/PDF/Excel
5. سند آرشیوی یا prototype

تعارض باید در `ENGINEERING_BACKLOG.md` به‌عنوان Decision/Open Item ثبت شود؛ هیچ‌کدام از منابع پایین‌تر نباید بی‌صدا جای واقعیت کد را بگیرند.

## قواعد نگهداری

- checklist یا review مستقل جدید نسازید؛ backlog واحد را به‌روزرسانی کنید.
- وضعیت جاری و معماری هدف را با برچسب روشن جدا کنید.
- credential، secret یا payload حساس را وارد مستندات نکنید.
- هر تغییر معماری مهم با ADR خلاصه و اثر migration/deployment ثبت شود.
- فایل‌های `archive/` فقط read-only تاریخی‌اند.
- پوشه `odata/` از فرآیند پاک‌سازی و بازنویسی مستثنا است.

آخرین تجمیع: 2026-08-14
