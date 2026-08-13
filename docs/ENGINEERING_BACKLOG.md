# فهرست واحد ایرادها و برنامه اصلاح FMMS Backend

این فایل تنها مرجع فعال برای ایرادهای فنی Backend است. گزارش‌ها و checklistهای قدیمی در `archive/` سابقه بررسی‌اند و وضعیت جاری از این فایل تعیین می‌شود.

## ۱. قواعد وضعیت و اولویت

| مقدار | معنی |
|---|---|
| P0 | مانع Deploy یا ریسک امنیت/یکپارچگی بحرانی |
| P1 | لازم پیش از Pilot Production |
| P2 | بهبود مهم کیفیت، معماری یا مقیاس‌پذیری |
| P3 | پاک‌سازی و بهبود کم‌ریسک |
| Open | هنوز رفع و اعتبارسنجی نشده است |
| Done | اصلاح، تست و evidence ثبت شده است |
| Decision | پیش از کدنویسی نیازمند تصمیم معماری/کسب‌وکار است |

تاریخ baseline این تجمیع: 2026-08-13.

## ۲. خلاصه اجرایی

| اولویت | تعداد فعال | موضوع‌های اصلی |
|---|---:|---|
| P0 | 6 | migration، authorization، داده SAP، concurrency و upload |
| P1 | 12 | transaction، pagination، soft delete، test isolation، CI و wiring SAP |
| P2/P3 | 25+ | boundary معماری، query، typing، مستندسازی و پاک‌سازی appها |

تا زمان بسته شدن P0ها، Backend نباید Production-ready اعلام شود.

## ۳. P0 — موانع Production

### DEP-001 — جداسازی Provisioning دیتابیس از Runtime

- شدت: 🔴 Critical
- وضعیت: Done
- محل: `config/settings/base.py`، `config/wsgi.py`، `config/asgi.py`، `docker-compose.yml`
- تصمیم: PostgreSQL در Development و Production خارج از Django و Compose provision می‌شود. Runtime user مسئول `CREATE DATABASE` نیست.
- evidence:
  - bootstrap سفارشی و `ensure_database` حذف شده‌اند.
  - WSGI، ASGI و Celery startup هیچ provisioning یا migration اجرا نمی‌کنند.
  - Compose فقط از طریق `POSTGRES_*` به دیتابیس خارجی متصل می‌شود.
  - migration یک مرحله صریح و مستقل است.

### DEP-002 — Healthcheck به route ناموجود متصل است

- شدت: 🔴 Critical
- وضعیت: Open
- محل: `Dockerfile:55` و `config/urls.py`
- مشکل: `/api/health/` وجود ندارد و container پس از startup unhealthy می‌شود.
- معیار پذیرش:
  - liveness و readiness مشخص باشند.
  - liveness بدون authentication و وابستگی سنگین پاسخ دهد.
  - readiness وضعیت DB را بررسی کند.
  - Docker healthcheck تست شود.

### DB-001 — Drift مدل و migration

- شدت: 🔴 Critical
- وضعیت: Open
- محل: Authentication و CentralStock migrations/models
- تصمیم تثبیت‌شده: `FMMSUser.personnel_number` برای مقدار غیرخالی باید Unique بماند.
- مشکل: `makemigrations --check --dry-run` قصد حذف `unique_fmms_user_personnel_number` و تغییر فیلدهای CentralStock را دارد.
- راهکار:
  - constraint شرطی personnel number به `Meta.constraints` مدل برگردد.
  - drift فیلدهای CentralStock جداگانه بررسی شود.
  - migration تولیدی کورکورانه پذیرفته نشود.
- معیار پذیرش: `makemigrations --check --dry-run` بدون تغییر خروجی دهد و migration tests عبور کنند.

### SEC-001 — افشای payload تراکنش SAP

- شدت: 🔴 Critical
- وضعیت: Open
- محل: `interfaces/api/v1/integration/views.py` و serializer متناظر
- مشکل: هر کاربر احراز هویت‌شده می‌تواند request/response payload، error و idempotency key را مشاهده کند.
- معیار پذیرش:
  - detail فقط برای نقش مدیریتی تعریف‌شده قابل دسترس باشد.
  - serializer عمومی payload خام را برنگرداند.
  - redaction و تست authorization اضافه شود.
  - مشاهده جزئیات حساس audit شود.

