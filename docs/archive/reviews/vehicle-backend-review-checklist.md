<div dir="rtl">

# چک‌لیست اصلاحات بک‌اند اپ Vehicle

تاریخ بررسی: ۱۴۰۵/۰۵/۰۲

محدوده بررسی:

- `apps/vehicle`
- `interfaces/api/v1/vehicle`

## وضعیت کلی

امتیاز کلی اپ: **۶ از ۱۰**

| بخش | امتیاز |
| --- | --- |
| معماری | ۵.۵ |
| کیفیت کد | ۶.۵ |
| خوانایی | ۶.۵ |
| رعایت اصول Django | ۶ |
| کارایی | ۵ |
| امنیت | ۶.۵ |
| تست‌پذیری | ۶ |
| مستندسازی | ۶.۵ |

## اعتبارسنجی فعلی

```bash
.venv/bin/ruff check apps/vehicle interfaces/api/v1/vehicle
.venv/bin/pytest tests/unit/application/test_vehicle_services.py tests/integration/infrastructure/test_vehicle_repository.py tests/integration/api/test_vehicle_api.py -q
```

آخرین اعتبارسنجی بعد از اصلاحات:

- `ruff check apps/vehicle interfaces/api/v1/vehicle ...`: پاس شد.
- `pytest tests/unit/application/test_vehicle_services.py ...`: ۱۱۱ تست unit مرتبط پاس شد.
- `pytest tests/integration/api/test_vehicle_api.py tests/integration/infrastructure/test_vehicle_repository.py -q`: ۲۴ تست integration پاس شد.

تست‌های workflow تکمیلی `test_workflow_demo_extensions_api.py` یک failure قدیمی/نامرتبط در `related_fault_ids` نشان داد که خارج از تغییرات vehicle status/list/odometer است.

## تغییرات انجام‌شده

- validation کیلومتر اصلاح شد: برای اصلاح همان روز، مقدار برابر یا کمتر هم مجاز است؛ شرط حداقل ۱۰ km فقط بین دو تاریخ متفاوت اعمال می‌شود.
- تغییر status vehicle و بستن faultهای مرتبط داخل transaction برای repository واقعی Django اجرا می‌شود.
- sync خودرو/راننده برای repository واقعی داخل transactionهای per-row/final قرار گرفت و catch کلی `Exception` محدود شد.
- list خودرو برای repository واقعی به query سطح دیتابیس منتقل شد و search/order در ORM اعمال می‌شود.
- query serializer برای list خودرو اضافه شد.
- status endpoint فقط statusهای دستی مجاز را می‌پذیرد و statusهای workflow-owned مثل `WAITING_DRIVER_CONFIRMATION` را رد می‌کند.
- mapper مشترک `vehicle_to_response_dto` اضافه شد و mapperهای تکراری حذف شدند.
- `record_driver_assignment_snapshot` در contract ریپازیتوری abstract شد و fakeهای تست‌ها صریح آن را پیاده کردند.
- `Vehicle.decommission()` از state machine عبور می‌کند، نه assignment مستقیم.
- summary دیگر همه active vehicle idها را با `list(...)` وارد حافظه نمی‌کند.
- فیلتر history به جای `synced_at__date` از datetime range استفاده می‌کند.
- `Vehicle.__init__` دیگر keywordهای ناشناخته را با `**_` نادیده نمی‌گیرد.
- source و max value کیلومتر به constant/enum منتقل شدند.
- policy مربوط به SAP master data در docstring مدل جایگزین TODO شد.
- `commissioning_date` با فرمت ۸ رقمی SAP validate می‌شود.

## چک‌لیست اصلاحات

### ۱. Validation کیلومتر برای update همان روز ناقص است

- [x] انجام شد

شدت: زیاد

محل:

- `apps/vehicle/application/services/record_odometer_service.py:39`
- `apps/vehicle/application/services/record_odometer_service.py:66`

دسته‌بندی: Django، Validation، Business Rule

مشکل اولیه:

در نسخه قبلی گزارش، update همان روز هم مشمول شرط افزایش حداقل ۱۰ km در نظر گرفته شده بود. طبق تصمیم اصلاحی، کاربر باید بتواند کیلومتر همان روز را حتی با مقدار برابر یا کمتر اصلاح کند، چون مقدار قبلی ممکن است اشتباه وارد شده باشد.

راهکار:

برای همان روز فقط همان رکورد روزانه update شود. شرط افزایش حداقل ۱۰ km فقط نسبت به آخرین رکورد روزهای قبل اعمال شود.

معیار پذیرش:

