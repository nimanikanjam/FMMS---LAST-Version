<div dir="rtl">

# گزارش بررسی بک‌اند اپ خودرو

تاریخ: ۱۴۰۵/۰۴/۲۹

محدوده بررسی: اپ `vehicle` در بک‌اند، بعد از اتمام ریفکتور اپ `driver`.

## خلاصه

اپ خودرو تا حد زیادی به مسیر فاز ۱ نزدیک شده، اما هنوز چند بخش از منطق قدیمی دمو و CRUD دستی داخل آن باقی مانده است.

مهم‌ترین موارد:

- خودروهای حذف‌شده از SAP هنوز با `is_deleted=True` مخفی می‌شوند.
- ریپازیتوری خودرو هنوز متد `delete` دارد.
- تغییر وضعیت خودرو از API بیش از حد آزاد است.
- اعتبارسنجی کیلومتر برای آپدیت همان روز کامل نیست.
- sync تک‌خودرو احتمالا در فاز ۱ اضافه است.
- بعضی docstringها و نام‌گذاری‌ها هنوز قدیمی‌اند.

## ۱. وضعیت «از رده خارج» خودرو هنوز با `is_deleted` قاطی شده

فایل:

- `apps/vehicle/infrastructure/repositories.py`

رفتار فعلی:

متد `decommission_missing_from_sap()` وقتی خودرویی در خروجی SAP نیست، این کارها را انجام می‌دهد:

- `status = DECOMMISSIONED`
- `is_deleted = True`
- `deleted_at = now`

مشکل:

برای راننده تصمیم گرفتیم داده‌ای که از SAP می‌آید نباید با `is_deleted` از دید سیستم حذف شود. فقط باید status آن تغییر کند. اما خودرو هنوز برعکس این رفتار را دارد.

پیشنهاد:

برای خودرو هم مثل راننده عمل کنیم:

- رکورد در دیتابیس بماند.
- فقط `status = DECOMMISSIONED` شود.
- مقدار `is_deleted` تغییر نکند و `False` بماند.

نکته مرتبط:

در مدل خودرو، unique constraintهای `vehicle_number` و `license_plate` هنوز شرط `is_deleted=False` دارند. اگر قرار است `is_deleted` در منطق خودرو استفاده نشود، این constraintها هم باید بدون شرط شوند.

## ۲. ریپازیتوری خودرو هنوز delete دارد

فایل‌ها:

- `apps/vehicle/domain/interfaces/vehicle_repository.py`
- `apps/vehicle/infrastructure/repositories.py`
- `tests/integration/infrastructure/test_vehicle_repository.py`

رفتار فعلی:

- در interface متد `delete()` وجود دارد.
- در repository واقعی، `delete()` خودرو را soft-delete می‌کند.
- تست‌ها هم همین رفتار را تایید می‌کنند.

مشکل:

در فاز ۱، خودرو master data است و باید از SAP خوانده شود. FMMS نباید خودرو را حذف کند.

پیشنهاد:

حذف شود:

- `delete()` از `IVehicleRepository`
- `delete()` از `DjangoVehicleRepository`
- تست‌های soft-delete خودرو

باقی بماند:

- `decommission_missing_from_sap()`

## ۳. تغییر status خودرو از API خیلی آزاد است

فایل:

- `interfaces/api/v1/vehicle/views.py`

رفتار فعلی:

`PATCH /api/v1/vehicles/{id}/` هر مقدار موجود در `VehicleStatus` را قبول می‌کند.

مشکل:

یعنی کاربر می‌تواند مستقیم statusهایی مثل موارد زیر را تنظیم کند:

- `UNDER_REPAIR`
- `OUT_OF_SERVICE`
- `WAITING_DRIVER_CONFIRMATION`
- `DECOMMISSIONED`

در حالی که بعضی از این وضعیت‌ها باید توسط workflowهای خرابی، تعمیر، تحویل خودرو یا sync از SAP تعیین شوند.

نیاز به تصمیم:

باید مشخص کنیم کاربر در فاز ۱ مجاز است کدام statusها را دستی تغییر دهد.

پیشنهاد اولیه:

- `DECOMMISSIONED` فقط توسط sync از SAP تنظیم شود.
- statusهای مربوط به تعمیر و خرابی توسط workflowهای خودشان تغییر کنند.
- اگر تغییر دستی status لازم است، لیست مجاز آن محدود شود.