### SEC-002 — نبود Object-Level Authorization برای Driver

- شدت: 🔴 Critical
- وضعیت: Open
- محل: handover و external workshop delivery/pickup
- مشکل: نقش DRIVER با UUID دلخواه می‌تواند روی assignment/handover متعلق به خودروی دیگر عمل کند.
- معیار پذیرش:
  - policy تعلق user -> personnel -> driver -> current vehicle وجود داشته باشد.
  - کنترل داخل application service نیز انجام شود.
  - تست IDOR/BOLA برای assignment دیگر اضافه شود.

### SAP-001 — Idempotency و retry در concurrency اتمیک نیست

- شدت: 🔴 Critical
- وضعیت: Open
- محل: `sap_transaction_manager.py` و integration repository
- مشکل: check و create idempotency در lock مشترک نیست و retry worker رکورد را claim نمی‌کند.
- معیار پذیرش:
  - رفتار درخواست‌های هم‌زمان مشخص و تست PostgreSQL داشته باشد.
  - `IntegrityError` ترجمه شود.
  - worker از claim اتمیک یا `select_for_update(skip_locked=True)` استفاده کند.
  - یک business event بیش از یک تماس مؤثر SAP ایجاد نکند.

### SEC-003 — Upload فاکتور بدون کنترل Production-grade

- شدت: 🟠 High، مانع Production
- وضعیت: Open
- محل: `_save_external_invoice_file` در Repair API
- مشکل: type، size، signature، نام امن، private storage و malware scan کنترل نشده‌اند.
- معیار پذیرش:
  - extension/MIME/signature whitelist شود.
  - محدودیت حجم در app و proxy وجود داشته باشد.
  - نام storage تصادفی باشد.
  - فایل private و دانلود آن authorization-aware باشد.
  - تست فایل نامعتبر/بزرگ اضافه شود.

## ۴. P1 — پایداری، امنیت و Performance

| شناسه | وضعیت | موضوع | محل/معیار کلیدی |
|---|---|---|---|
| TX-001 | Open | `ATOMIC_REQUESTS=True` هنگام تماس خارجی | transaction کوتاه؛ SAP I/O خارج از DB transaction |
| SAP-002 | Open | sync کامل SAP به‌صورت synchronous | enqueue در Celery و پاسخ `202 Accepted` |
| SAP-003 | Open | BAPI واقعی در composition root سیم‌کشی نشده | `SAPBAPIClient` امن و تست‌شده برای non-mock |
| SAP-004 | Open | retry map همه object typeها را پوشش نمی‌دهد | policy صریح retryable/non-retryable برای هر type |
| PERF-001 | Open | pagination بعد از load کل داده | DB-level pagination در Vehicle/Driver/Fault/Repair/SAP logs |
| PERF-002 | Open | external workshop list الگوی تقریبی `1 + 3N` دارد | read query با select_related/projection |
| DB-002 | Decision | cross-domain UUID در برابر FK | تصمیم جدا برای رابطه‌های critical و reconciliation |
| DB-003 | Open | soft-delete در همه queryها enforce نیست | manager پیش‌فرض + `all_objects` + visibility tests |
| DEP-003 | Open | Celery fallback به development settings | fail-fast یا production-safe settings |
| TEST-001 | Open | تست‌ها از `.env` و `SAP_WRITE` اثر می‌گیرند | test settings hermetic؛ اجرای عادی ۷۸۸ تست سبز |
| API-001 | Open | UUID نامعتبر ممکن است 500 شود | URL converter/helper و پاسخ 400 استاندارد |
| CI-001 | Open | CI و quality gates فعال وجود ندارد | lint/type/migration/test/deploy/schema/compose gates |

## ۵. P2 — کیفیت سراسری