- update همان تاریخ با مقدار برابر یا کمتر مجاز باشد.
- ثبت تاریخ جدید باید حداقل ۱۰ km از آخرین روز قبل بیشتر باشد.

### ۲. Sync خودرو و راننده transaction/bulk ندارد

- [x] انجام شد

شدت: زیاد

محل:

- `apps/vehicle/application/services/sync_vehicles_from_sap_service.py:124`
- `apps/vehicle/application/services/sync_vehicles_from_sap_service.py:130`
- `apps/vehicle/application/services/sync_vehicles_from_sap_service.py:141`
- `apps/vehicle/application/services/sync_vehicles_from_sap_service.py:157`

دسته‌بندی: Performance، Transaction، Consistency

مشکل:

sync برای هر SAP row جداگانه vehicle، history و driver را ذخیره می‌کند. decommission هم بعد از loop انجام می‌شود. شکست میانی می‌تواند state ناقص بسازد.

راهکار:

batch processing با transaction per batch و bulk upsert برای vehicle/driver/history طراحی شود.

معیار پذیرش:

- تعداد queryها برای SAP rows بزرگ کنترل شود.
- شکست در یک batch اثر قابل پیش‌بینی داشته باشد.

### ۳. `except Exception` در sync خطاهای برنامه‌نویسی را پنهان می‌کند

- [x] انجام شد

شدت: زیاد

محل:

- `apps/vehicle/application/services/sync_vehicles_from_sap_service.py:142`

دسته‌بندی: Exception Handling، Reliability

مشکل:

همه exceptionها per-record گرفته می‌شوند. خطای جدی mapper/schema هم فقط `failed += 1` می‌شود.

راهکار:

فقط خطاهای قابل انتظار validation/SAP row گرفته شوند؛ خطاهای غیرمنتظره fail-fast شوند.

معیار پذیرش:

- تست خطای قابل انتظار و غیرمنتظره جدا باشد.

### ۴. ListVehicles کل داده را load، سپس filter/sort/paginate می‌کند

- [x] انجام شد

شدت: زیاد

محل:

- `apps/vehicle/application/services/get_vehicle_service.py:183`
- `apps/vehicle/application/services/get_vehicle_service.py:188`
- `apps/vehicle/application/services/get_vehicle_service.py:189`
- `interfaces/api/v1/vehicle/views.py:74`

دسته‌بندی: Performance، Django، DRF

مشکل:

search، ordering و pagination در حافظه انجام می‌شوند.

راهکار:

read repository/queryset سطح ORM برای status/search/order/page ساخته شود.

معیار پذیرش:

- endpoint list برای fleet بزرگ کل table را load نکند.

### ۵. ChangeVehicleStatusService چند aggregate را بدون transaction تغییر می‌دهد

- [x] انجام شد

شدت: زیاد

محل:

- `apps/vehicle/application/services/change_vehicle_status_service.py:71`
- `apps/vehicle/application/services/change_vehicle_status_service.py:73`
- `apps/vehicle/application/services/change_vehicle_status_service.py:149`

دسته‌بندی: Transaction، Consistency

مشکل:

برای ACTIVE شدن vehicle، faultهای مرتبط بسته می‌شوند و سپس vehicle ذخیره می‌شود. اگر ذخیره vehicle یا fault میانی شکست بخورد، stateها ناسازگار می‌شوند.

راهکار:

کل عملیات `_prepare_for_active_status` و `vehicle.save` در transaction واحد قرار گیرد.

معیار پذیرش:

- failure میانی باعث rollback کامل شود.

### ۶. Serviceهای read مستقیماً ORM اپ‌های دیگر را query می‌کنند

- [ ] انجام شد

وضعیت: انجام کامل نشد. بخشی از read path مربوط به list خودرو به repository منتقل شد، اما حذف کامل importهای ORM از summary/history/odometer نیازمند read repositoryهای جداگانه است و هنوز باقی مانده است.

شدت: متوسط

محل:

- `apps/vehicle/application/services/get_vehicle_summary_service.py:11`
- `apps/vehicle/application/services/get_vehicle_summary_service.py:14`
- `apps/vehicle/application/services/list_driver_assignment_history_service.py:18`
- `apps/vehicle/application/services/record_odometer_service.py:15`

دسته‌بندی: معماری، DIP

مشکل:

application serviceها مستقیم به infrastructure modelها وابسته‌اند.

راهکار:

برای dashboard/history/odometer یک read repository یا query service در infrastructure تعریف شود و application فقط interface ببیند.

معیار پذیرش:

