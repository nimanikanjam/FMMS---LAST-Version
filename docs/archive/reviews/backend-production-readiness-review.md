# گزارش حرفه‌ای بررسی Backend پروژه FMMS

## مشخصات بررسی

- دامنه بررسی: فقط Backend پروژه Django
- هدف: ارزیابی پیش از استقرار در محیط Production
- بخش‌های بررسی‌شده: معماری، Django/DRF، دیتابیس، امنیت، Performance، API، تست، Docker، Celery، SAP Integration و آمادگی استقرار
- بخش خارج از دامنه: Frontend
- تاریخ بررسی: ۱۴۰۵/۰۵/۲۲ (2026-08-13)

> هیچ مقدار محرمانه‌ای از فایل `.env` در این گزارش ثبت نشده است.

---

## خلاصه مدیریتی

Backend پروژه در وضعیت فعلی **برای Deploy در Production آماده نیست**.

پروژه از معماری لایه‌ای قابل توجه، مدل دامنه، تست‌های گسترده، logging ساختاریافته و abstraction مناسب برای SAP برخوردار است. بااین‌حال چند blocker جدی در استقرار، مجوزهای سطح شیء، migrationها، هم‌زمانی تراکنش‌های SAP، آپلود فایل و کیفیت pipeline وجود دارد.

مهم‌ترین موانع Production:

1. `docker-compose.yml` معتبر نیست و اجرا نمی‌شود.
2. Docker healthcheck به endpoint ناموجود اشاره می‌کند.
3. Modelها با migrationها همگام نیستند.
4. جزئیات و payload کامل تراکنش‌های SAP برای تمام کاربران احراز هویت‌شده قابل خواندن است.
5. Object-Level Authorization برای عملیات رانندگان کامل نیست.
6. مکانیزم idempotency تراکنش‌های SAP در برابر concurrency اتمیک نیست.
7. آپلود فایل فاقد کنترل نوع، حجم، نام و دسترسی امن است.
8. اجرای عادی تست‌ها تحت تأثیر `.env` قرار می‌گیرد و قطعی نیست.

حکم نهایی: **Deploy باید تا رفع موارد Critical و High متوقف شود.**

---

# یافته‌ها

## ۱. پیکربندی Docker Compose غیرقابل اجرا است

### شدت مشکل

🔴 بحرانی (Critical)

### محل مشکل

- فایل: `docker-compose.yml`
- خطوط: حدود 48 تا 56، 79 تا 86 و 111 تا 118
- فایل: `Dockerfile`
- خطوط: 55 تا 57
- فایل: `config/urls.py`
- خطوط: 15 تا 37

### شرح مشکل

سرویس‌های `app`، `celery-worker` و `celery-beat` به سرویسی با نام `db` وابسته‌اند، ولی هیچ serviceای با این نام در Compose تعریف نشده است.

خروجی واقعی بررسی:

```text
service "app" depends on undefined service "db": invalid compose project
```

علاوه بر آن، Docker healthcheck مسیر زیر را فراخوانی می‌کند:

```text
/api/health/
```

اما چنین routeای در URLهای پروژه وجود ندارد؛ بنابراین حتی پس از رفع Compose نیز container احتمالاً همواره `unhealthy` خواهد بود.

### دلیل

این دو ایراد مستقیماً مانع راه‌اندازی stack، rolling deployment و تشخیص صحیح سلامت container می‌شوند.

### روش استاندارد

- تعریف صریح PostgreSQL و healthcheck آن در Compose
- ایجاد endpoint سبک و بدون authentication برای liveness
- ایجاد readiness check جداگانه برای بررسی دیتابیس و وابستگی‌های ضروری

### راهکار پیشنهادی

سرویس `db` به Compose اضافه شود و endpointهای سلامت ایجاد شوند:

```python
urlpatterns = [
    path("api/health/live/", LiveHealthView.as_view()),
    path("api/health/ready/", ReadyHealthView.as_view()),
]
```

Healthcheck تصویر Production باید به `/api/health/live/` متصل شود.

---

## ۲. Modelها با Migrationها همگام نیستند

### شدت مشکل

🔴 بحرانی (Critical)

### محل مشکل

- `apps/authentication/infrastructure/models.py:75`
- `apps/authentication/infrastructure/migrations/0005_fmmsuser_personnel_number.py:30`
- `apps/material/infrastructure/models.py:70`

### شرح مشکل

