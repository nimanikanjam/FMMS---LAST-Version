<div dir="rtl">
# بررسی ارتباط بک‌اند FMMS با SAP


تاریخ بررسی: 2026-07-26

این سند بر اساس کد فعلی بک‌اند تهیه شده و فقط ارتباط‌های موجود در پروژه را گزارش می‌کند. مقادیر credential مثل username/password عمدا در سند آورده نشده‌اند.

## جمع‌بندی

بک‌اند دو نوع ارتباط SAP دارد:

1. **OData / HTTP GET** برای خواندن داده‌های مرجع و موجودی از SAP به FMMS.
2. **BAPI / RFC** برای نوشتن رخدادها و اسناد از FMMS به SAP.

همه writeهای SAP باید از مسیر `SAPTransactionManager` عبور کنند تا idempotency، retry، ذخیره payload/response و audit فنی در جدول `sap_transaction` انجام شود.

نکته مهم: در `interfaces/api/v1/deps.py` تابع `_sap_client()` برای writeها فقط `MockSAPClient` را برمی‌گرداند و اگر `SAP_USE_MOCK=False` باشد خطا می‌دهد. بنابراین در ترکیب فعلی API v1، **writeهای BAPI به SAP واقعی وصل نمی‌شوند** مگر اینکه composition root برای `SAPBAPIClient` اصلاح شود. اما readهای OData از طریق `_sap_odata_client()` در حالت `SAP_USE_MOCK=False` می‌توانند به SAP واقعی وصل شوند.

## تنظیمات اتصال

فایل اصلی تنظیمات SAP:

- `infrastructure/sap/config.py`

متغیرهای اصلی:

| متغیر | کاربرد |
| --- | --- |
| `SAP_USE_MOCK` | اگر `True` باشد همه ارتباط‌ها از `MockSAPClient` استفاده می‌کنند. مقدار پیش‌فرض `True` است. |
| `SAP_BASE_URL` | آدرس پایه OData، مثل `/sap/opu/odata/sap`. |
| `SAP_CLIENT` | mandant/client SAP. |
| `SAP_USERNAME` | کاربر فنی SAP. |
| `SAP_PASSWORD` | رمز کاربر فنی SAP. |
| `SAP_ASHOST` | host سرور RFC/BAPI. |
| `SAP_SYSNR` | شماره سیستم RFC/BAPI. |
| `SAP_LANG` | زبان logon. پیش‌فرض `EN`. |
| `SAP_TIMEOUT_SECONDS` | timeout ارتباط HTTP. پیش‌فرض 30 ثانیه. |
| `SAP_VERIFY_SSL` | فعال/غیرفعال بودن SSL verification. |

آدرس‌هایی که در پروژه دیده شد:

| منبع | مقدار |
| --- | --- |
| `docker-compose.sap-v2.yml` | `SAP_BASE_URL=http://ghsapsnd-app.gbgnetwork.net:8000/sap/opu/odata/sap` |
| `docker-compose.sap-v2.yml` | `SAP_ASHOST=GHSAP-APP1.gbgnetwork.net` |
| `.env` محلی | `SAP_BASE_URL=https://GHSAP-APP1.gbgnetwork.net:44301/sap/opu/odata/sap` |
| `.env` محلی | `SAP_ASHOST=GHSAP-APP1.gbgnetwork.net` |

Credentialها در `.env` وجود دارند، اما در این سند بازنشر نشده‌اند.

## کلاینت‌ها

| فایل | نقش | پروتکل |
| --- | --- | --- |
| `infrastructure/sap/client/odata_client.py` | اجرای `odata_get`، `odata_get_xml` و `odata_post` با `httpx`، Basic Auth و query `sap-client` | HTTP/OData |
| `infrastructure/sap/client/bapi_client.py` | اجرای `bapi_call` با `pyrfc` و سپس `BAPI_TRANSACTION_COMMIT` | RFC/BAPI |
| `infrastructure/sap/client/mock/mock_client.py` | داده و پاسخ mock برای dev/test | Mock |

فرمت URL برای OData:

```text
{SAP_BASE_URL}/{service}/{entity}?sap-client={SAP_CLIENT}&$format=json|xml
```

## ارتباط‌های OData فعال

این ارتباط‌ها در `RunSAPSyncService` اجرا می‌شوند و از مسیر داخلی زیر قابل trigger هستند:

- `POST /sap-sync/`
- Celery task: `fmms.sync_vehicles_from_sap`
- History: `GET /sap-sync/history/`

در `config/settings/base.py`، task خواندن SAP طبق `VEHICLE_SYNC_INTERVAL_HOURS` زمان‌بندی شده است. نام task قدیمی `sync_vehicles_from_sap` است، اما در عمل سرویس global sync را اجرا می‌کند و فقط خودرو نیست.

| دامنه FMMS | سرویس application | Adapter | SAP service / entity | نوع داده | مقصد محلی |
| --- | --- | --- | --- | --- | --- |
| Vehicle + Driver | `SyncVehiclesFromSAPService` | `VehicleDriverODataAdapter` | `ZC_VEHICLEDRIVER_CDS`، entity پیش‌فرض خالی | XML OData root feed | خودروها، راننده‌ها، snapshot تخصیص راننده |
| Inspection Template | `SyncInspectionTemplatesFromSAPService` | `ObjectPartCatalogODataAdapter` | پیش‌فرض config: `ZI_FLEET_CAT_B_CDS`، entity پیش‌فرض خالی | XML OData root feed | قالب‌های چک‌لیست |
| Fault Catalog | `SyncFaultCatalogFromSAPService` | `FaultCatalogODataAdapter` | `ZI_B_DEFECTCATALOG9_CDS`، entity پیش‌فرض خالی | XML OData root feed | کاتالوگ خرابی |
| Central Stock | `SyncCentralStockFromSAPService` | `CentralStockODataAdapter` | `ZI_STOCK_KH08_CDS`، entity پیش‌فرض خالی | XML OData root feed | موجودی انبار مرکزی قطعات |

متغیرهای قابل override برای OData:

| متغیر | پیش‌فرض |
| --- | --- |
| `SAP_VEHICLE_DRIVER_SERVICE` | `ZC_VEHICLEDRIVER_CDS` |
| `SAP_VEHICLE_DRIVER_ENTITY_SET` | خالی |
| `SAP_OBJECT_PART_CATALOG_SERVICE` | `ZI_FLEET_CAT_B_CDS` |
| `SAP_OBJECT_PART_CATALOG_ENTITY_SET` | خالی |
| `SAP_FAULT_CATALOG_SERVICE` | `ZI_B_DEFECTCATALOG9_CDS` |
| `SAP_FAULT_CATALOG_ENTITY_SET` | خالی |
| `SAP_CENTRAL_STOCK_SERVICE` | `ZI_STOCK_KH08_CDS` |
| `SAP_CENTRAL_STOCK_ENTITY_SET` | خالی |

## ارتباط‌های BAPI/RFC فعال در workflow

همه موارد زیر از `SAPTransactionManager` عبور می‌کنند و در `sap_transaction` ذخیره می‌شوند.

| رخداد FMMS | سرویس application | Adapter | Function Module | Object Type | Idempotency key |
| --- | --- | --- | --- | --- | --- |
| ثبت خرابی دستی | `ReportFaultService` | `PMNotificationBAPIAdapter` | `BAPI_ALM_NOTIF_CREATE` | `FAULT` | `fault-pm-notification:{fault_id}` |
| ثبت خرابی از چک‌لیست | `ReportInspectionFaultService` | `PMNotificationBAPIAdapter` | `BAPI_ALM_NOTIF_CREATE` | `FAULT` | `fault-pm-notification:{fault_id}` |
| ثبت کیلومتر در SAP بعد از خرابی | `ReportFaultService` / `ReportInspectionFaultService` | `VehicleMeasurementBAPIAdapter` | `MEASUREM_DOCUM_RFC_SINGLE_001` | `MEASUREMENT_DOCUMENT` | `fault-odometer-measurement:{fault_id}` |
| تایید خرابی توسط توزیع و درخواست خودروی جایگزین | `DistributionFaultDecisionService` | `VehicleAssignmentBAPIAdapter` | `ZFM_FLEET_ASSIGN_REPLACEMENT` | `VEHICLE_ASSIGNMENT` | `fault-replacement-assignment:{fault_id}` |
| sync درخواست تعمیر به SAP | `SyncRepairToSAPService` | `PMOrderBAPIAdapter` | `BAPI_ALM_ORDER_MAINTAIN` | `REPAIR_ORDER` | `repair-pm-order:{repair_order_id}` |
| ایجاد PM work order با اعلان SAP | `TriggerPMWorkOrderService` | `PMNotificationBAPIAdapter` | `BAPI_ALM_NOTIF_CREATE` | `PM_WORK_ORDER` | `pm-notification:{work_order_id}` |
| ارسال PR به SAP | `SubmitPRToSAPService` | `PurchaseRequisitionBAPIAdapter` | `BAPI_PR_CREATE` | `PURCHASE_REQUISITION` | `pr-submit:{pr_id}` یا مقدار ورودی |