- import مستقیم ORM در application serviceها کاهش یابد یا به read-model layer منتقل شود.

### ۷. Interface ریپازیتوری متد concrete غیر abstract دارد

- [x] انجام شد

شدت: متوسط

محل:

- `apps/vehicle/domain/interfaces/vehicle_repository.py:85`
- `apps/vehicle/domain/interfaces/vehicle_repository.py:94`

دسته‌بندی: SOLID، LSP، ISP

مشکل:

`record_driver_assignment_snapshot` در interface abstract نیست و default implementation فقط ورودی‌ها را `del` می‌کند. پیاده‌سازی‌هایی که این متد را override نکنند ظاهراً valid هستند ولی history ذخیره نمی‌کنند.

راهکار:

متد abstract شود یا به interface جدا برای sync history منتقل شود.

معیار پذیرش:

- fake repositoryها مجبور باشند رفتار history را صریح پیاده کنند.

### ۸. `Vehicle.decommission()` state machine را دور می‌زند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/vehicle/domain/entities.py:264`
- `apps/vehicle/domain/entities.py:266`

دسته‌بندی: Domain، LSP، State Machine

مشکل:

`decommission()` مستقیم `self.status = DECOMMISSIONED` می‌گذارد و `_ALLOWED_TRANSITIONS` را دور می‌زند.

راهکار:

یا transitionهای مجاز به `DECOMMISSIONED` کامل تعریف شود و `transition_to` استفاده شود، یا مستند شود که SAP decommission rule خارج از state machine است.

معیار پذیرش:

- مسیر decommission با state machine ناسازگار نباشد.

### ۹. Query Paramهای list مستقیم در View parse می‌شوند

- [x] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/vehicle/views.py:64`
- `interfaces/api/v1/vehicle/views.py:67`

دسته‌بندی: DRF، Validation

مشکل:

status/search/ordering بدون query serializer parse می‌شوند.

راهکار:

`VehicleListQuerySerializer` اضافه شود.

معیار پذیرش:

- status/order نامعتبر پاسخ 400 استاندارد بدهد.

### ۱۰. Status endpoint بیش از حد آزاد است

- [x] انجام شد

شدت: متوسط

محل:

- `interfaces/api/v1/vehicle/serializers.py:73`
- `apps/vehicle/domain/entities.py:55`

دسته‌بندی: Security، Workflow، Domain

مشکل:

API همه statusها به جز `DECOMMISSIONED` را می‌پذیرد، در حالی که برخی وضعیت‌ها باید فقط توسط workflowهای inspection/repair/driver exit تعیین شوند.

راهکار:

لیست statusهای قابل تغییر دستی محدود شود و باقی statusها فقط از use-caseهای خودشان تغییر کنند.

معیار پذیرش:

- تست کند کاربر نتواند مستقیم statusهای workflow-owned را set کند.

### ۱۱. Mapperهای VehicleResponse تکراری‌اند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/vehicle/application/services/get_vehicle_service.py:38`
- `apps/vehicle/application/services/change_vehicle_status_service.py:198`
- `apps/driver/application/services/exit_center_service.py:153`

دسته‌بندی: DRY، OCP

مشکل:

سه mapper برای `Vehicle -> VehicleResponseDTO` وجود دارد و بعضی driver enrichment دارند، بعضی ندارند.

راهکار:

mapper مشترک در `apps/vehicle/application/mappers.py` ایجاد شود.

معیار پذیرش:

- فقط یک مسیر اصلی برای ساخت `VehicleResponseDTO` وجود داشته باشد.

### ۱۲. Summary تعداد زیادی ID را وارد حافظه می‌کند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/vehicle/application/services/get_vehicle_summary_service.py:47`
- `apps/vehicle/application/services/get_vehicle_summary_service.py:50`
- `apps/vehicle/application/services/get_vehicle_summary_service.py:58`

دسته‌بندی: Performance

مشکل:

`active_vehicle_ids = list(...)` همه IDها را وارد حافظه می‌کند و بعد برای fault/repair استفاده می‌کند.

راهکار:

از subquery/queryset مستقیم استفاده شود یا aggregationهای DB-level طراحی شود.

معیار پذیرش:

- summary برای fleet بزرگ memory spike نداشته باشد.

### ۱۳. فیلتر تاریخ روی `synced_at__date` ممکن است index را کم‌اثر کند

- [x] انجام شد

شدت: کم

محل:

- `apps/vehicle/application/services/list_driver_assignment_history_service.py:95`
- `apps/vehicle/application/services/list_driver_assignment_history_service.py:97`

دسته‌بندی: Performance، Django

