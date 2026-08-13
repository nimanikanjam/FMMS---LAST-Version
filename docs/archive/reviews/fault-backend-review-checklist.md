<div dir="rtl">

# چک‌لیست اصلاحات بک‌اند اپ Fault

تاریخ بررسی: ۱۴۰۵/۰۵/۰۲

محدوده بررسی:

- `apps/fault`
- `interfaces/api/v1/fault`

نکته: این سند برای پیگیری مرحله‌ای ساخته شده است. هر مورد بعد از اصلاح و پاس شدن تست‌های مرتبط قابل تیک زدن است.

## وضعیت کلی

امتیاز کلی اپ: **۷ از ۱۰**

| بخش | امتیاز |
| --- | --- |
| معماری | ۷ |
| کیفیت کد | ۷.۵ |
| خوانایی | ۸ |
| رعایت اصول Django | ۷ |
| کارایی | ۶ |
| امنیت | ۶.۵ |
| تست‌پذیری | ۷ |
| مستندسازی | ۷ |

## دستورات پیشنهادی برای اعتبارسنجی

بعد از هر چند اصلاح، این دستورها اجرا شوند:

```bash
.venv/bin/ruff check apps/fault interfaces/api/v1/fault
.venv/bin/pytest tests/unit/application/test_fault_services.py tests/unit/application/test_fault_catalog_services.py tests/unit/domain/test_fault_domain.py tests/integration/infrastructure/test_fault_repository.py tests/integration/api/test_fault_api.py -q
```

در زمان بررسی، این دو دستور پاس شدند. اجرای کامل `mypy` به خطاهای خارج از اپ fault رسید و اجرای محدود هم به internal error در `django-stubs` برخورد.

آخرین اعتبارسنجی بعد از اصلاحات SAP:

- `ruff check apps/fault ... core/sap infrastructure/sap interfaces/api/v1/deps.py ...`: پاس شد.
- `pytest tests/unit/application/test_fault_services.py tests/unit/application/test_inspection_services.py tests/integration/api/test_fault_api.py tests/integration/api/test_inspection_api.py -q`: ۵۵ تست پاس شد.
- `pytest tests/unit/infrastructure/sap/test_pm_notification_adapter.py tests/unit/infrastructure/sap/test_vehicle_measurement_adapter.py tests/unit/infrastructure/sap/test_sap_retry_lifecycle.py tests/unit/infrastructure/messaging/test_retry_failed_sap_service.py -q`: ۱۷ تست پاس شد.

آخرین اعتبارسنجی بعد از اصلاحات صف خرابی واحد توزیع:

- `.venv/bin/ruff check apps/fault apps/integration core/sap infrastructure/sap interfaces/api/v1 tests/integration/api/test_fault_api.py tests/unit/infrastructure tests/unit/application`: پاس شد.
- `.venv/bin/pytest tests/integration/api/test_fault_api.py tests/unit/application/test_fault_services.py tests/unit/infrastructure/messaging/test_retry_failed_sap_service.py tests/unit/infrastructure/sap/test_sap_retry_lifecycle.py tests/unit/infrastructure/sap/test_vehicle_measurement_adapter.py tests/unit/infrastructure/sap/test_vehicle_assignment_adapter.py`: ۴۳ تست پاس شد.
- `npm run build` در `frontend`: پاس شد. فقط warning اندازه chunk از Vite گزارش شد.

## تغییرات انجام‌شده در این مرحله