دستور زیر با exit code غیرصفر خاتمه یافت:

```bash
python manage.py makemigrations --check --dry-run
```

Django قصد تولید migrationهای جدید برای موارد زیر را دارد:

- حذف constraint مربوط به `unique_fmms_user_personnel_number`
- تغییر چند فیلد `CentralStockModel`

در migration شماره ۵، `personnel_number` برای مقادیر غیرخالی unique است؛ اما constraint متناظر در `Meta` مدل فعلی وجود ندارد.

### دلیل

Schema واقعی دیتابیس می‌تواند با تعریف جاری مدل‌ها متفاوت شود. این موضوع موجب رفتار متفاوت database تازه و database قدیمی، شکست deployment و ایجاد migration ناخواسته می‌شود.

### روش استاندارد

هر تغییر مدل باید همراه migration بررسی‌شده و commit‌شده باشد. CI نیز باید دستورات زیر را اجرا کند:

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
```

### راهکار پیشنهادی

ابتدا باید مشخص شود حذف uniqueness از `personnel_number` عمدی است یا خیر. اگر هر شماره پرسنلی فقط متعلق به یک حساب است، constraint باید در مدل حفظ شود:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["personnel_number"],
            condition=~models.Q(personnel_number=""),
            name="unique_fmms_user_personnel_number",
        )
    ]
```

سپس تغییرات `CentralStockModel` نیز باید بررسی و migration معتبر آن commit شود.

---

## ۳. افشای payload کامل تراکنش‌های SAP

### شدت مشکل

🔴 بحرانی (Critical)

### محل مشکل

- `interfaces/api/v1/integration/views.py:26`
- کلاس: `SAPTransactionViewSet`
- `interfaces/api/v1/integration/serializers.py:26`
- کلاس: `SAPTransactionResponseSerializer`

### شرح مشکل

برای مشاهده تراکنش‌های SAP فقط `IsFMMSAuthenticated` لازم است. بنابراین نقش‌هایی مانند `VIEWER` یا `DRIVER` نیز می‌توانند تمام تراکنش‌های SAP را مشاهده کنند.

Serializer اطلاعات زیر را بدون redaction برمی‌گرداند:

- `request_payload`
- `response_payload`
- `error_message`
- `idempotency_key`
- شماره اسناد SAP

### دلیل

این payloadها می‌توانند شامل شماره پرسنلی، اطلاعات خودرو، اقلام خرید، vendor، plant، شرح خرابی و جزئیات داخلی ERP باشند. پیام خطای SAP نیز ممکن است اطلاعات فنی یا سازمانی حساس افشا کند.

### روش استاندارد

- دسترسی به جزئیات Integration فقط برای نقش‌های مدیریتی محدود
- استفاده از serializer عمومی بدون payload خام
- redaction فیلدهای حساس
- ثبت audit برای مشاهده جزئیات تراکنش‌ها

### راهکار پیشنهادی

حداقل permission به یکی از موارد زیر تغییر کند:

```python
permission_classes = [IsAdminRole]
```

یا:

```python
permission_classes = [IsSupervisorOrAbove]
```

همچنین payload خام باید از API عمومی حذف و در endpoint مدیریتی مجزا با redaction ارائه شود.

---

## ۴. نبود Object-Level Authorization برای رانندگان

### شدت مشکل

🔴 بحرانی (Critical)

### محل مشکل

- `core/permissions/role_permissions.py:138`
- کلاس: `IsDriverOrTechnicianOrAbove`
- `interfaces/api/v1/repair/views.py:753`
- توابع: `confirm_delivery` و `confirm_pickup`
- `apps/repair/application/services/external_workshop_service.py:247`
- `apps/handover/application/services/handover_service.py:119`

### شرح مشکل

Permission فقط نقش `DRIVER` را بررسی می‌کند. پس از آن کاربر می‌تواند با UUID دلخواه روی assignment یا handover متعلق به راننده یا خودروی دیگری عملیات انجام دهد.

عملیات در معرض خطر:

- تأیید تحویل خودرو به تعمیرگاه بیرونی
- تأیید دریافت خودرو از تعمیرگاه
- قبول یا رد handover

در application service بررسی نمی‌شود که کاربر فعلی راننده تخصیص‌یافته به همان خودرو باشد.

### دلیل

این وضعیت نمونه BOLA/IDOR است؛ دانستن یا حدس زدن UUID رکورد برای انجام عملیات حساس کافی می‌شود.

