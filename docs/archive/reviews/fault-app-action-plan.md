# برنامه اصلاح اپ `fault` — به ترتیب اولویت

> مبنا: بررسی کامل ۲۹ فایل پایتون اپ `apps/fault` (~۱٬۹۰۰ خط غیر-migration).
> تاریخ بررسی: ۱۴۰۵/۰۵/۰۶ (2026-07-28)
> امتیاز فعلی اپ: **6.6 / 10**

ترتیب بر اساس «بیشترین تأثیر بر کیفیت پروژه به ازای کمترین ریسک تغییر» چیده شده است.
موارد ۱ تا ۵ باگ یا نقص یکپارچگی داده‌اند و باید قبل از هر ریفکتور دیگری انجام شوند.

---

## فاز ۱ — باگ‌های صحت و یکپارچگی داده (فوری)

### ۱. رفع عبور از اعتبارسنجی `FaultCode`
- **فایل:** `apps/fault/domain/value_objects.py:41`
- **مشکل:** `_PATTERN` به‌جای `ClassVar` یک فیلد dataclass شده؛ `FaultCode('!!!bad!!!', re.compile('.*'))` از اعتبارسنجی عبور می‌کند (تأیید عملی شد).
- **اصلاح:** `_PATTERN: ClassVar[re.Pattern[str]] = re.compile(...)`
- **ریسک:** بسیار کم · **تلاش:** ۵ دقیقه
- **تست لازم:** یک تست که ثابت کند `dataclasses.fields(FaultCode)` فقط `['value']` است.

### ۲. رفع پاسخ کهنه در `mark_usable`
- **فایل:** `apps/fault/application/services/distribution_fault_decision_service.py:104`
- **مشکل:** `return result` یک snapshot قبل از ذخیره‌ی `note` است؛ API همیشه `distribution_decision_note: null` برمی‌گرداند.
- **اصلاح:** `return _to_response_dto(fault)`
- **ریسک:** کم · **تلاش:** ۵ دقیقه
- **تست لازم:** ارسال `note` و assert روی حضور آن در پاسخ.

### ۳. افزودن `transaction.atomic` به سرویس‌های نویسنده
- **فایل‌ها:**
  - `distribution_fault_decision_service.py` → `mark_usable`, `mark_unusable`
  - `close_fault_service.py` → `execute`
  - `report_fault_service.py` → `execute`
- **مشکل:** `mark_unusable` پنج نوشتن مستقل انجام می‌دهد؛ شکست در میانه ⇒ خودرو OUT_OF_SERVICE بدون دستور تعمیر (رکورد یتیم و غیرقابل بازیابی از UI).
- **اصلاح:** دکوراتور `@transaction.atomic` + انتقال فراخوانی SAP به `transaction.on_commit` تا اتصال DB پشت I/O شبکه قفل نشود.
- **ریسک:** متوسط (نیاز به بازبینی نقاط commit) · **تلاش:** نیم روز

### ۴. بستن شکاف نگهبان وضعیت در `mark_usable`
- **فایل:** `distribution_fault_decision_service.py:63`
- **مشکل:** برخلاف `mark_unusable` (خط ۱۱۷) هیچ چک `status != OPEN` ندارد؛ چون گذار `IN_REPAIR → CLOSED` مجاز است، سرپرست توزیع می‌تواند خرابیِ در حال تعمیر را ببندد.
- **اصلاح:** همان `FMMSStateError` با `error_code="FAULT_NOT_AWAITING_DISTRIBUTION"` در ابتدای متد.
- **ریسک:** کم (ممکن است داده‌ی تست موجود را بشکند) · **تلاش:** ۱۵ دقیقه

### ۵. تضمین «یک جریان باز به ازای هر خودرو» در سطح دیتابیس
- **فایل:** `apps/fault/infrastructure/models.py` (+ migration جدید)
- **مشکل:** `assert_vehicle_has_no_open_flow` یک check-then-act بدون قفل است؛ دو درخواست هم‌زمان دو خرابی باز می‌سازند.
- **اصلاح:**
  ```python
  models.UniqueConstraint(
      fields=["vehicle_id"],
      condition=~models.Q(status="CLOSED") & models.Q(is_deleted=False),
      name="unique_open_fault_per_vehicle",
  )
  ```
  به‌همراه تبدیل `IntegrityError` به `FMMSStateError` در سرویس.
- **ریسک:** بالا (نیاز به پاک‌سازی داده‌ی موجود قبل از migration) · **تلاش:** ۱ روز
- **پیش‌نیاز:** کوئری بررسی داده‌های نقض‌کننده در محیط production.

---

## فاز ۲ — کارایی (تأثیر مستقیم بر تجربه کاربر)