- بعد از ثبت خرابی موردی، SAP PM Notification با `BAPI_ALM_NOTIF_CREATE` از مسیر `SAPTransactionManager` ساخته می‌شود.
- بعد از ثبت خرابی از checklist هم همان SAP PM Notification ساخته می‌شود.
- payload ایجاد notification با مشخصات SAP جدید هماهنگ شد: `NOTIF_TYPE="EM"`، `EQUIPMENT=VehicleNumber`، `DESCRIPT=شرح هدر`، و تاریخ‌های `STRMLFNDATE`/`DESSTDATE`.
- شماره `NOTIF_NO` موفق روی `fault.sap_notification_number` ذخیره می‌شود.
- برای آپدیت کیلومتر SAP، port و adapter جدید `VehicleMeasurementBAPIAdapter` با function module `MEASUREM_DOCUM_RFC_SINGLE_001` اضافه شد.
- آخرین odometer خودرو از read model جدا خوانده می‌شود و در صورت وجود، transaction جداگانه `MEASUREMENT_DOCUMENT` برای SAP ساخته می‌شود.
- retry service برای object typeهای `FAULT` و `MEASUREMENT_DOCUMENT` توسعه داده شد.
- endpoint لیست خرابی‌ها بدون filter حالا برای صف واحد توزیع، همه خرابی‌های ثبت‌شده را برمی‌گرداند.
- query paramهای لیست خرابی با `FaultListQuerySerializer` اعتبارسنجی می‌شوند.
- دو endpoint تصمیم واحد توزیع اضافه شد: `distribution-usable` و `distribution-unusable`.
- در تصمیم «خودرو قابل استفاده است»، خرابی بسته می‌شود، repair orderهای اولیه لغو می‌شوند و خودرو به `ACTIVE` برمی‌گردد تا راننده بتواند خروج را ادامه دهد.
- در تصمیم «خودرو قابل استفاده نیست»، خودرو `OUT_OF_SERVICE` می‌شود و درخواست تخصیص خودرو جایگزین از مسیر transaction قابل retry به SAP ثبت می‌شود.
- برای درخواست خودرو جایگزین SAP، port/dto/adapter/mock/test اضافه شد. نام function module فعلا placeholder است تا SAP API نهایی اعلام شود.
- صفحه فرانت `خرابی‌های توزیع` زیر منوی `توزیع خودرو` اضافه شد و فرم ثبت خرابی موردی به مسیر `/faults/new` منتقل شد.

## فاز ۱: یکپارچگی داده و Transaction

### ۰. ارسال PM Notification به SAP بعد از اعلام خرابی

- [x] انجام شد

شدت: بحرانی

محل:

- `apps/fault/application/services/report_fault_service.py`
- `apps/inspection/application/services/report_inspection_fault_service.py`
- `infrastructure/sap/adapters/bapi/pm_notification_bapi_adapter.py`
- `infrastructure/sap/adapters/bapi/vehicle_measurement_bapi_adapter.py`

مشکل:

اعلام خرابی، چه موردی و چه از checklist، باید در SAP به PM Notification تبدیل شود و آخرین کیلومتر خودرو هم برای SAP ارسال شود.

راهکار انجام‌شده:

PM Notification و measurement update از طریق SAP write gateway و transactionهای idempotent انجام می‌شوند. اگر SAP موفق باشد شماره notification روی fault ذخیره می‌شود. اگر measurement خوانده نشود، ثبت خرابی fail نمی‌شود و warning log ثبت می‌شود.

معیار پذیرش:

- خرابی موردی SAP PM Notification بسازد.
- خرابی checklist SAP PM Notification بسازد.
- payloadهای SAP با مشخصات اعلام‌شده توسط تیم SAP هماهنگ باشند.
- retry برای transactionهای fault notification و measurement فعال باشد.

### ۱. Transaction واحد برای ثبت Fault و تغییر وضعیت Vehicle

- [ ] انجام شد

شدت: زیاد

محل:

- `apps/fault/application/services/report_fault_service.py:147`
- `apps/fault/application/services/report_fault_service.py:152`

مشکل:

ثبت fault و تغییر وضعیت vehicle در دو repository جدا و بدون transaction واحد انجام می‌شود. اگر fault ذخیره شود اما ذخیره vehicle شکست بخورد، fault باز ثبت شده ولی vehicle ممکن است همچنان `ACTIVE` بماند.

راهکار:

کل عملیات `save(fault)` و `save(vehicle)` در یک transaction application-level یا Unit of Work قرار بگیرد.

نمونه:

```python
from django.db import transaction

with transaction.atomic():
    saved = self._fault_repo.save(fault)
    if vehicle.status == VehicleStatus.ACTIVE:
        vehicle.mark_under_repair()
        vehicle.updated_at = now
        self._vehicle_repo.save(vehicle)
```

معیار پذیرش:

- اگر ذخیره vehicle شکست بخورد، fault هم persist نشود.
- تست failure میانی اضافه شود.

### ۲. Transaction واحد برای بستن Fault و تغییر Repair Orderها

- [ ] انجام شد

شدت: زیاد

محل:

- `apps/fault/application/services/close_fault_service.py:104`
- `apps/fault/application/services/close_fault_service.py:108`

مشکل:

fault ابتدا بسته و ذخیره می‌شود، سپس repair orderهای مرتبط لغو یا تکمیل می‌شوند. اگر مرحله repair شکست بخورد، وضعیت fault و repair order از هم جدا می‌شود.