### روش استاندارد

Authorization باید هم نقش و هم مالکیت عملیاتی را کنترل کند:

```text
request.user
  -> personnel_number
  -> linked driver
  -> current vehicle assignment
  -> target vehicle/assignment/handover
```

### راهکار پیشنهادی

یک policy یا authorization service مستقل ایجاد شود:

```python
driver_access_policy.ensure_can_confirm_vehicle(
    user_id=current_user_id,
    vehicle_id=assignment.vehicle_id,
)
```

این کنترل باید داخل application service نیز اجرا شود تا invocation از API، command یا task همگی امن باشند.

---

## ۵. Idempotency تراکنش‌های SAP در برابر concurrency ایمن نیست

### شدت مشکل

🔴 بحرانی (Critical)

### محل مشکل

- `infrastructure/sap/transaction/sap_transaction_manager.py:128`
- `apps/integration/infrastructure/repositories.py:97`
- متدها: `execute`، `save` و `retry_all_pending`

### شرح مشکل

Manager ابتدا با `get_by_idempotency_key()` وجود رکورد را بررسی و بعد رکورد جدیدی با UUID متفاوت ذخیره می‌کند. check و insert در یک transaction یا lock مشترک نیستند.

Repository در docstring ادعا می‌کند از `select_for_update` استفاده شده، اما در implementation هیچ `select_for_update()`ای وجود ندارد.

Retry sweep نیز همه رکوردهای قابل retry را بدون claim یا `skip_locked` بارگذاری می‌کند؛ در نتیجه چند worker می‌توانند یک تراکنش را هم‌زمان retry کنند.

### دلیل

عملیات SAP اثر خارجی دارد و rollback دیتابیس نمی‌تواند اثر ایجادشده در SAP را خنثی کند. ارسال تکراری می‌تواند اثر مالی یا عملیاتی ایجاد کند.

### روش استاندارد

- claim اتمیک transaction پیش از تماس خارجی
- `select_for_update(skip_locked=True)` برای workerها
- مدیریت `IntegrityError`
- transition شرطی وضعیت با compare-and-set
- استفاده از idempotency در سمت SAP در صورت پشتیبانی

### راهکار پیشنهادی

```python
with transaction.atomic():
    txn = (
        SAPTransactionModel.objects
        .select_for_update(skip_locked=True)
        .get(id=transaction_id)
    )
    if txn.status != SAPTransactionStatus.FAILED.value:
        return
    txn.status = SAPTransactionStatus.IN_PROGRESS.value
    txn.save(update_fields=["status", "updated_at"])
```

تماس خارجی باید پس از claim کوتاه و commit شدن وضعیت انجام شود.

---

## ۶. باز ماندن transaction دیتابیس هنگام تماس خارجی

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `config/settings/base.py:148`
- `interfaces/api/v1/integration/views.py:115`
- `apps/repair/application/services/external_workshop_service.py:167`

### شرح مشکل

`ATOMIC_REQUESTS=True` تمام request را داخل transaction دیتابیس قرار می‌دهد. در همین requestها ممکن است sync کامل SAP یا تماس شبکه‌ای طولانی انجام شود. برخی serviceها نیز transaction تو‌در‌تو دارند.

### دلیل

تماس SAP می‌تواند زمان‌بر باشد. در این مدت connection و transaction دیتابیس باز می‌ماند و احتمال lock contention، timeout و exhaustion connection pool افزایش می‌یابد.

### روش استاندارد

- غیرفعال کردن `ATOMIC_REQUESTS`
- transactionهای کوتاه و صریح برای writeهای مرتبط
- انتقال syncهای طولانی به Celery
- استفاده از outbox pattern برای هماهنگی دیتابیس و SAP

### راهکار پیشنهادی

endpointهای sync باید job ایجاد کرده و `202 Accepted` برگردانند:

```python
task = run_sap_sync.delay(...)
return Response(
    {"task_id": task.id},
    status=status.HTTP_202_ACCEPTED,
)
```

---

## ۷. آپلود فایل ناامن و بدون محدودیت کافی

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `interfaces/api/v1/repair/views.py:137`
- تابع: `_save_external_invoice_file`
- `interfaces/api/v1/repair/views.py:803`
- action: `review`

### شرح مشکل

فایل فاکتور با `uploaded.name` ذخیره می‌شود و کنترل صریحی برای موارد زیر وجود ندارد:

- حداکثر حجم فایل
- MIME type
- extension مجاز
- signature واقعی فایل
- malware scan
- نام تصادفی فایل
- private storage و URL امضاشده

### دلیل

امکان آپلود فایل بسیار بزرگ، محتوای executable یا HTML/SVG مخرب، سوءاستفاده از storage و توزیع فایل ناامن وجود دارد.

### روش استاندارد

- whitelist نوع فایل مانند PDF/JPEG/PNG
- محدودیت حجم در Django و reverse proxy
- نام ذخیره‌سازی UUID
- private object storage
- endpoint دانلود احراز هویت‌شده
- malware scanning

### راهکار پیشنهادی

```python
extension = validate_invoice_file(uploaded)
safe_name = f"{uuid.uuid4()}{extension}"
```

نام اصلی کاربر فقط به‌عنوان metadata ذخیره شود و URL عمومی دائمی برگردانده نشود.

---

## ۸. Pagination پس از بارگذاری کل داده‌ها انجام می‌شود

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `interfaces/api/v1/utils.py:24`
- `apps/vehicle/infrastructure/repositories.py:139`
- `apps/driver/infrastructure/repositories.py:100`
- `interfaces/api/v1/integration/views.py:44`

### شرح مشکل

Repositoryها ابتدا تمام `QuerySet` را به list از domain entity تبدیل می‌کنند و سپس API همان list را paginate می‌کند.

در list تراکنش‌های SAP، وضعیت‌ها جداگانه query، تمام رکوردها در حافظه ادغام و sort و سپس paginate می‌شوند.

### دلیل

pagination فقط اندازه پاسخ را کاهش می‌دهد؛ ولی مصرف حافظه، زمان query و هزینه تبدیل داده را محدود نمی‌کند. با رشد داده endpointها کند یا دچار OOM می‌شوند.

### روش استاندارد

filter، sort، count و slice باید در database انجام شوند.

### راهکار پیشنهادی

Query service باید `QuerySet` محدود یا یک مدل page صریح برگرداند:

```python
@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    next_cursor: str | None
```

برای logهای SAP، cursor pagination از page-number مناسب‌تر است.

---

## ۹. حذف Referential Integrity بین bounded contextها

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `apps/vehicle/infrastructure/models.py:15`
- `apps/fault/infrastructure/models.py:10`
- `apps/repair/infrastructure/models.py:14`
- مدل‌های Material، PM و Handover

### شرح مشکل

تعداد زیادی از ارتباط‌های اصلی فقط `UUIDField` هستند:

- Fault به Vehicle
- Repair Order به Fault و Vehicle
- Material Request به Repair Order
- PM Plan به Vehicle
- Handover به Vehicle و Repair Order

### دلیل

در یک monolith با database مشترک، این تصمیم ایجاد orphan record و داده ناسازگار را ممکن می‌کند. مرزبندی DDD الزاماً مستلزم حذف constraint دیتابیس نیست.

### روش استاندارد

برای relationshipهایی که consistency آن‌ها ضروری است باید FK واقعی یا حداقل constraint معتبر وجود داشته باشد. در صورت استقلال کامل storage، reconciliation job و consistency contract لازم است.

### راهکار پیشنهادی

حداقل ارتباط‌های critical مانند موارد زیر به FK تبدیل شوند:

- `RepairOrder -> Vehicle`
- `RepairOrder -> Fault`
- `Handover -> RepairOrder`
- `MaterialRequest -> RepairOrder`

UUID همچنان می‌تواند کلید اصلی باقی بماند.

---

## ۱۰. Soft-delete به‌صورت سراسری enforce نشده است

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `infrastructure/database/base_model.py:17`
- `apps/vehicle/infrastructure/repositories.py:94`
- `apps/driver/infrastructure/repositories.py:84`
- `apps/integration/infrastructure/repositories.py:57`

### شرح مشکل

`BaseModel` اعلام می‌کند تمام queryها باید `is_deleted=False` داشته باشند، اما repositoryهای متعددی این شرط را اعمال نمی‌کنند؛ برای نمونه:

```python
VehicleModel.objects.get(id=vehicle_id)
DriverModel.objects.all()
SAPTransactionModel.objects.get(id=transaction_id)
```

### دلیل

رکورد حذف‌شده ممکن است دوباره نمایش داده یا وارد workflow شود. اتکا به اینکه هر توسعه‌دهنده در هر query فیلتر را دستی اضافه کند قابل اطمینان نیست.

