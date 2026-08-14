# راهنمای ارتباط FMMS با SAP

این سند هم برای آشنایی اولیه با SAP و هم برای دنبال کردن مسیر واقعی integration در کد فعلی نوشته شده است.

## ۱. مدل ذهنی ساده

SAP در این پروژه دو نقش دارد:

1. منبع اطلاعات پایه: خودرو، راننده، کاتالوگ و موجودی.
2. محل ایجاد اسناد رسمی: اعلان خرابی، سفارش تعمیر و درخواست خرید.

FMMS روی SAP جایگزین نمی‌شود؛ یک لایه عملیاتی با workflow ساده‌تر برای کاربران است.

```text
SAP --OData/read--> FMMS local cache
FMMS --BAPI/write--> SAP business documents
```

## ۲. اصطلاحات ضروری

| اصطلاح | کاربرد در FMMS |
|---|---|
| Client/Mandant | شناسه tenant منطقی SAP که همراه درخواست ارسال می‌شود |
| Equipment | نمایش SAP از تجهیز/خودرو |
| Customer/Personnel | شناسه‌های مرتبط با راننده یا پرسنل، بسته به مدل سازمان |
| Plant | سایت عملیاتی |
| Storage Location | محل موجودی، مانند انبار مرکزی قطعه |
| OData Service | endpoint HTTP برای query داده SAP |
| Entity Set | collection داخل OData service |
| Function Module/BAPI | عملیات تجاری SAP که از RFC فراخوانی می‌شود |
| Commit | بسیاری از BAPIها پس از موفقیت به `BAPI_TRANSACTION_COMMIT` نیاز دارند |
| Document Number | شناسه رسمی سند ایجادشده در SAP |

## ۳. لایه‌های کد SAP

```text
Application Service
  -> core/sap/ports                 قرارداد مستقل از SAP client
  -> infrastructure/sap/adapters    mapping دامنه به OData/BAPI
  -> infrastructure/sap/client      HTTP یا RFC transport
  -> SAP
```

فایل‌های شروع مطالعه:

1. `infrastructure/sap/config.py`
2. `infrastructure/sap/client/base.py`
3. `infrastructure/sap/client/odata_client.py`
4. `infrastructure/sap/client/bapi_client.py`
5. `infrastructure/sap/client/mock/`
6. `infrastructure/sap/adapters/odata/`
7. `infrastructure/sap/adapters/bapi/`
8. `infrastructure/sap/transaction/sap_transaction_manager.py`
9. `apps/integration/application/services/`
10. `infrastructure/messaging/tasks/`

## ۴. حالت Mock و Real

| تنظیم | معنی |
|---|---|
| `SAP_USE_MOCK=True` | OData و BAPI از MockSAPClient استفاده می‌کنند |
| `SAP_USE_MOCK=False` | OData واقعی فعال می‌شود و credentialهای لازم اجباری‌اند |
| `SAP_WRITE=True` | اجرای writeهای BAPI در manager مجاز است |
| `SAP_WRITE=False` | manager write را skip می‌کند؛ این رفتار برای workflowهایی که document number لازم دارند باید با دقت استفاده شود |

نکته مهم وضعیت فعلی: `_sap_odata_client()` می‌تواند `SAPODataClient` واقعی بسازد، ولی `_sap_client()` در composition root API فقط Mock را می‌پذیرد و هنگام `SAP_USE_MOCK=False` خطا می‌دهد. بنابراین wiring واقعی BAPI در API v1 هنوز تکمیل نشده است.

## ۵. OData Readهای فعال

| داده | Adapter | Service پیش‌فرض | مقصد محلی |
|---|---|---|---|
| خودرو و راننده | `VehicleDriverODataAdapter` | `ZC_VEHICLEDRIVER_CDS` | Vehicle، Driver و assignment history |
| آیتم بازرسی | `ObjectPartCatalogODataAdapter` | `ZI_FLEET_CAT_B_CDS` | InspectionTemplate |
| کاتالوگ خرابی | `FaultCatalogODataAdapter` | `ZI_FLEET_CAT_B_CDS` (همان Service آیتم بازرسی) | FaultCatalog |
| موجودی مرکزی | `CentralStockODataAdapter` | `ZI_STOCK_KH08_CDS` | CentralStock |

جریان خواندن:

```text
POST /api/v1/sap-sync/ یا Celery Beat
  -> RunSAPSyncService
  -> چهار sync service
  -> OData adapter
  -> OData client یا mock
  -> mapping و upsert محلی
  -> SAPSyncRun + SAPSyncRunItem
```

اجرای دستی sync فقط باید برای Admin باشد. history برای supervisorهای مجاز نمایش داده می‌شود.

## ۶. BAPI Writeهای متصل به workflow