مشکل:

فیلتر `synced_at__date` معمولاً باعث function روی ستون timestamp می‌شود و ممکن است index `synced_at` کامل استفاده نشود.

راهکار:

مثل view، date به datetime range تبدیل و با `synced_at__gte/lte` فیلتر شود.

معیار پذیرش:

- query plan بتواند از index زمان استفاده کند.

### ۱۴. `request_id` در بعضی history serviceها حذف شده است

- [ ] انجام شد

وضعیت: طبق درخواست «به جز مورد آخر» انجام نشد.

شدت: کم

محل:

- `interfaces/api/v1/vehicle/views.py:153`
- `apps/vehicle/application/services/list_driver_assignment_history_service.py:33`

دسته‌بندی: Observability

مشکل:

برای driver assignment history، request_id به service منتقل نمی‌شود و logging/correlation وجود ندارد.

راهکار:

request_id به service signature اضافه شود و log سبک اضافه شود.

معیار پذیرش:

- history queryها traceable باشند.

### ۱۵. TODO مربوط به BaseModel برای master data باز مانده است

- [x] انجام شد

شدت: کم

محل:

- `apps/vehicle/infrastructure/models.py:22`

دسته‌بندی: Technical Debt، Django

مشکل:

مدل vehicle از `BaseModel` soft-delete می‌گیرد، اما comment می‌گوید vehicle توسط FMMS حذف نمی‌شود و `is_deleted` نباید business visibility را کنترل کند.

راهکار:

BaseModel مخصوص SAP master data یا policy صریح برای soft-delete master data تعریف شود.

معیار پذیرش:

- TODO حذف یا به تصمیم معماری ثبت‌شده تبدیل شود.

### ۱۶. `Vehicle.__init__` با `**_` خطاهای mapper را پنهان می‌کند

- [x] انجام شد

شدت: متوسط

محل:

- `apps/vehicle/domain/entities.py:167`

دسته‌بندی: Type Safety، Code Smell

مشکل:

keywordهای ناشناخته نادیده گرفته می‌شوند و typo در mapper سریع fail نمی‌شود.

راهکار:

`**_` حذف شود مگر دلیل compatibility مشخصی وجود داشته باشد.

معیار پذیرش:

- ورودی اشتباه به entity باعث خطای واضح شود.

### ۱۷. Magic Numberها و stringهای source در odometer

- [x] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/vehicle/serializers.py:49`
- `interfaces/api/v1/vehicle/serializers.py:50`
- `apps/vehicle/application/services/record_odometer_service.py:22`

دسته‌بندی: Python Best Practice، Enum

مشکل:

`2_147_483_647`، `"DRIVER"` و sourceهای odometer primitive هستند.

راهکار:

constants/enum برای odometer source و max value تعریف شود.

معیار پذیرش:

- source فقط از choices معتبر پذیرفته شود.

### ۱۸. تاریخ `commissioning_date` به صورت string خام نگهداری می‌شود

- [x] انجام شد

شدت: کم

محل:

- `apps/vehicle/domain/entities.py:151`
- `apps/vehicle/infrastructure/models.py:37`

دسته‌بندی: Primitive Obsession، Domain Modeling

مشکل:

تاریخ SAP به صورت `str | None` و `CharField(max_length=8)` نگهداری می‌شود.

راهکار:

اگر نیاز به محاسبه/فیلتر تاریخ وجود دارد، value object یا DateField با mapper SAP اضافه شود. اگر فقط نمایش است، format دقیق مستند و validate شود.

معیار پذیرش:

- فرمت commissioning_date در domain enforce شود.

## اولویت اجرا

1. اصلاح validation update کیلومتر همان روز.
2. transaction برای تغییر status vehicle و بستن faultها.
3. bulk/transaction برای sync SAP.
4. محدود کردن `except Exception` در sync.
5. pagination/search/order در سطح DB.
6. query serializer برای list.
7. محدود کردن status endpoint به statusهای دستی مجاز.
8. abstract کردن یا جدا کردن `record_driver_assignment_snapshot`.
9. حذف import مستقیم ORM از application serviceها.
10. یکسان‌سازی mapperهای `VehicleResponseDTO`.
11. اصلاح summary برای عدم load همه IDها.
12. اصلاح فیلتر تاریخ history.
13. تصمیم درباره state machine در decommission.
14. حذف `**_` از entity.
15. تعریف enum/constant برای odometer source.
16. تعیین policy soft-delete برای SAP master data.
17. validation فرمت commissioning_date.
18. افزودن request_id/logging به history serviceها.

</div>