### روش استاندارد

استفاده از Manager پیش‌فرض برای رکوردهای فعال و Manager مجزا برای audit:

```python
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    objects = ActiveManager()
    all_objects = models.Manager()
```

---

## ۱۱. Celery ممکن است ناخواسته با تنظیمات Development اجرا شود

### شدت مشکل

🟠 زیاد (High)

### محل مشکل

- `infrastructure/messaging/celery_app.py:13`

### شرح مشکل

Celery در نبود متغیر محیطی از `config.settings.development` استفاده می‌کند؛ درحالی‌که WSGI و ASGI پیش‌فرض Production دارند.

### دلیل

یک worker ناقص پیکربندی‌شده می‌تواند با `DEBUG=True`، CORS باز و logging دیتابیس در محیط Production بالا بیاید.

### روش استاندارد

settings محیط Production باید صریح و اجباری باشد. fallback runtime نباید به Development اشاره کند.

### راهکار پیشنهادی

fallback به production تغییر کند یا نبود `DJANGO_SETTINGS_MODULE` موجب fail-fast شود.

---

## ۱۲. تست‌ها Hermetic و مستقل از محیط نیستند

### شدت مشکل

🟡 متوسط (Medium)

### محل مشکل

- `config/settings/test.py:11`
- `config/settings/base.py:27`

### شرح مشکل

تنظیمات تست `SAP_USE_MOCK=True` را override می‌کند، ولی مقدار `SAP_WRITE` را از `.env` توسعه‌دهنده به ارث می‌برد.

نتایج واقعی:

```text
اجرای عادی: 15 failed, 773 passed
اجرا با SAP_WRITE=true: 788 passed
```

### دلیل

نتیجه تست به workstation و `.env` وابسته است و pipeline قابل اعتماد نیست.

### روش استاندارد

تمام feature flagها و integration toggleها باید در test settings مقدار قطعی داشته باشند.

### راهکار پیشنهادی

```python
os.environ["SAP_USE_MOCK"] = "True"
os.environ["SAP_WRITE"] = "True"
```

بهتر است test settings از ابتدا مانع خوانده شدن `.env` محلی شود.

---

## ۱۳. UUID نامعتبر ممکن است به پاسخ 500 تبدیل شود

### شدت مشکل

🟡 متوسط (Medium)

### محل مشکل

- `interfaces/api/v1/integration/views.py:34`
- `interfaces/api/v1/vehicle/views.py:49`
- موارد مشابه در Fault، Repair، Material، PM، Procurement و Driver
- `core/exceptions/http_exception_handler.py:251`

### شرح مشکل

ده‌ها endpoint مستقیماً مقدار مسیر را به‌شکل زیر تبدیل می‌کنند:

```python
uuid.UUID(str(pk))
```

`ValueError` حاصل در exception handler به Validation Error ترجمه نمی‌شود و ممکن است به 500 تبدیل شود.

### روش استاندارد

از URL converter یا serializer استفاده شود:

```python
path("<uuid:pk>/...", ...)
```

یا تبدیل UUID در helper مشترک انجام و پاسخ 400 استاندارد تولید شود.

---

## ۱۴. Quality Gateها در وضعیت شکست هستند

### شدت مشکل

🟡 متوسط (Medium)

### محل مشکل

- `pyproject.toml:46`
- `Makefile:100`
- کل Backend

### شرح مشکل

نتایج بررسی خودکار:

- Ruff: چهار خطا
- mypy: ۳۴ خطا در ۲۰ فایل
- Django deploy/OpenAPI check: بیست warning/error
- migration check: ناموفق
- CI workflow در repository مشاهده نشد

برخی خطاهای mypy فقط ظاهری نیستند؛ برای مثال احتمال dereference روی dependency اختیاری یا مقدار `None` را نشان می‌دهند.

### روش استاندارد

Merge باید مشروط به عبور موارد زیر باشد:

```text
black --check
ruff
mypy
makemigrations --check
pytest
check --deploy
OpenAPI schema validation
```

---

## ۱۵. OpenAPI ناقص و ناسازگار است

### شدت مشکل

🟡 متوسط (Medium)

### محل مشکل

- `interfaces/api/v1/vehicle/views.py:40`
- `interfaces/api/v1/material/views.py:38`
- `interfaces/api/v1/repair/external_invoice_views.py:61`
- چندین پارامتر مسیر در ViewSetها