## ۴. اعتبارسنجی کیلومتر برای همان روز ناقص است

فایل:

- `apps/vehicle/application/services/record_odometer_service.py`

رفتار فعلی:

برای ثبت کیلومتر، فقط رکوردهای روزهای قبل بررسی می‌شوند. اگر برای همان روز قبلا رکورد وجود داشته باشد، مقدار قبلی همان روز در validation لحاظ نمی‌شود.

مثال مشکل:

- برای تاریخ `2026-07-15` قبلا مقدار `1015` ثبت شده.
- دوباره برای همان تاریخ مقدار `1000` ارسال می‌شود.

در حال حاضر ممکن است این مقدار قبول شود، چون فقط روزهای قبل بررسی می‌شوند.

نیازمندی شما:

وقتی رکورد همان روز update می‌شود:

- کیلومتر جدید نباید از مقدار قبلی کمتر باشد.
- باید حداقل ۱۰ کیلومتر بیشتر از مقدار قبلی باشد.

پیشنهاد:

قبل از update همان روز، رکورد موجود همان روز هم خوانده شود و قانون افزایش حداقل ۱۰ کیلومتر روی آن اعمال شود.

## ۵. sync تک‌خودرو احتمالا در فاز ۱ اضافه است

فایل‌ها:

- `apps/vehicle/application/services/sync_sap_equipment_service.py`
- `interfaces/api/v1/deps.py`
- `infrastructure/messaging/tasks/sap_sync_tasks.py`
- تست‌های مرتبط

رفتار فعلی:

دو نوع sync داریم:

- sync زمان‌بندی‌شده کل خودروها
- sync یک خودرو بر اساس `VehicleNumber`

مشکل:

نیازمندی فاز ۱ sync زمان‌بندی‌شده خودروها از SAP است. sync تک‌خودرو شاید اضافه باشد.

نیاز به تصمیم:

آیا sync تک‌خودرو در فاز ۱ لازم است یا نه؟

اگر لازم نیست، پیشنهاد حذف:

- `SyncSAPEquipmentService`
- `get_sync_sap_equipment_service()`
- task مربوط به `sync_equipment_from_sap`
- تست‌های sync تک‌خودرو

باقی بماند:

- `SyncVehiclesFromSAPService`
- task زمان‌بندی‌شده `sync_vehicles_from_sap`
- management command برای اجرای دستی توسط ادمین سیستم، اگر لازم است

## ۶. بعضی docstringها و نام‌گذاری‌ها قدیمی‌اند

نمونه‌ها:

- `VehicleAlreadyExistsError` هنوز درباره ثبت دستی خودرو صحبت می‌کند.
- بعضی متن‌ها هنوز بین `equipment_number`، `sap_equipment` و `vehicle_number` جابه‌جا هستند.
- بعضی تست‌ها هنوز اسم‌های مرتبط با رفتار دمو دارند.

پیشنهاد:

نام‌گذاری را با فیلدهای SAP یکدست کنیم:

- `VehicleNumber`
- `LicensePlate`
- `CommissioningDate`
- `Driver1CustomerNo`
- `Driver2CustomerNo`

## ۷. فایل export سرویس‌ها مرتب نیست

فایل:

- `apps/vehicle/application/services/__init__.py`

وضعیت فعلی:

- `SyncSAPEquipmentService` export شده.
- `ActivateVehicleService` export نشده.
- `SyncVehiclesFromSAPService` export نشده.

مشکل:

این فایل سطح واقعی سرویس‌های فاز ۱ را درست نشان نمی‌دهد.

پیشنهاد:

بعد از تصمیم درباره sync تک‌خودرو، این فایل تمیز شود و فقط سرویس‌های فعال را export کند.

## ترتیب پیشنهادی تصمیم‌گیری

۱. اول تصمیم بگیریم خودرو هم مثل راننده از `is_deleted` برای منطق business استفاده نکند یا نه.

۲. اگر پاسخ مثبت است، `delete()` خودرو حذف شود و constraintها و تست‌ها اصلاح شوند.

۳. validation کیلومتر برای آپدیت همان روز اصلاح شود.

۴. مشخص شود کدام statusهای خودرو قابل تغییر دستی هستند.

۵. مشخص شود sync تک‌خودرو در فاز ۱ لازم است یا حذف شود.

۶. docstringها، نام‌گذاری‌ها، exportها و تست‌های قدیمی تمیز شوند.

</div>