### ۶. رفع N+1 در `ListFaultsService`
- **فایل:** `apps/fault/application/services/get_fault_service.py:152`
- **مشکل:** یک کوئری `get_profile` به ازای هر خرابی (پیاده‌سازی `DjangoUserProfileReader` بدون کش است). با ۵٬۰۰۰ خرابی ⇒ ۵٬۰۰۱ کوئری برای نمایش ۲۰ ردیف.
- **اصلاح:** افزودن `get_profiles(ids: set[UUID]) -> dict[UUID, UserProfileSummaryDTO]` به `IUserProfileReader` و batch کردن.
- **ریسک:** کم · **تلاش:** نیم روز
- **توجه:** پورت متعلق به اپ `authentication` است؛ هماهنگی لازم است.

### ۷. انتقال صفحه‌بندی به لایه repository
- **فایل‌ها:** `fault_repository.py`, `repositories.py`, `get_fault_service.py`
- **مشکل:** `list_all` کل جدول را می‌کشد و `paginate_dto_list` در حافظه برش می‌زند.
- **اصلاح:** پارامترهای `limit`/`offset` به پورت repository و بازگرداندن `total_count`.
- **ریسک:** متوسط (تغییر امضای پورت ⇒ همه‌ی فِیک‌های تست) · **تلاش:** ۱ روز

### ۸. افزودن ایندکس برای مرتب‌سازی پیش‌فرض
- **فایل:** `apps/fault/infrastructure/models.py:20` (+ migration)
- **مشکل:** `order_by("-reported_at")` روی ستون بدون ایندکس؛ در هیچ‌کدام از دو composite index موجود نیست.
- **اصلاح:** `models.Index(fields=["is_deleted", "-reported_at"], name="fault_active_reported_idx")`
- **ریسک:** بسیار کم · **تلاش:** ۱۵ دقیقه

### ۹. بهینه‌سازی نوشتن در repository
- **فایل:** `apps/fault/infrastructure/repositories.py:184-200`
- **مشکل:** دو write برای هر insert (`update_or_create` سپس `save(update_fields=["created_at"])`). خرابی با ۵ آیتم = ۱۲ کوئری نوشتن.
- **اصلاح:** `created_at` را داخل `defaults` قرار دهید.
- **ریسک:** کم · **تلاش:** ۱ ساعت

### ۱۰. بهینه‌سازی حلقه‌ی sync کاتالوگ
- **فایل:** `sync_fault_catalog_from_sap_service.py:130`
- **مشکل:** `get_by_sap_key` + `update_or_create` = دو کوئری per row (۶۶+ کوئری برای ۳۳ ردیف).
- **اصلاح:** `bulk_create(update_conflicts=True, unique_fields=["code", "code_group"])` — constraint لازم از قبل در `models.py:93` وجود دارد.
- **ریسک:** کم · **تلاش:** نیم روز

---

## فاز ۳ — معماری و بدهی فنی

### ۱۱. استخراج mapper عمومی از `report_fault_service`
- **مشکل:** تابع خصوصی `_to_response_dto` توسط ۵ ماژول import می‌شود، از جمله `apps/inspection` (اپ دیگر). ضمناً `close_fault_service.py:17` از ماژول خصوصی `apps.repair.application.services._timeline_helper` می‌خواند.
- **اصلاح:** ایجاد `apps/fault/application/mappers/fault_mapper.py` با تابع عمومی `to_response_dto`؛ عمومی‌سازی `_timeline_helper` در اپ repair.
- **ریسک:** کم (فقط import) · **تلاش:** ۲ ساعت
- **سود جانبی:** `report_fault_service` دیگر mapperِ سراسری اپ نیست ⇒ SRP احیا می‌شود.

### ۱۲. تزریق `CloseFaultService` به‌جای ساخت داخلی
- **فایل:** `distribution_fault_decision_service.py:65`
- **مشکل:** نقض DIP و غیرقابل mock بودن.
- **اصلاح:** افزودن به `__init__` و سیم‌کشی در `interfaces/api/v1/deps.py`.
- **ریسک:** کم · **تلاش:** ۱ ساعت

### ۱۳. یکسان‌سازی مدیریت `updated_at`
- **فایل:** `repositories.py:78` + ۵ سرویس
- **مشکل:** repository مقدار entity را با `datetime.now()` بازنویسی می‌کند، پس ۵ انتساب تکراری در سرویس‌ها بی‌اثر است و entity با DB واگرا می‌شود.
- **اصلاح:** یکی را انتخاب کنید — پیشنهاد: `"updated_at": fault.updated_at` در repository و حذف پنج خط تکراری.
- **ریسک:** کم · **تلاش:** ۱ ساعت

### ۱۴. حذف کد مرده (۶ مورد، همه با grep تأیید شده)
| مورد | محل |
|---|---|
| `IFaultRepository.delete()` | `fault_repository.py:96` + `repositories.py:205` — صفر فراخوانی حتی در تست |
| `IFaultCatalogRepository.get_by_id()` | `fault_catalog_repository.py:15` + `catalog_repositories.py:40` |
| `Fault.is_critical` | `entities.py:198` — فقط تست |
| `Fault.is_open` | `entities.py:203` — فقط تست |
| `AssignFaultDTO.assigned_by` | `fault_dto.py:76` — پر می‌شود ولی خوانده نمی‌شود |
| `Fault.sap_defect_code` | `entities.py:123` — هیچ‌جا ست نمی‌شود؛ شاخه‌ی `report_fault_service.py:313` همیشه False |