| شناسه | وضعیت | موضوع | معیار پذیرش |
|---|---|---|---|
| ARCH-001 | Open | `interfaces/api/v1/deps.py` بیش از حد بزرگ است | composition به moduleهای domain/integration تقسیم شود |
| ARCH-002 | Open | Celery task از `interfaces.api.v1.deps` import می‌کند | composition مستقل از transport ایجاد شود |
| ARCH-003 | Open | Application بعضی ORMهای خود/دامنه دیگر را import می‌کند | query port/read model صریح |
| ARCH-004 | Open | import helper خصوصی بین appها | API عمومی application/domain یا shared policy |
| API-002 | Open | OpenAPI برای چند ViewSet ناقص است | schema بدون warning مهم تولید شود |
| API-003 | Open | serializer/filter contractها یکدست نیستند | query serializers و schema صریح |
| AUTH-001 | Open | Bulk profile reader وجود ندارد | batch reader برای جلوگیری از N+1 enrichment |
| AUTH-002 | Open | Current User مسیر application service ندارد | use case/reader مشخص برای `/me/` |
| AUTH-003 | Open | `/me/` فیلدهای `is_staff/is_superuser` می‌دهد | حذف یا justification و تست disclosure |
| AUTH-004 | Open | validation صریح role در manager ناقص است | enum/validation مرکزی |
| AUTH-005 | Open | تست‌های امنیتی auth محدودند | inactive، role abuse، token misuse و throttling |
| AUTH-006 | Decision | login آینده SAP/SSO | انتخاب IdP، protocol، external subject و role mapping |
| QUAL-001 | Open | Ruff چهار خطا دارد | zero violation |
| QUAL-002 | Open | mypy ۳۴ خطا در ۲۰ فایل دارد | zero error یا baseline موجه و نزولی |
| QUAL-003 | Open | dependency lock/hash وجود ندارد | build reproducible و vulnerability scan |
| OPS-001 | Open | upload/storage strategy تولیدی مشخص نیست | private object storage، retention و backup |
| OPS-002 | Open | runbook/monitoring کامل نیست | alert، dashboard و ownership برای DB/Redis/Celery/SAP |
| ADMIN-001 | Open | Admin عملیاتی فقط User را پوشش می‌دهد | read-only support views با permission/redaction |

## ۶. Backlog اپ Fault

این جدول موارد باز دو گزارش Fault را deduplicate می‌کند. اختلاف شماره خط باید هنگام شروع هر task با کد جاری دوباره بررسی شود.

| شناسه | اولویت | وضعیت | موضوع | معیار پذیرش خلاصه |
|---|---|---|---|---|
| FAULT-001 | P1 | Open | transaction واحد برای report/decision/close | rollback scenario tests؛ SAP با boundary روشن |
| FAULT-002 | P1 | Open | یک جریان باز برای هر خودرو در concurrency | constraint/lock + migration data audit |
| FAULT-003 | P1 | Open | guard ناقص `mark_usable` | فقط state مجاز قابل بسته شدن باشد |
| FAULT-004 | P1 | Open | پاسخ کهنه `mark_usable` | note ذخیره‌شده در پاسخ بازگردد |
| FAULT-005 | P1 | Open | `FaultCode._PATTERN` باید `ClassVar` باشد | invalid code با override تصادفی عبور نکند |
| FAULT-006 | P1 | Open | N+1 پروفایل کاربر | bulk profile reader و query-count test |
| FAULT-007 | P1 | Open | pagination واقعی | limit/offset یا page abstraction در repository |
| FAULT-008 | P2 | Open | sync catalog دو query برای هر row | bulk upsert با conflict policy |
| FAULT-009 | P2 | Open | index مرتب‌سازی `reported_at` | migration + query plan مناسب |
| FAULT-010 | P2 | Open | state کامل FaultItem هنگام save | create/update/remove semantics و تست aggregate |
| FAULT-011 | P2 | Open | ValueObject error به API استاندارد ترجمه نمی‌شود | پاسخ validation کنترل‌شده |
| FAULT-012 | P2 | Open | Choiceهای serializer تکراری/خام | enum/choice مشترک |
| FAULT-013 | P2 | Open | mapper خصوصی در چند module مصرف می‌شود | mapper عمومی مستقل |
| FAULT-014 | P2 | Open | وابستگی به internals اپ Repair | port/facade عمومی |
| FAULT-015 | P2 | Open | repository interface پهن | ISP بر اساس use case |
| FAULT-016 | P2 | Open | Service Locator در View | dependency composition قابل تست |
| FAULT-017 | P2 | Decision | رابطه FaultItem | FK داخلی aggregate یا UUID با constraint روشن |
| FAULT-018 | P2 | Open | validation کاتالوگ | field/domain validation و invalid-row policy |
| FAULT-019 | P2 | Open | `assigned_by` و `sap_defect_code` نیمه‌کاره | استفاده واقعی یا حذف کنترل‌شده |
| FAULT-020 | P2 | Open | وضعیت sync SAP روی Fault مشخص نیست | PENDING/SYNCED/FAILED یا reliance صریح بر transaction |
| FAULT-021 | P3 | Open | timestamp، docstring، متن فارسی و dead code | cleanup بدون تغییر رفتار + tests |