### شرح مشکل

`drf-spectacular` نتوانست serializer چند ViewSet را استخراج کند و برای UUIDها و enumها collision گزارش کرد. بخشی از schema یا client generated از آن ناقص خواهد بود.

### راهکار پیشنهادی

- تعریف `serializer_class` یا `get_serializer_class`
- annotation صریح پارامترهای UUID
- تنظیم `ENUM_NAME_OVERRIDES`
- تولید schema در CI و fail کردن pipeline روی warningهای مهم

---

## ۱۶. Dependencyها reproducible نیستند

### شدت مشکل

🟡 متوسط (Medium)

### محل مشکل

- `requirements/base.txt:7`
- `requirements/production.txt:8`

### شرح مشکل

وابستگی‌ها با range مشخص شده‌اند و lockfile یا hash وجود ندارد. buildهای مختلف ممکن است نسخه‌های متفاوتی نصب کنند.

همچنین comment فایل Production بیان می‌کند `psycopg2-binary` باید با نسخه کامپایل‌شده جایگزین شود، ولی در عمل همان binary از base نصب می‌شود.

### روش استاندارد

- requirements قفل‌شده و دارای hash
- dependency scanning
- build قابل تکرار
- pin کردن base image با digest

---

## ۱۷. پوشش محدود Django Admin

### شدت مشکل

🟢 کم (Low)

### محل مشکل

- `apps/authentication/admin.py:9`

### شرح مشکل

فقط مدل User در Admin ثبت شده است. مشاهده امن workflowهای گیرکرده، تراکنش‌های SAP و رکوردهای soft-deleted برای پشتیبانی Production دشوار خواهد بود.

### روش استاندارد

Admin عملیاتی باید read-only، دارای permission دقیق و redaction اطلاعات حساس باشد. ثبت بدون محدودیت تمام مدل‌ها نیز راهکار مناسبی نیست.

---

# بررسی معماری

## نقاط مثبت

- تفکیک `domain/application/infrastructure/interfaces` در اکثر bounded contextها واضح است.
- business state transitionها عمدتاً داخل domain entity قرار گرفته‌اند.
- repository interfaceها testability را بهتر کرده‌اند.
- SAP adapterها و transaction manager از منطق HTTP جدا شده‌اند.
- exception contract و response format مرکزی وجود دارد.

## مشکلات معماری

- application serviceهای متعددی مستقیماً مدل ORM را import می‌کنند.
- بعضی query serviceها به infrastructure چند app وابسته‌اند.
- `interfaces.api.v1.deps` بیش از ۱۲۰۰ خط شده و Composition Root بیش از حد متمرکز است.
- Celery taskها dependencyهای خود را از لایه API دریافت می‌کنند:

```python
from interfaces.api.v1 import deps
```

- بعضی serviceها private helper یک bounded context دیگر را import می‌کنند؛ مانند `_close_fault_for_completed_repair`.
- فایل‌هایی مانند `repair/views.py` و `repair/domain/entities.py` بیش از حد بزرگ شده‌اند.

## نتیجه معماری

جهت کلی معماری مناسب است، اما boundaryها در چند نقطه رعایت نشده‌اند. پیشنهاد می‌شود Composition Root مستقل از API ایجاد و read model/query serviceها صریحاً به لایه جداگانه منتقل شوند.

---

# بررسی دیتابیس و ORM

## نقاط مثبت

- استفاده گسترده از UUID برای شناسه‌ها
- وجود indexهای ترکیبی برای status، vehicle و date
- استفاده از `UniqueConstraint` در child entityها
- استفاده از `transaction.atomic` و `bulk_create` در بعضی aggregate repositoryها
- استفاده از `prefetch_related` برای SAP sync history

## مشکلات اصلی

- pagination عمدتاً بعد از materialize شدن تمام داده انجام می‌شود.
- در برخی repositoryها soft-delete نادیده گرفته شده است.
- تعداد زیادی relationship بدون FK واقعی هستند.
- برخی indexها تکراری‌اند؛ یک field هم `db_index=True` دارد و هم Index جداگانه روی همان field تعریف شده است.
- تست‌های اصلی روی SQLite اجرا می‌شوند و رفتار PostgreSQL را کاملاً پوشش نمی‌دهند.
- `ATOMIC_REQUESTS` transactionهای طولانی ایجاد می‌کند.
- concurrency workflowها در بیشتر serviceها `select_for_update` ندارند.

