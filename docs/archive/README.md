# آرشیو مستندات FMMS

این پوشه نسخه‌های پیشین و گزارش‌های تاریخی را نگه می‌دارد. فایل‌ها حذف نشده‌اند تا سابقه تصمیم‌ها و بررسی‌ها قابل ردیابی بماند، اما نباید به‌عنوان وضعیت جاری پروژه استفاده شوند.

## `foundation/`

| فایل قدیمی | جایگزین جاری |
|---|---|
| `FMMS_Architecture.md` | `../TECHNICAL_ARCHITECTURE.md` |
| `Database_Design.md` | `../TECHNICAL_ARCHITECTURE.md` |
| `API_Contract.md` | `../TECHNICAL_ARCHITECTURE.md` |
| `SAP_Integration.md` | `../SAP_INTEGRATION_GUIDE.md` |
| `BRANCH_STRATEGY.md` | `../DEVELOPMENT_GUIDE.md` |
| `IMPLEMENTATION_TRACKER.md` | ADRهای معتبر در `../TECHNICAL_ARCHITECTURE.md` و کارهای باز در `../ENGINEERING_BACKLOG.md` |

## `reviews/`

گزارش‌های Authentication، Driver، Fault، Vehicle، SAP و Production Readiness در backlog واحد ادغام شده‌اند:

- [ENGINEERING_BACKLOG.md](../ENGINEERING_BACKLOG.md)

checkbox یا شماره خط موجود در فایل‌های آرشیوی وضعیت قطعی فعلی نیست. برای بستن یا باز کردن task فقط backlog جاری را تغییر دهید.

## سیاست آرشیو

- فایل‌های این پوشه ویرایش نمی‌شوند.
- محتوای معتبر جدید به اسناد canonical منتقل می‌شود.
- حذف نهایی آرشیو فقط پس از تأیید تیم و اطمینان از وجود Git history انجام می‌شود.
- فایل‌های `docs/odata/` بخشی از آرشیو نیستند و بدون تغییر باقی می‌مانند.