## ۷. Backlog اپ Vehicle و Driver

| شناسه | اولویت | وضعیت | موضوع | معیار پذیرش خلاصه |
|---|---|---|---|---|
| VEH-001 | P2 | Open | summary service ORM دامنه‌های دیگر را می‌خواند | query port/read model مستقل |
| VEH-002 | P3 | Open | history service request ID را حذف می‌کند | correlation log قابل جست‌وجو |
| DRIVER-001 | P1 | Open | pagination/sort هنوز پس از load کامل گزارش شده | DB-level page با تست حجم/query |
| DRIVER-002 | P2 | Decision | soft-delete mixin برای SAP master data | policy مشترک decommission/soft-delete |

موارد انجام‌شده تاریخی Vehicle شامل validation کیلومتر همان روز، sync transaction/bulk، محدودسازی exception، انتقال filter/sort، transaction تغییر status، query serializer، mapper مشترک، بهبود summary و validation commissioning date بوده‌اند. قبل از اتکا در Production باید regression suite جاری اجرا شود.

## ۸. Backlog Authentication و Login آینده

علاوه بر `AUTH-001` تا `AUTH-006`:

| شناسه | اولویت | وضعیت | موضوع | معیار پذیرش |
|---|---|---|---|---|
| AUTH-007 | P1 | Open | uniqueness شماره پرسنلی در model state نیست | constraint شرطی مدل/migration همگام |
| AUTH-008 | P2 | Decision | account linking با SAP | collision، تغییر personnel number و audit مشخص |
| AUTH-009 | P2 | Decision | role source | local role یا mapping از group/claim با least privilege |
| AUTH-010 | P2 | Decision | رفتار قطعی IdP/SAP | session موجود، login جدید و break-glass admin مشخص |

## ۹. Code Review شناسه اصلی مدل‌ها

### DB-002 — انتخاب UUID یا BigAutoField برای هر مدل

- شدت: 🟡 Medium
- وضعیت: Review per model
- محل: `infrastructure/database/model_mixins.py` و تمام مدل‌های ORM جدید یا در حال بازطراحی
- مسئله: استفاده از `UUIDPrimaryKeyMixin` نباید برای تمام جدول‌ها یک قانون خودکار باشد. مدل‌های فعلی برای جلوگیری از migration و breaking change همچنان از `BusinessRecordModel` استفاده می‌کنند، اما هر مدل جدید باید جداگانه بررسی شود.

#### معیار انتخاب UUID

UUID معمولاً برای aggregate root یا entity مستقلی مناسب است که حداقل یکی از شرایط زیر را داشته باشد:

- شناسه آن در API، Celery، event، audit log یا SAP transaction مبادله می‌شود.
- قبل از اولین `INSERT` به شناسه نیاز دارد؛ مانند ساخت idempotency key.
- داده ممکن است میان چند محیط، سرویس یا منبع import/merge شود.
- حدس‌زدن ترتیب و تعداد رکوردها از روی URL مطلوب نیست.
- رکورد مستقل است و lifecycle آن فقط تابع یک parent نیست.

نمونه قابل‌قبول:

```python
class RepairOrderModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    UserAuditMixin,
    SoftDeleteMixin,
):
    order_number = models.CharField(max_length=30, unique=True)
```