## APIهای داخلی مرتبط با SAP

| API | متد | نقش |
| --- | --- | --- |
| `/sap-sync/` | `POST` | اجرای همه read syncهای OData. فقط admin. |
| `/sap-sync/history/` | `GET` | تاریخچه اجرای read syncها. supervisor به بالا. |
| `/sap-transactions/` | `GET` | لیست transactionهای SAP با filter اختیاری `status` و `object_type`. |
| `/sap-transactions/{id}/` | `GET` | جزئیات یک SAP transaction. |
| `/sap-transactions/summary/` | `GET` | شمارش transactionها برای داشبورد. |
| `/repair-orders/{id}/sync-sap/` | `POST` | ایجاد PM Order در SAP برای repair order. |
| `/purchase-requisitions/{id}/submit-sap/` | `POST` | ارسال PR به SAP. |
| `/purchase-orders/` | `POST` | دریافت/ثبت PO از SAP در FMMS؛ این endpoint خودش SAP را صدا نمی‌زند و payload را از caller می‌گیرد. |

علاوه بر APIهای بالا، ثبت خرابی و گزارش خرابی از inspection می‌توانند به صورت side-effect اعلان PM و measurement document در SAP ایجاد کنند، چون سرویس‌های مربوطه در `deps.py` با adapterهای SAP سیم‌کشی شده‌اند.

## SAPTransaction و retry

مدل‌های مرتبط:

- `apps/integration/domain/entities.py`
- `apps/integration/infrastructure/models.py`
- `apps/integration/infrastructure/repositories.py`
- `infrastructure/sap/transaction/sap_transaction_manager.py`

وضعیت‌ها:

- `PENDING`
- `IN_PROGRESS`
- `SUCCESS`
- `FAILED`
- `RETRYING`
- `EXHAUSTED`

task retry:

- `fmms.retry_failed_sap_transactions`
- فایل: `infrastructure/messaging/tasks/sap_retry_tasks.py`
- schedule در `config/settings/base.py`: هر 15 دقیقه

retry فقط برای object typeهای زیر adapter دارد:

- `PURCHASE_REQUISITION`
- `REPAIR_ORDER`
- `FAULT`
- `PM_WORK_ORDER`
- `MEASUREMENT_DOCUMENT`
- `VEHICLE_ASSIGNMENT`

برای `PURCHASE_ORDER`، `GOODS_RECEIPT` و `GOODS_ISSUE` در retry map فعلی adapter ثبت نشده است.

## Adapterهای موجود ولی فعلا در workflow/API سیم‌کشی نشده

این adapterها در کد وجود دارند، اما در `deps.py` یا workflowهای فعلی به صورت عملی استفاده نشده‌اند:

| Adapter | SAP ارتباط | وضعیت |
| --- | --- | --- |
| `MaterialODataAdapter` | `API_PRODUCT_SRV`، entityهای `A_Product` و `A_ProductPlant` | موجود ولی در sync فعلی استفاده نشده |
| `InventoryODataAdapter` | `API_MATERIAL_STOCK_SRV`، entity `MatlStkInAcctMod` | موجود ولی در sync فعلی استفاده نشده |
| `PurchaseOrderBAPIAdapter` | `BAPI_PO_CREATE1`، `BAPI_PO_APPROVE`، `BAPI_PO_GET_DETAIL` | موجود ولی در serviceهای فعلی استفاده نشده |
| `GoodsReceiptBAPIAdapter` | `BAPI_GOODSMVT_CREATE_GR`، `BAPI_GOODSMVT_CANCEL_GR` | موجود ولی در serviceهای فعلی استفاده نشده |
| `GoodsIssueBAPIAdapter` | `BAPI_GOODSMVT_CREATE_GI`، `BAPI_GOODSMVT_CANCEL_GI` | موجود ولی در serviceهای فعلی استفاده نشده |
| `ServicePOBAPIAdapter` | `BAPI_SERVICE_PO_CREATE`، `BAPI_SERVICE_PO_CONFIRM`، `BAPI_SERVICE_PO_GET` | موجود ولی در serviceهای فعلی استفاده نشده |

## نکات مهم و ریسک‌ها

1. **write واقعی SAP فعلا از API v1 فعال نیست.**
   در `interfaces/api/v1/deps.py`، تابع `_sap_client()` در صورت `SAP_USE_MOCK=False` خطا می‌دهد و فقط `MockSAPClient` برمی‌گرداند. برای BAPI واقعی باید `SAPBAPIClient` در composition root سیم‌کشی شود.

2. **دو مجموعه نام env برای SAP وجود دارد.**
   `infrastructure/sap/config.py` از `SAP_USERNAME`، `SAP_ASHOST`، `SAP_SYSNR` استفاده می‌کند؛ اما `config/settings/base.py` همچنین `SAP_USER`، `SAP_HOST` و `SAP_SYSTEM_ID` را هم می‌خواند. این ممکن است باعث ابهام operational شود.

3. **`docker-compose.sap-v2.yml` احتمالا syntax مشکل دارد.**
   انتهای service مقدار `},` دیده می‌شود که برای YAML معتبر نیست. اگر این فایل استفاده شود باید validate شود.

4. **کامنت compose به management command اشاره می‌کند که در سورس فعلی دیده نشد.**
   `docker-compose.sap-v2.yml` دستور `python manage.py sync_sap_vehicles` را پیشنهاد می‌کند، اما فایل command متناظر در سورس فعلی وجود ندارد. فقط pycache قدیمی دیده شد.

5. **نام Celery task خواندن SAP گمراه‌کننده است.**
   task با نام `sync_vehicles_from_sap` همه syncهای OData را اجرا می‌کند، نه فقط خودروها.

6. **Function Module خودروی جایگزین placeholder است.**
   `VehicleAssignmentBAPIAdapter` از `ZFM_FLEET_ASSIGN_REPLACEMENT` استفاده می‌کند و خود فایل نوشته که نام نهایی باید توسط تیم SAP تایید شود.

7. **External Workshop جدید هنوز SAP write مستقیم ندارد.**
   در workflow تعمیرگاه بیرونی فیلدهای `sap_purchase_order_number` و `sap_invoice_document_number` در مدل review وجود دارند، اما در سرویس فعلی ایجاد PO یا Invoice Document از SAP پیاده‌سازی نشده است.

## پیشنهادهای عملی

1. برای write واقعی، `deps.py` را به دو client جدا تغییر دهید:
   - `_sap_odata_client()` برای read
   - `_sap_bapi_client()` برای write

2. `SAPConfig` و `config/settings/base.py` را از نظر نام envها یکدست کنید.

3. adapterهای موجود اما استفاده‌نشده را یا به workflow وصل کنید یا در سند معماری به عنوان future adapter علامت بزنید.

4. برای External Workshop، سرویس جدا برای ثبت SAP PO و SAP Invoice Document طراحی شود و نتیجه در `ExternalRepairReview.sap_purchase_order_number` و `sap_invoice_document_number` ذخیره شود.

5. فایل `docker-compose.sap-v2.yml` و command قدیمی sync خودرو بازبینی شوند.

</div>