راهکار:

کل close flow در یک transaction قرار بگیرد یا orchestration service با Unit of Work ایجاد شود.

معیار پذیرش:

- شکست در ذخیره repair order باعث rollback شدن close fault شود.
- تست برای rollback اضافه شود.

### ۳. مدیریت کامل state آیتم‌های Fault در Repository

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/infrastructure/repositories.py:182`

مشکل:

`save()` آیتم‌های موجود در aggregate را upsert می‌کند، اما آیتم‌هایی که از `fault.items` حذف شده‌اند soft-delete نمی‌شوند. در نتیجه save نماینده state کامل aggregate نیست.

راهکار:

در زمان save، itemهای persisted با itemهای فعلی aggregate مقایسه شوند و itemهای حذف‌شده soft-delete شوند.

معیار پذیرش:

- اگر یک item از `fault.items` حذف شود و repository save شود، در `get_by_id` دوباره برنگردد.
- تست repository اضافه شود.

## فاز ۲: Performance و Query

### ۴. تبدیل Sync کاتالوگ SAP به Bulk Upsert

- [ ] انجام شد

شدت: زیاد

محل:

- `apps/fault/application/services/sync_fault_catalog_from_sap_service.py:100`
- `apps/fault/infrastructure/catalog_repositories.py:50`

مشکل:

برای هر row از SAP ابتدا `get_by_sap_key` و سپس `save/update_or_create` انجام می‌شود. برای N رکورد حداقل 2N query اجرا می‌شود.

راهکار:

Repository متد bulk داشته باشد. کلیدهای SAP یکجا خوانده شوند و سپس bulk create/update انجام شود.

معیار پذیرش:

- تعداد queryها نسبت به تعداد rowها خطی با ضریب پایین یا batch شود.
- تست sync برای created/updated/failed حفظ شود.

### ۵. Pagination واقعی در سطح دیتابیس

- [ ] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/fault/views.py:52`
- `interfaces/api/v1/fault/views.py:57`

مشکل:

سرویس کل لیست faultها را در حافظه برمی‌گرداند و pagination بعد از آن انجام می‌شود.

راهکار:

read repository یا query service پارامترهای pagination بگیرد و فقط همان page را از دیتابیس بخواند.

معیار پذیرش:

- endpoint list برای داده زیاد، همه رکوردها را load نکند.
- تست pagination API حفظ یا اضافه شود.

### ۶. Batch کردن Enrichment پروفایل کاربران

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/application/services/get_fault_service.py:150`
- `apps/fault/application/services/report_fault_service.py:40`

مشکل:

در list faultها، `_to_response_dto` برای هر fault می‌تواند `profile_reader.get_profile` را جداگانه صدا بزند.

راهکار:

برای list، profileها به شکل bulk خوانده شوند یا enrichment به مرحله batch منتقل شود.

معیار پذیرش:

- برای لیست چند fault، تعداد lookup پروفایل به تعداد faultها وابسته مستقیم نباشد.

### ۷. افزودن Index برای Inspection

- [ ] انجام شد

شدت: کم

محل:

- `apps/fault/infrastructure/models.py:24`
- `apps/fault/infrastructure/repositories.py:165`

مشکل:

`list_by_inspection` با `inspection_id` و `is_deleted` filter می‌کند، اما index ترکیبی برای آن وجود ندارد.

راهکار:

Index زیر به `FaultModel.Meta.indexes` اضافه شود و migration ساخته شود:

```python
models.Index(
    fields=["inspection_id", "is_deleted"],
    name="fault_inspection_idx",
)
```

معیار پذیرش:

- migration جدید ایجاد شود.
- تست repository موجود پاس بماند.

## فاز ۳: Validation و استاندارد DRF

### ۸. تبدیل خطاهای Value Object به خطای استاندارد API

- [ ] انجام شد

شدت: زیاد

محل:

- `interfaces/api/v1/fault/serializers.py:15`
- `apps/fault/application/services/report_fault_service.py:136`

مشکل:

serializer فقط `max_length` را چک می‌کند، اما validation واقعی `FaultCode` در service رخ می‌دهد. خطای `ValueError` ممکن است به پاسخ غیر استاندارد تبدیل شود.

راهکار:

یا validation در serializer به DRF `ValidationError` تبدیل شود، یا exception handler مشترک برای خطاهای value object اضافه شود.

نمونه:

```python
def validate_code(self, value: str) -> str:
    try:
        return str(FaultCode(value))
    except ValueError as exc:
        raise serializers.ValidationError(str(exc)) from exc