در این مثال `id` شناسه فنی، `order_number` شناسه قابل‌نمایش کسب‌وکار و شماره سند SAP یک فیلد مستقل است؛ این سه نباید با هم ادغام شوند.

#### معیار انتخاب BigAutoField

شناسه عددی پیش‌فرض Django معمولاً برای جدول‌هایی مناسب‌تر است که:

- child داخلی یک aggregate هستند و خارج از parent آدرس‌دهی نمی‌شوند.
- شناسه آن‌ها وارد API عمومی، event، SAP یا integration contract نمی‌شود.
- حجم درج بسیار بالا دارند و locality/index size مهم است.
- merge مستقل داده میان چند منبع برای آن‌ها مطرح نیست.
- فقط یک surrogate key ساده برای دیتابیس نیاز دارند.

نمونه:

```python
class RepairOrderLine(TimestampMixin):
    # Django automatically adds: id = BigAutoField(primary_key=True)
    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="lines",
    )
```

#### سؤال‌های اجباری در Code Review

1. آیا شناسه این مدل از مرز دیتابیس خارج می‌شود؟
2. آیا قبل از ذخیره‌شدن رکورد به شناسه نیاز داریم؟
3. آیا مدل aggregate root است یا child داخلی؟
4. آیا business identifier مستقلی مانند `order_number` یا `sap_document_number` لازم است؟
5. حجم درج و اثر نوع کلید بر PK/FK indexها چقدر است؟
6. آیا تغییر نوع کلید برای مدل موجود، API یا migration شکستن‌پذیر ایجاد می‌کند؟

#### معیار پذیرش

- انتخاب نوع PK در PR مدل جدید با پاسخ کوتاه به سؤال‌های بالا مستند شود.
- UUID صرفاً برای یکسان‌بودن با مدل‌های قدیمی انتخاب نشود.
- مدل موجود بدون برنامه migration، بررسی FKها و قرارداد API از UUID به عدد یا برعکس تغییر نکند.
- benchmark فقط برای جدول پرتراکنش لازم است؛ تصمیم‌های عادی با الگوی دسترسی و مرزهای مدل گرفته شوند.
- دانستن UUID هرگز جایگزین object-level permission محسوب نشود.

## ۱۰. موارد انجام‌شده تاریخی

این بخش برای جلوگیری از باز شدن دوباره taskهای بسته نگهداری می‌شود، ولی جای commit history را نمی‌گیرد:

- claimهای حساس JWT کاهش یافتند.
- throttling login/refresh تعریف شد.
- schema پاسخ token اصلاح شد.
- query serializerهای Vehicle/Driver/Fault در بخش‌هایی اضافه شدند.
- چند mapper تکراری Vehicle یکپارچه شد.
- validation کیلومتر و commissioning date بهبود یافت.
- sync Vehicle/Driver و fault notification مسیرهای اجرایی پیدا کردند.
- domain exception translation و error contract مرکزی ایجاد شد.
- تست‌های domain، repository، API و SAP mock گسترش یافتند.

## ۱۱. ترتیب اجرای پیشنهادی

### مرحله شناخت و تثبیت

1. مطالعه اسناد canonical و دو جریان read/write SAP
2. جلسه قرارداد با تیم SAP
3. ثبت تصمیم Login/IdP و BAPI واقعی

### موج اول

1. `DEP-001`, `DEP-002`
2. `DB-001`, `AUTH-007`
3. `TEST-001`, `CI-001`

### موج امنیت و یکپارچگی

1. `SEC-001`, `SEC-002`, `SEC-003`
2. `SAP-001`, `TX-001`
3. `FAULT-001` تا `FAULT-005`

### موج Performance و معماری

1. `PERF-001`, `PERF-002`, `DRIVER-001`, `FAULT-006/007`
2. `DB-003`, `ARCH-001` تا `ARCH-004`
3. OpenAPI، typing، dependency lock و runbook

## ۱۲. نحوه بستن یک مورد

برای تغییر وضعیت به Done این اطلاعات ثبت شود:

```text
Status: Done
Commit/PR: ...
Validation: commands/tests
Migration impact: none / details
Operational note: rollout/rollback
Closed at: YYYY-MM-DD
```
