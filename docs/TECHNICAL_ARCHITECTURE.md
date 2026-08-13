# معماری فنی FMMS

این سند مرجع معماری Backend فعلی است. برای مسئله کسب‌وکار به [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)، برای SAP به [SAP_INTEGRATION_GUIDE.md](SAP_INTEGRATION_GUIDE.md) و برای ایرادهای باز به [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md) مراجعه کنید.

## ۱. نمای کلان

Backend یک Django modular monolith با تفکیک domain/application/infrastructure/interface است:

```text
HTTP Client
  -> interfaces/api/v1 (View, Serializer, Permission)
  -> Application Service / DTO
  -> Domain Entity / Value Object / Port
  -> Repository یا SAP Port
  -> Django ORM / SAP Adapter / Celery
  -> PostgreSQL / SAP / Redis
```

## ۲. ساختار مخزن

```text
config/                  تنظیمات Django، URL، WSGI و ASGI
core/                    exception، logging، middleware، permission، pagination و SAP ports
apps/<domain>/domain/    entity، value object، exception و repository interface
apps/<domain>/application/ service، DTO و use case
apps/<domain>/infrastructure/ ORM model، repository و migration
interfaces/api/v1/       REST API v1 و composition فعلی dependencyها
infrastructure/database/ mixinهای ORM و commandهای عملیاتی
infrastructure/sap/      client، adapter و transaction manager
infrastructure/messaging/ Celery app و taskها
tests/                   unit، integration و factory
```

## ۳. قواعد وابستگی

1. Domain نباید Django، DRF، interface یا infrastructure را import کند.
2. Application باید به portها وابسته باشد، نه ORM یا adapter concrete.
3. Interface مسئول HTTP validation، authentication، serialization و status code است.
4. Infrastructure مسئول ORM، SAP، storage و messaging است.
5. business rule نباید در View، Serializer یا Celery task تکرار شود.
6. Composition Root باید مستقل از API قابل استفاده باشد؛ `interfaces/api/v1/deps.py` در آینده باید کوچک و ماژولار شود.

## ۴. مرزهای دامنه

هر app یک bounded context است. referenceهای داخل aggregate از FK واقعی استفاده می‌کنند؛ بسیاری از referenceهای cross-domain به‌شکل UUID نگهداری شده‌اند. این تصمیم استقلال appها را بیشتر کرده، ولی referential integrity را به application service منتقل کرده است و باید برای ارتباط‌های critical بازنگری شود.

## ۵. دیتابیس

### فناوری و اصول

- Production: PostgreSQL
- Development: PostgreSQL خارجی، مشابه Production
- Test فعلی: SQLite
- کلید اصلی business modelها: UUID
- timestampها: UTC
- audit: `created_*`, `updated_*`, `deleted_*`
- soft delete: `is_deleted`
- migrationها در `apps/<domain>/infrastructure/migrations/`
- ساخت Database و Role خارج از Django و توسط DBA/زیرساخت انجام می‌شود.
- Django فقط schema را با migration مدیریت می‌کند؛ WSGI، ASGI و Celery startup بدون side effect دیتابیسی‌اند.

### Model mixinها

چهار abstract mixin مستقل، UUID، timestamp، user audit و soft-delete را فراهم می‌کنند. مدل‌های فعلی برای حفظ schema از ترکیب `BusinessRecordModel` استفاده می‌کنند؛ مدل جدید باید فقط mixinهای واقعاً لازم را انتخاب کند. وضعیت فعلی یک نقص شناخته‌شده دارد: همه repositoryها `is_deleted=False` را یکسان enforce نمی‌کنند. هدف معماری استفاده از managerهای `objects` و `all_objects` یا policy صریح برای master data است.

### رابطه‌های بین دامنه‌ها

ADR تاریخی استفاده از UUID به‌جای FK را تعیین کرده است. این تصمیم برای هر رابطه الزام دائمی نیست. برای `RepairOrder -> Vehicle/Fault`، `Handover -> RepairOrder` و `MaterialRequest -> RepairOrder` باید trade-off استقلال و یکپارچگی داده جداگانه ثبت شود.

### Migration policy

- هیچ تغییر model بدون migration مجاز نیست.
- CI باید `makemigrations --check --dry-run` و `migrate --check` را اجرا کند.
- data migration باید forward-safe و برای حجم Production بررسی شود.
- migration تولیدی نباید صرفاً برای خاموش کردن drift پذیرفته شود.

### تصمیم `personnel_number`

`FMMSUser.personnel_number` برای مقدار غیرخالی باید Unique بماند. constraint مورد انتظار:

```python
models.UniqueConstraint(
    fields=["personnel_number"],
    condition=~models.Q(personnel_number=""),
    name="unique_fmms_user_personnel_number",
)
```

این فیلد اتصال عملیاتی کاربر FMMS به پرسنل/راننده SAP است. برای login آینده، شناسه ورود پایدار SAP/IdP باید جدا از `personnel_number` مدل شود.

## ۶. API