| رخداد FMMS | Function Module | Object Type | Idempotency Key |
|---|---|---|---|
| ثبت خرابی | `BAPI_ALM_NOTIF_CREATE` | `FAULT` | `fault-pm-notification:{fault_id}` |
| ثبت کیلومتر مرتبط با خرابی | `MEASUREM_DOCUM_RFC_SINGLE_001` | `MEASUREMENT_DOCUMENT` | `fault-odometer-measurement:{fault_id}` |
| درخواست خودروی جایگزین | `ZFM_FLEET_ASSIGN_REPLACEMENT` | `VEHICLE_ASSIGNMENT` | `fault-replacement-assignment:{fault_id}` |
| ارسال تعمیر | `BAPI_ALM_ORDER_MAINTAIN` | `REPAIR_ORDER` | `repair-pm-order:{repair_order_id}` |
| اعلان PM | `BAPI_ALM_NOTIF_CREATE` | `PM_WORK_ORDER` | `pm-notification:{work_order_id}` |
| ارسال PR | `BAPI_PR_CREATE` | `PURCHASE_REQUISITION` | `pr-submit:{pr_id}` یا کلید ورودی |

Adapterهای بیشتری برای PO، Goods Receipt، Goods Issue و Service PO وجود دارند، ولی وجود adapter به معنی اتصال کامل آن به workflow/API نیست.

## ۷. SAPTransaction

هر write باید از `SAPTransactionManager` عبور کند:

```text
check idempotency key
  -> PENDING
  -> IN_PROGRESS
  -> call BAPI
  -> SUCCESS + response/document number
       یا
     FAILED + error
  -> periodic retry
  -> EXHAUSTED پس از پایان retry budget
```

فیلدهای مهم:

- `object_type`, `object_id`
- `idempotency_key`
- `status`, `retry_count`, `max_retries`
- `request_payload`, `response_payload`
- `sap_document_number`, `error_message`

این payloadها داده داخلی و بالقوه حساس‌اند و نباید برای هر کاربر احراز هویت‌شده نمایش داده شوند.

## ۸. ریسک‌های مهم فعلی

1. BAPI واقعی در composition root API سیم‌کشی نشده است.
2. idempotency check و claim worker در برابر concurrency کاملاً اتمیک نیست.
3. بعضی تماس‌های SAP داخل request/transaction طولانی اجرا می‌شوند.
4. retry برای برخی adapterهای موجود mapping ندارد.
5. payloadها باید redaction و permission محدود داشته باشند.
6. `SAP_WRITE=False` در بعضی workflowها پاسخ بدون document number می‌دهد و می‌تواند مسیر را به خطای 502 برساند.
7. credentialها فقط باید از secret manager/env دریافت شوند و هرگز در سند یا log نوشته نشوند.

جزئیات و اولویت اصلاح در [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md) آمده است.

## ۹. روش امن بررسی بدون SAP واقعی

1. `SAP_USE_MOCK=True` و `SAP_WRITE=True` را در محیط تست تثبیت کنید.
2. سناریوهای `SUCCESS`, `BAPI_ERROR`, `TRANSPORT_ERROR` و `DUPLICATE` را از mock اجرا کنید.
3. ابتدا یک read flow مانند sync خودرو را دنبال کنید.
4. سپس یک write flow مانند PM Notification یا PR را دنبال کنید.
5. در هر مرحله request payload، mapping، document number، status و retry را یادداشت کنید.
6. برای اتصال واقعی ابتدا فقط endpointهای read-only و محیط SAP غیرProduction بررسی شوند.

## ۱۰. چک‌لیست جلسه با تیم SAP

- محصول و نسخه: ECC یا S/4HANA؟
- محیط‌ها و Clientهای DEV/QAS/PRD چیست؟
- hostname، port، TLS و network route چیست؟
- OData serviceها publish و authorize شده‌اند؟
- service account چه roleهایی دارد؟
- RFC SDK و `pyrfc` در runtime قابل نصب است؟
- BAPIهای استاندارد/سفارشی دقیق و قرارداد ورودی/خروجی چیست؟
- commit/rollback هر BAPI چگونه است؟
- duplicate detection در SAP چگونه انجام می‌شود؟
- timeout و retry مجاز سازمان چیست؟
- چه داده‌هایی PII یا محرمانه محسوب می‌شوند؟
- monitoring و مسئول پاسخ‌گویی خطای SAP چه تیمی است؟

## ۱۱. Login آینده از طریق SAP

Login کاربر با service accountهای OData/BAPI متفاوت است و نباید با آن‌ها ترکیب شود.

ترتیب ترجیحی:

1. SAP IAS یا IdP سازمانی با OIDC
2. SAML در صورت الزام سازمان
3. سرویس authentication سفارشی SAP فقط اگر دو گزینه قبل ممکن نباشند

`personnel_number` شناسه اتصال کاربر به پروفایل عملیاتی است و برای مقادیر غیرخالی Unique می‌ماند. برای authentication باید یک `external_subject` یا `sap_user_id` پایدار و Unique جداگانه وجود داشته باشد. password SAP نباید در FMMS ذخیره شود.

## ۱۲. منابع خام

- `SAP_API_Field_Reference.xlsx`: مرجع گسترده API و فیلدها؛ همه ردیف‌ها الزاماً در FMMS استفاده نمی‌شوند.
- `odata/`: نمونه‌های خام سرویس‌ها؛ این پوشه نباید تغییر کند.
- `prototypes/sap_odata_test/`: کد آزمایشی و خارج از مسیر Production.

