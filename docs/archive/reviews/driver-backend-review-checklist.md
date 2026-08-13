<div dir="rtl">

# چک‌لیست اصلاحات بک‌اند اپ Driver

تاریخ بررسی: ۱۴۰۵/۰۵/۰۲

محدوده بررسی:

- `apps/driver`
- `interfaces/api/v1/driver`

## وضعیت کلی

امتیاز کلی اپ: **۶.۵ از ۱۰**

| بخش | امتیاز |
| --- | --- |
| معماری | ۶ |
| کیفیت کد | ۷ |
| خوانایی | ۷ |
| رعایت اصول Django | ۶.۵ |
| کارایی | ۵.۵ |
| امنیت | ۷ |
| تست‌پذیری | ۶.۵ |
| مستندسازی | ۷ |

## اعتبارسنجی فعلی

```bash
.venv/bin/ruff check apps/driver interfaces/api/v1/driver
.venv/bin/pytest tests/unit/application/test_driver_services.py tests/integration/infrastructure/test_driver_repository.py tests/integration/api/test_driver_api.py -q
```

در زمان بررسی پاس شد: ۲۷ تست. یک warning مربوط به teardown دیتابیس تست دیده شد.

آخرین اعتبارسنجی بعد از اصلاحات:

- `ruff check apps/driver interfaces/api/v1/driver interfaces/api/v1/deps.py ...`: پاس شد.
- `pytest tests/unit/application/test_driver_services.py tests/integration/infrastructure/test_driver_repository.py tests/integration/api/test_driver_api.py -q`: ۲۸ تست پاس شد.

## تغییرات انجام‌شده

- `DriverListQuerySerializer` برای validation پارامترهای `status`، `ordering`، `search` و `role` اضافه شد.
- search و ordering برای repository واقعی Django به query سطح ORM منتقل شد.
- فیلتر role از View حذف و داخل `ListDriversService` اعمال شد.
- وابستگی مستقیم application service به `VehicleModel` حذف و `IDriverVehicleAssignmentReader`/`DjangoDriverVehicleAssignmentReader` اضافه شد.
- summary service به `IDriverSummaryReader` وابسته شد و ORM summary به infrastructure منتقل شد.
- `Driver.__init__` دیگر keyword ناشناخته را با `**_` نادیده نمی‌گیرد.
- role filter به `DriverAssignmentRole` تبدیل شد و schema/serializer از choices مشترک استفاده می‌کنند.
- duplicate current assignment رفتار صریح دارد: بر اساس `updated_at` جدیدترین vehicle انتخاب می‌شود و assignmentهای تکراری warning log می‌شوند.
- `requested_by` در DTO خروج از مرکز به `requested_by_user_id` تغییر کرد و مستند شد که فقط برای structured logging استفاده می‌شود.
- docstring package service با نقش orchestration/workflow هماهنگ شد.

## چک‌لیست اصلاحات

### ۱. انتقال Search و Role Filter از View به Query Service/Repository

- [x] انجام شد

شدت: زیاد

محل:

- `interfaces/api/v1/driver/views.py:36`
- `interfaces/api/v1/driver/views.py:59`
- `interfaces/api/v1/driver/views.py:106`
- `interfaces/api/v1/driver/views.py:108`

دسته‌بندی: معماری، Fat View، DRY

مشکل:

منطق search و role filtering داخل view نوشته شده است. view باید request/response را مدیریت کند، نه business/query filtering را.

راهکار:

Query params در serializer validate شود و فیلترها به `ListDriversService` یا read repository منتقل شوند.

معیار پذیرش:

- view فقط serializer، service call و response بسازد.
- تست‌های list/search/role همچنان پاس بمانند.

### ۲. Pagination و Sorting بعد از Load کامل داده انجام می‌شود

- [ ] انجام کامل نشد

وضعیت: search و ordering برای repository واقعی Django در سطح ORM انجام می‌شود، اما pagination هنوز با `paginate_dto_list` بعد از ساخت لیست DTO انجام می‌شود. پیاده‌سازی pagination واقعی دیتابیس نیازمند تغییر contract سرویس list برای دریافت page/page_size و برگرداندن count است.

شدت: زیاد

محل:

- `apps/driver/application/services/get_driver_service.py:221`
- `apps/driver/application/services/get_driver_service.py:222`
- `interfaces/api/v1/driver/views.py:109`

دسته‌بندی: Performance، Django، DRF

مشکل:

`list_all()` یا `list_by_status()` کل driverها را load می‌کند، بعد در Python sort/filter/paginate انجام می‌شود.

راهکار:

read repository باید search/order/pagination را در ORM انجام دهد.

معیار پذیرش:

- endpoint list برای fleet بزرگ کل table را در حافظه load نکند.

### ۳. وابستگی مستقیم Driver Service به ORM مدل Vehicle

- [x] انجام شد

شدت: متوسط

محل:

- `apps/driver/application/services/get_driver_service.py:19`
- `apps/driver/application/services/get_driver_service.py:98`

دسته‌بندی: معماری، DIP

مشکل:

Application service اپ driver مستقیم `VehicleModel` را query می‌کند. این وابستگی infrastructure اپ دیگر را وارد لایه application driver کرده است.

راهکار:

یک port/read model برای current vehicle assignment تعریف شود و implementation آن در infrastructure قرار گیرد.

معیار پذیرش:

- `apps/driver/application` هیچ import مستقیمی از `apps.vehicle.infrastructure.models` نداشته باشد.

### ۴. Summary Service مستقیماً ORM چند bounded context را می‌خواند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/driver/application/services/get_driver_summary_service.py:9`
- `apps/driver/application/services/get_driver_summary_service.py:10`
- `apps/driver/application/services/get_driver_summary_service.py:11`

دسته‌بندی: معماری، DIP، Query Service

مشکل:

summary service مستقیم `DriverModel`، `VehicleModel` و `SAPSyncRunItemModel` را query می‌کند.

راهکار:

اگر این read model عمداً برای dashboard است، آن را در infrastructure/query layer قرار دهید یا interfaceهای read-only تزریق کنید.

معیار پذیرش:

- وابستگی ORM از application service حذف یا به عنوان read model مستند شود.

### ۵. متد `Driver.__init__` با `**_` خطاهای mapper را پنهان می‌کند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/driver/domain/entities.py:68`

دسته‌بندی: Code Smell، Type Safety

مشکل:

`**_: object` هر keyword ناشناخته را silently نادیده می‌گیرد.

راهکار:

پارامترهای دقیق نگه داشته شوند و `**_` حذف شود، مگر compatibility migration مستند لازم باشد.

معیار پذیرش:

- typo در mapper باعث خطای سریع شود.

### ۶. Interface ریپازیتوری Driver بیش از حد پهن است

- [x] انجام شد

شدت: متوسط

محل:

- `apps/driver/domain/interfaces/driver_repository.py:12`

دسته‌بندی: SOLID، ISP

مشکل:

یک interface شامل read، list، save و SAP decommission است.

راهکار:

به reader/writer/sap-sync repository یا capability interfaceها تفکیک شود.

معیار پذیرش:

- سرویس read-only فقط به read interface وابسته باشد.

### ۷. استفاده از string خام برای role filter

- [x] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/driver/views.py:33`
- `interfaces/api/v1/driver/views.py:75`

دسته‌بندی: Primitive Obsession، Enum

مشکل:

نقش assignment با stringهای `"DRIVER"` و `"ASSISTANT"` کنترل می‌شود.

راهکار:

از enum یا TextChoices مشترک با مدل history vehicle استفاده شود.

اقدام انجام‌شده:

`DriverAssignmentRole` اضافه شد و `DRIVER_ROLE_CHOICES` در serializer/schema از همین enum ساخته می‌شود.

معیار پذیرش:

- role filter و schema از یک منبع مشترک choices استفاده کنند.

### ۸. Query برای current vehicle در صورت چند assignment فقط آخرین updated_at را انتخاب می‌کند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/driver/application/services/get_driver_service.py:98`
- `apps/driver/application/services/get_driver_service.py:104`
- `apps/driver/application/services/get_driver_service.py:113`

دسته‌بندی: Data Integrity، Code Smell

مشکل:

اگر یک driver همزمان روی چند vehicle باشد، سیستم با `order_by("-updated_at")` یکی را انتخاب می‌کند و مشکل داده را پنهان می‌کند.

راهکار:

یا constraint/rule تعریف شود که driver در هر role فقط یک vehicle جاری داشته باشد، یا API چند assignment را نشان دهد و inconsistency را گزارش کند.

اقدام انجام‌شده:

رفتار فعلی API صریح شد: در صورت duplicate، جدیدترین assignment بر اساس `updated_at` انتخاب می‌شود و assignmentهای دیگر با warning log می‌شوند. تست integration برای انتخاب deterministic vehicle جدیدتر اضافه شد.

معیار پذیرش:

- رفتار duplicate assignment صریح و تست‌شده باشد.

### ۹. `requested_by` در خروج از مرکز فقط log می‌شود

- [x] انجام شد

شدت: کم

محل:

- `apps/driver/application/dto/driver_dto.py:26`
- `apps/driver/application/services/exit_center_service.py:68`

دسته‌بندی: Auditability، Dead Field Risk

مشکل اولیه:

`requested_by` فقط در log آمده و روی audit/persistence/timeline اثری ندارد.

راهکار:

اگر audit لازم است در event/history ذخیره شود؛ اگر نه، نام/مستندات آن فقط به correlation/log محدود شود.

اقدام انجام‌شده:

نام فیلد به `requested_by_user_id` تغییر کرد و docstring DTO صریح کرد که این مقدار فقط برای structured logging است.

معیار پذیرش:

- کاربرد `requested_by` روشن و تست‌شده باشد.

### ۱۰. Docstring package با واقعیت serviceها هماهنگ نیست

- [x] انجام شد

شدت: کم

محل:

- `apps/driver/application/services/__init__.py:1`

دسته‌بندی: Docstring

مشکل:

docstring می‌گوید serviceها without business rules هستند، اما `DriverExitCenterService` ruleهای checklist و assignment را enforce می‌کند.

راهکار:

docstring به orchestration/workflow coordination تغییر کند.

معیار پذیرش:

- مستندات package با رفتار واقعی serviceها هماهنگ باشد.

### ۱۱. TODO معماری BaseModel برای master data باز مانده است

- [ ] انجام نشد، طبق دستور کاربر

شدت: کم

محل:

- `apps/driver/infrastructure/models.py:14`

دسته‌بندی: Technical Debt، Django

مشکل:

مدل driver از `BaseModel` فیلدهای soft-delete را می‌گیرد، در حالی که comment می‌گوید driver توسط FMMS حذف نمی‌شود.

راهکار:

تصمیم معماری master data گرفته شود: یا BaseModel مناسب SAP master data ساخته شود یا soft-delete در queryها کاملاً بی‌اثر/مستند بماند.

معیار پذیرش:

- TODO حذف یا به issue معماری مشخص تبدیل شود.

### ۱۲. نبود Query Serializer برای list

- [x] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/driver/views.py:96`
- `interfaces/api/v1/driver/views.py:100`

دسته‌بندی: DRF، Validation

مشکل:

status/order/search/role مستقیم از `request.query_params` خوانده و parse می‌شوند.

راهکار:

`DriverListQuerySerializer` اضافه شود.

اقدام انجام‌شده:

`DriverListQuerySerializer` اضافه شد و View دیگر `status`، `ordering`، `search` و `role` را مستقیم parse نمی‌کند.

معیار پذیرش:

- مقدار نامعتبر status/role/order پاسخ 400 استاندارد بدهد.

## اولویت اجرا

1. [x] انتقال search/role filter از view.
2. [ ] pagination واقعی در سطح دیتابیس. وضعیت فعلی: search/order در DB انجام شد، pagination هنوز روی لیست DTO است.
3. [x] حذف وابستگی application driver به `VehicleModel`.
4. [x] اصلاح summary service به read model/port.
5. [x] افزودن query serializer.
6. [x] تعیین rule duplicate vehicle assignment.
7. [x] حذف `**_` از entity.
8. [x] محدود کردن وابستگی serviceهای read به read interface/protocol.
9. [x] enum مشترک برای role filter.
10. [x] تعیین کاربرد audit برای `requested_by_user_id`.
11. [x] اصلاح docstring package.
12. [ ] تعیین تکلیف TODO مربوط به BaseModel. طبق دستور کاربر در این مرحله انجام نشد.

</div>