- Base path: `/api/v1/`
- Authentication فعلی: JWT و SessionAuthentication
- Schema: drf-spectacular
- Pagination: page number، اندازه پیش‌فرض ۲۰ و سقف ۱۰۰
- Error body:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "details": {},
  "request_id": "..."
}
```

### قواعد API

- ورودی commandها با Serializer validate شود.
- UUID مسیر با converter یا serializer validate شود.
- عملیات طولانی integration باید `202 Accepted` و job identifier برگرداند.
- list endpoint باید در دیتابیس paginate شود، نه پس از materialize شدن list.
- role permission با object-level policy تکمیل شود.
- model ORM مستقیماً serialize نشود؛ DTO/read model مرز پاسخ است.

## ۷. Authentication و Authorization

### وضعیت فعلی

- `FMMSUser` با username، email، role و personnel number
- JWT access/refresh
- roleهای ADMIN، SUPERVISOR، DISTRIBUTION، TRANSPORT، WAREHOUSE، WORKSHOP_SUPERVISOR، TECHNICIAN، DRIVER و VIEWER
- throttle روی token obtain و refresh

### جهت آینده Login از طریق SAP

ورود SAP نباید به معنی ذخیره password SAP در FMMS باشد. مسیر ترجیحی:

```text
SAP IAS / Entra ID / Corporate IdP
  -> OIDC یا SAML
  -> stable external subject
  -> FMMSUser
  -> role mapping داخلی و JWT/session FMMS
```

فیلدهای مفهومی آینده:

```text
identity_provider
external_subject / sap_user_id (unique when present)
personnel_number (unique when non-empty)
last_identity_sync_at
```

تصمیم‌های باز: محصول SAP، وجود IAS، پروتکل مورد حمایت، شناسه پایدار، منبع roleها، رفتار هنگام قطعی IdP و سیاست account linking.

## ۸. Background Processing

Celery/Beat برای syncهای SAP، retry تراکنش‌های ناموفق و trigger نگهداری پیشگیرانه استفاده می‌شود. Task باید application service را فراخوانی کند و business logic یا ORM workflow مستقل نسازد.

مشکلات شناخته‌شده:

- Celery app در نبود env به development settings fallback می‌کند.
- retry worker claim اتمیک/`skip_locked` کامل ندارد.
- بعضی عملیات طولانی هنوز synchronous از API اجرا می‌شوند.

## ۹. Logging و Audit

- JSON structured logging
- `X-Request-ID` برای correlation
- audit middleware برای POST/PUT/PATCH/DELETE
- Sentry در staging/production
- SAP transaction و sync run برای audit integration

Client-supplied request ID باید validate و محدود شود. audit امنیتی آینده باید login، تغییر role، مشاهده payload حساس و عملیات مدیریتی را نیز پوشش دهد.

## ۱۰. Deployment

### معماری هدف

```text
Reverse Proxy / TLS
  -> Gunicorn / Django
  -> PostgreSQL
  -> Redis
  -> Celery Worker + Beat
  -> Private File Storage
  -> SAP OData/RFC
```

### وضعیت فعلی

Dockerfile از user غیر root و Gunicorn استفاده می‌کند و production settings hardening مناسبی دارند؛ ولی Compose فاقد service دیتابیس و healthcheck متصل به route ناموجود است. تا رفع موارد `DEP-001` و `DEP-002` سند Compose مرجع deployment قابل اجرا نیست.

## ۱۱. تست و Quality Gate

- تست‌ها: pytest و pytest-django
- lint/format: Ruff، Black و isort
- typing: mypy
- coverage target: ۸۰٪
- رفتار PostgreSQL-specific و concurrency باید در pipeline جداگانه با PostgreSQL واقعی تست شود.

Quality gate پیشنهادی:

```bash
black --check .
isort --check .
ruff check .
mypy .
python manage.py makemigrations --check --dry-run
python manage.py check --deploy
pytest
```

## ۱۲. تصمیم‌های معماری تثبیت‌شده

| شناسه | تصمیم |
|---|---|
| ADR-001 | لایه‌بندی داخلی هر app بر اساس domain/application/infrastructure |
| ADR-002 | SAP infrastructure در سطح project و مشترک بین دامنه‌ها |
| ADR-003 | repository interface در domain |
| ADR-004/018 | SAPTransactionManager تنها gateway نوشتن SAP |
| ADR-005 | settings جدا برای محیط‌ها |
| ADR-006 | audit و soft delete برای business records |
| ADR-008 | SAP portها در `core/sap/ports` |
| ADR-009 | custom user model از اولین migration |
| ADR-010 | reporting تحلیلی به فاز بعد موکول شده است |
| ADR-011 | تنظیم ابزارها در `pyproject.toml` |
| ADR-015 | تزریق SAP client به adapter |
| ADR-016 | transaction manager با callable از adapter مستقل است |
| ADR-017 | mock پیش‌فرض و الزام config صریح برای SAP واقعی |
| ADR-021 | exception hierarchy مشترک و ترجمه در مرز API |
| ADR-022 | PostgreSQL در تمام محیط‌ها externally provision می‌شود؛ Django فقط migration را مدیریت می‌کند |

ADRهای تاریخی مربوط به جزئیات قدیمی API یا frontend در archive نگهداری می‌شوند و تا بازاعتبارسنجی، تصمیم جاری محسوب نمی‌شوند.