## ریسک N+1

N+1 کلاسیک در بخش‌هایی با `prefetch_related` کنترل شده است، اما در مسیر external workshop، تبدیل هر assignment به DTO می‌تواند برای delivery، pickup و review سه query جداگانه اجرا کند. در list assignmentها این الگو به‌صورت تقریبی `1 + 3N` query ایجاد می‌کند.

محل مهم:

- `apps/repair/application/services/external_workshop_service.py:148`

بهتر است repository یک read query با `select_related("delivery", "pickup", "repair_review")` یا projection مناسب ارائه کند.

---

# بررسی امنیت

## نقاط مثبت

- `DEBUG=False` در Production
- HSTS و HTTPS redirect
- cookieهای Secure و HttpOnly
- CORS محدود در Production
- JWT authentication
- throttle مستقل برای token obtain و refresh
- exception response بدون stack trace
- `.env` در `.gitignore` و `.dockerignore`
- SQL خام و `eval/exec` خطرناک مشاهده نشد

## مشکلات امنیتی کلیدی

- نبود object-level permission برای عملیات راننده
- افشای payloadهای SAP
- آپلود فایل بدون validation کافی
- read access گسترده برای تمام کاربران احراز هویت‌شده
- request ID ورودی بدون validation یا محدودیت طول پذیرفته می‌شود
- refresh token rotation و blacklist تنظیم نشده است
- endpointهای schema و Admin نیازمند سیاست انتشار صریح هستند
- throttle عمومی برای endpointهای پرهزینه وجود ندارد

---

# بررسی Performance و مقیاس‌پذیری

## مشکلات اصلی

- pagination در حافظه
- sync کامل SAP به‌صورت synchronous از API
- transactionهای طولانی ناشی از `ATOMIC_REQUESTS`
- query و sort در Python برای SAP transaction list
- نبود cache کاربردی با وجود تنظیم Redis
- احتمال `1 + 3N` query در external workshop assignment DTO
- workerهای retry بدون claim اتمیک
- استفاده از listهای کامل domain entity به‌جای projection یا page

## پیشنهادهای اصلی

1. database-level pagination
2. انتقال عملیات طولانی به Celery
3. outbox pattern برای SAP writes
4. read modelهای بهینه برای dashboardها
5. cache محدود و versioned برای catalogها و dashboardهای مناسب
6. PostgreSQL integration tests برای constraint و concurrency

---

# بررسی API

## نقاط مثبت

- versioning مسیر با `/api/v1/`
- serializer validation در اکثر command endpointها
- status codeهای مناسب در بسیاری از create/updateها
- error contract مرکزی
- pagination پیش‌فرض با حداکثر page size

## مشکلات

- بعضی عملیات طولانی به‌جای `202` پاسخ synchronous می‌دهند.
- UUID نامعتبر ممکن است 500 شود.
- OpenAPI ناقص است.
- BOLA برای workflow راننده وجود دارد.
- SAP payload بیش از حد در response افشا می‌شود.
- filtering و ordering در همه endpointها contract یکسان و schema کامل ندارند.

---

# آمادگی Production

## موارد موجود و مناسب

- Gunicorn
- non-root Docker user
- structured JSON logging
- Sentry integration
- request correlation ID
- Celery و Celery Beat
- Redis cache/broker
- تنظیمات مجزای Development، Staging، Test و Production

## موارد ناقص یا مسدودکننده

- Compose خراب
- health endpoint ناموجود
- migration drift
- CI/CD workflow ناموجود
- dependency lock ناموجود
- health/readiness ناقص
- strategy مشخص برای static/media و private uploads وجود ندارد
- migration در image Production به‌شکل روشن orchestrate نشده است
- collectstatic با `|| true` failure را پنهان می‌کند
- monitoring عملیاتی Celery/Redis/DB کامل نیست
- backup، restore و disaster recovery در scope repository مشخص نشده است

---

# نتایج بررسی‌های خودکار

## Django system check

```text
System check identified no issues (test settings)
```

## Production deploy/schema check

```text
20 warnings/errors
```

مهم‌ترین موارد مربوط به schema generation، serializer detection، UUID parameter typing و enum collision بود.

## Migration check

```text
Failed: model changes without committed migrations
```

## Ruff

```text
4 errors
```

## mypy