- **سود جانبی:** حذف `delete()` انتزاعی، ۷ فِیک تست را از پیاده‌سازی متد بلااستفاده خلاص می‌کند (ISP).
- **تصمیم لازم:** آیا `sap_defect_code` قرار بوده از کاتالوگ SAP پر شود؟ اگر بله، این یک feature ناتمام است نه کد مرده — باید تیکت جدا بخورد.
- **ریسک:** کم · **تلاش:** ۲ ساعت

### ۱۵. خارج کردن متن فارسی از لایه Application
- **فایل‌ها:** `close_fault_service.py:36-41`, `distribution_fault_decision_service.py:208`
- **اصلاح:** جایگزینی با کد رویداد و resolve متن در `interfaces/` یا فایل ترجمه.
- **ریسک:** کم · **تلاش:** ۲ ساعت

### ۱۶. ثبت وضعیت همگام‌سازی SAP روی خرابی
- **فایل:** `report_fault_service.py:344`
- **مشکل:** شکست SAP بی‌صدا بلعیده می‌شود؛ «تلاش شد و شکست خورد» از «هنوز تلاش نشده» قابل تفکیک نیست ⇒ retry خودکار ممکن نیست. با توجه به قطعی DNS مشاهده‌شده، سناریوی واقعی است.
- **اصلاح:** فیلد `sap_sync_status` (`PENDING`/`SYNCED`/`FAILED`) + job بازپخش.
- **اصلاح فوری و کم‌هزینه:** افزودن `exc_info=True` به `logger.error` (مطابق `sync_fault_catalog_from_sap_service.py:119`).
- **ریسک:** متوسط · **تلاش:** ۱ تا ۲ روز

---

## فاز ۴ — خوانایی و پاکسازی

### ۱۷. تصحیح docstring نادرست `ListFaultsService`
- **فایل:** `get_fault_service.py:111`
- **مشکل:** نوشته «returns an empty list (explicit filter required)» ولی کد `list_all(status=status)` را صدا می‌زند — دقیقاً برعکس. پارامتر `status` هم در `Args:` غایب است.

### ۱۸. تغییر نام `_cancel_distribution_usable_repair_orders`
- **فایل:** `close_fault_service.py:125`
- **مشکل:** علاوه بر لغو، دستورهای `WAITING_TRANSPORT_FINAL_APPROVAL` را «تکمیل» می‌کند ولی همه را در `cancelled_count` می‌شمارد و لاگ `repairs_cancelled` می‌زند ⇒ آمار لاگ غلط است.
- **اصلاح:** نام `_settle_repair_orders_on_close` + دو شمارنده‌ی جدا در خروجی و لاگ.

### ۱۹. استخراج ثابت‌های طول
- `500` در سه جا مستقل: `value_objects.py:73`, `models.py:19`, `serializers.py:27`
- literalهای `[:20]`, `[:100]`, `[:500]` در `report_fault_service.py:249,286,294`

### ۲۰. موارد جزئی
- `existing[0]` غیرقطعی → `min(existing, key=lambda o: o.created_at)` — `distribution_fault_decision_service.py:192`
- کوتاه‌سازی بعد از پیشوندگذاری باعث بریدن انتهای متن — `report_fault_service.py:288-294`
- `link_sap_notification` تنها mutator بدون نگهبان CLOSED — `entities.py:189`
- منطق زائد `setdefault` روی dict از پیش مقداردهی‌شده — `repositories.py:107-111`
- بارگذاری تکراری آیتم‌ها در `get_by_id` به‌جای استفاده از `_attach_items` — `repositories.py:129-135`
- ۸ خط بیش از `line-length = 88` (بلندترین ۱۱۰ کاراکتر در `distribution_fault_decision_service.py:208`) — black روی این فایل‌ها اجرا نشده

---

## خلاصه تلاش

| فاز | موارد | تلاش تخمینی | تأثیر |
|---|---|---|---|
| ۱ — صحت داده | ۵ | ~۲ روز | بحرانی |
| ۲ — کارایی | ۵ | ~۲.۵ روز | زیاد |
| ۳ — معماری | ۶ | ~۳ روز | زیاد |
| ۴ — خوانایی | ۴ | ~۱ روز | متوسط |

**مسیر پیشنهادی:** موارد ۱، ۲، ۴، ۸ و اصلاح فوری ۱۶ (`exc_info=True`) در یک PR کوچک — مجموعاً کمتر از یک ساعت کار با ریسک نزدیک به صفر و پنج باگ واقعی برطرف‌شده. سپس فاز ۱ باقی‌مانده (۳ و ۵) که نیاز به بازبینی داده دارند.