```

معیار پذیرش:

- ورودی code نامعتبر پاسخ 400 قابل پیش‌بینی بدهد.
- تست API اضافه شود.

### ۹. Serializer برای Query Paramهای لیست Fault

- [x] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/fault/views.py:50`
- `interfaces/api/v1/fault/views.py:51`

مشکل:

`vehicle_id` و `open_by_severity` مستقیم داخل view parse می‌شوند. ورودی UUID یا severity نامعتبر مسیر validation استاندارد DRF را طی نمی‌کند.

راهکار:

یک serializer برای query params ساخته شود.

راهکار انجام‌شده:

`FaultListQuerySerializer` در `interfaces/api/v1/fault/serializers.py` اضافه شد و `FaultViewSet.list` فقط از `validated_data` استفاده می‌کند. فیلترهای پشتیبانی‌شده فعلی `vehicle_id`، `status` و `open_by_severity` هستند.

معیار پذیرش:

- UUID نامعتبر پاسخ 400 بدهد.
- severity نامعتبر پاسخ 400 بدهد.

### ۱۰. تعیین رفتار صریح برای List بدون Filter یا Filter همزمان

- [x] انجام شد

شدت: متوسط

محل:

- `apps/fault/application/services/get_fault_service.py:131`
- `apps/fault/application/services/get_fault_service.py:136`

مشکل:

اگر filter ارسال نشود، خروجی `[]` است. اگر `vehicle_id` و severity همزمان ارسال شوند، vehicle اولویت دارد. این رفتار در API schema و validation صریح نیست.

راهکار:

یا query بدون filter را 400 کنید، یا endpoint list عمومی تعریف کنید. همچنین ارسال همزمان filterهای ناسازگار باید صریح validate شود.

راهکار انجام‌شده:

برای نیاز صف واحد توزیع، query بدون filter به عنوان list عمومی خرابی‌های ثبت‌شده تعریف شد. متد `IFaultRepository.list_all` و پیاده‌سازی Django آن اضافه شد و تست‌های service/API رفتار جدید را تثبیت کردند.

معیار پذیرش:

- رفتار مورد نظر در تست API تثبیت شود.

### ۱۱. استخراج Choiceهای Serializer

- [ ] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/fault/serializers.py:17`
- `interfaces/api/v1/fault/serializers.py:41`
- `interfaces/api/v1/fault/serializers.py:52`
- `interfaces/api/v1/fault/serializers.py:53`

مشکل:

ساخت choices برای `FaultSeverity` و `FaultStatus` چند بار تکرار شده است.

راهکار:

constants محلی تعریف شود:

```python
FAULT_SEVERITY_CHOICES = [item.value for item in FaultSeverity]
FAULT_STATUS_CHOICES = [item.value for item in FaultStatus]
```

معیار پذیرش:

- serializerها از constants مشترک استفاده کنند.

## فاز ۴: معماری و SOLID

### ۱۲. انتقال Mapper خصوصی به فایل مستقل

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/application/services/report_fault_service.py:34`
- `apps/fault/application/services/assign_fault_service.py:13`
- `apps/fault/application/services/close_fault_service.py:15`
- `apps/fault/application/services/get_fault_service.py:12`

مشکل:

`_to_response_dto` داخل `report_fault_service.py` است اما سرویس‌های دیگر آن را import می‌کنند. این coupling غیرطبیعی است.

راهکار:

Mapper به فایل مستقل مثل `apps/fault/application/mappers.py` منتقل شود.

معیار پذیرش:

- هیچ service دیگری mapper خصوصی فایل report را import نکند.

### ۱۳. کاهش وابستگی مستقیم Fault به Repair Application Internals

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/application/services/close_fault_service.py:17`
- `apps/fault/application/services/close_fault_service.py:20`
- `apps/fault/application/services/close_fault_service.py:23`

مشکل:

`CloseFaultService` به helper و service concrete از اپ repair وابسته است.

راهکار:

یک port/interface برای ثبت timeline یا اجرای command مربوط به repair تعریف و به fault تزریق شود.

معیار پذیرش:

- سرویس fault به implementation داخلی repair وابسته نباشد.
- تست سرویس fault با mock ساده‌تر شود.

### ۱۴. تفکیک Interface ریپازیتوری Fault طبق ISP

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/domain/interfaces/fault_repository.py:12`

مشکل:

`IFaultRepository` هم read دارد، هم write، هم existence check، هم delete. مصرف‌کننده‌های read-only به کل contract وابسته‌اند.

راهکار:

Interfaceها تفکیک شوند:

- `IFaultReader`
- `IFaultWriter`
- `IFaultOpenFlowChecker`

معیار پذیرش:

- سرویس‌های read-only فقط به reader وابسته باشند.

### ۱۵. جایگزینی Service Locator در View

- [ ] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/fault/views.py:40`
- `interfaces/api/v1/fault/views.py:76`
- `interfaces/api/v1/fault/views.py:99`

مشکل:

View مستقیماً از `interfaces.api.v1.deps` سرویس می‌گیرد. dependency graph پنهان می‌شود و تست واحد view سخت‌تر می‌شود.

راهکار:

برای ViewSet provider قابل override تعریف شود یا factory سطح کلاس داشته باشد.

معیار پذیرش:

- در تست بتوان سرویس‌ها را بدون patch کردن module-level deps تزریق کرد.

## فاز ۵: Domain Integrity و مدل داده

### ۱۶. تصمیم درباره ForeignKey برای FaultItem

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/infrastructure/models.py:52`

مشکل:

`FaultItemModel.fault_id` یک `UUIDField` ساده است. چون FaultItem child همین aggregate است، نبود ForeignKey می‌تواند orphan item ایجاد کند و ORM relation طبیعی را از بین ببرد.

راهکار:

اگر محدودیت معماری وجود ندارد، `ForeignKey` به `FaultModel` اضافه شود. اگر عمداً UUIDField می‌ماند، integrity checks و cleanup در repository صریح شود.

معیار پذیرش:

- امکان orphan شدن itemها یا با FK یا با تست/cleanup کنترل شود.

### ۱۷. افزودن Validation برای FaultCatalog

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/fault/domain/catalog_entities.py:10`

مشکل:

`FaultCatalog` فقط مجموعه‌ای از `str` خام است و invariant ندارد.

راهکار:

برای `code`, `code_group`, `defect_class` validation حداقلی در entity یا value object اضافه شود.

معیار پذیرش:

- داده خالی/نامعتبر SAP وارد cache نشود یا به عنوان failed ثبت شود.

### ۱۸. استفاده یا حذف `assigned_by`

- [ ] انجام شد

شدت: کم

محل:

- `apps/fault/application/dto/fault_dto.py:57`
- `apps/fault/application/services/assign_fault_service.py:31`

مشکل:

`assigned_by` در DTO وجود دارد اما در service هیچ اثری ندارد.

راهکار:

یا حذف شود، یا در logging/audit/timeline استفاده شود.

معیار پذیرش:

- هیچ فیلد ظاهراً audit-critical بدون مصرف باقی نماند.

## فاز ۶: Exception Handling و مستندسازی

### ۱۹. اصلاح Exception Handling در Sync

- [ ] انجام شد

شدت: زیاد

محل:

- `apps/fault/application/services/sync_fault_catalog_from_sap_service.py:106`

مشکل:

`except Exception` خطاهای غیرمنتظره را هم در آمار `failed` پنهان می‌کند.

راهکار:

فقط خطاهای قابل انتظار per-row گرفته شوند. خطاهای برنامه‌نویسی یا خطاهای ساختاری re-raise شوند.

معیار پذیرش:

- تست برای خطای قابل انتظار per-row وجود داشته باشد.
- خطای غیرمنتظره fail-fast شود.

### ۲۰. اصلاح Docstring نادرست Services Package

- [ ] انجام شد

شدت: کم

محل:

- `apps/fault/application/services/__init__.py:1`

مشکل:

docstring می‌گوید serviceها «without business rules» هستند، در حالی که serviceها orchestration و workflow rule دارند.

راهکار:

docstring به عبارت دقیق‌تر تغییر کند؛ مثلاً:

```python
"""Fault application services — orchestration and workflow coordination."""
```

معیار پذیرش:

- مستندات با رفتار واقعی serviceها هماهنگ باشد.

## مواردی که در بررسی مشکل قطعی نداشتند

- کلاس‌های اصلی domain/service/repository استفاده می‌شوند.
- import اضافه طبق `ruff` دیده نشد.
- mutable default argument دیده نشد.
- raw SQL و SQL injection دیده نشد.
- signal ناامن در محدوده fault دیده نشد.
- unreachable code و کد کامنت‌شده قابل حذف در sourceهای track‌شده دیده نشد.

</div>