```text
34 errors in 20 files
```

## Docker Compose

```text
Failed: undefined service "db"
```

## تست‌ها

اجرای عادی با environment فعلی:

```text
15 failed, 773 passed
```

با تنظیم قطعی `SAP_WRITE=true`:

```text
788 passed, 1 warning
```

این نتیجه نشان می‌دهد پوشش تست پروژه قابل توجه است، اما test configuration از `.env` محلی اثر می‌پذیرد.

---

# نقاط مثبت کلی پروژه

- معماری لایه‌ای و bounded contextهای قابل تشخیص
- domain entity و state machineهای نسبتاً قوی
- ۷۸۸ تست در domain، application، API، repository و SAP adapter
- error contract مرکزی و دارای request ID
- logging ساختاریافته
- تنظیمات امنیتی مناسب در Production
- throttle endpointهای authentication
- abstraction مناسب برای SAP client و adapter
- وجود idempotency key و retry lifecycle، هرچند concurrency آن نیازمند اصلاح است
- استفاده مناسب از index و constraint در چند بخش مهم
- نبود SQL خام و الگوهای injection آشکار

---

# ارزیابی سطح مهندسی پروژه

## سطح کلی

**Mid-Level قوی، نزدیک به Senior**

طراحی دامنه، تعداد تست‌ها، abstractionهای SAP و logging از سطح Mid معمولی بالاتر است و بعضی بخش‌ها کیفیت Senior دارند. بااین‌حال موارد زیر مانع ارزیابی کلی Senior، Staff یا Principal می‌شوند:

- deployment configuration قابل اجرا نیست؛
- object-level authorization کامل نشده است؛
- migration drift وجود دارد؛
- concurrency عملیات SAP تضمین نشده است؛
- pagination در حافظه انجام می‌شود؛
- boundaryهای معماری در چند نقطه شکسته شده‌اند؛
- CI و quality gate فعال وجود ندارد؛
- test suite از `.env` محلی اثر می‌پذیرد.

معماری پروژه گرایش Staff-level دارد، اما اجرای Production فعلی هنوز به سطح قابل اتکای Senior نرسیده است.

---

# امتیاز نهایی

| معیار | امتیاز |
|---|---:|
| معماری | 7.0 از 10 |
| Best Practiceهای Django | 6.0 از 10 |
| کیفیت کدنویسی | 6.5 از 10 |
| امنیت | 4.5 از 10 |
| Performance | 5.0 از 10 |
| مقیاس‌پذیری | 5.0 از 10 |
| قابلیت نگهداری | 6.5 از 10 |
| آمادگی Production | **3.0 از 10** |

---

# اولویت اصلاحات

## P0 — قبل از هر Deploy

1. اصلاح `docker-compose.yml` و تعریف `db`
2. ایجاد health endpoint معتبر
3. رفع migration drift
4. محدودسازی API تراکنش‌های SAP و حذف payload خام
5. پیاده‌سازی object-level authorization برای Driver
6. اصلاح concurrency و claim تراکنش‌های SAP
7. امن‌سازی file upload

## P1 — پیش از Pilot Production

1. حذف `ATOMIC_REQUESTS` و تعریف transaction boundaryهای کوتاه
2. database-level pagination
3. انتقال SAP syncهای طولانی به Celery
4. enforce کردن soft-delete با Manager
5. مستقل کردن test settings از `.env`
6. رفع Ruff، mypy و OpenAPI warnings
7. راه‌اندازی CI quality gates

## P2 — برای مقیاس‌پذیری و نگهداری

1. اصلاح dependency direction و Composition Root
2. تجزیه فایل‌های بسیار بزرگ
3. افزودن PostgreSQL integration/concurrency tests
4. طراحی read model و cache برای dashboardها
5. بازنگری FKها و referential integrity
6. lock کردن dependencyها و افزودن vulnerability scanning

---

# نتیجه نهایی

پروژه پایه فنی خوبی دارد و از یک CRUD ساده بسیار فراتر است. وجود domain model، workflow، SAP abstraction و تست‌های گسترده ارزشمند است. بااین‌حال، ریسک‌های فعلی عمدتاً در مرزهایی قرار دارند که در Production اهمیت حیاتی پیدا می‌کنند: استقرار، authorization، concurrency، migration consistency و کنترل داده حساس.

تا زمان رفع موارد P0، این Backend نباید Production-ready تلقی شود.
