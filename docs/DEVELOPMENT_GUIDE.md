# راهنمای توسعه و نگهداری FMMS

## ۱. شروع کار

```bash
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

برای محیط مجازی موجود پروژه می‌توان از `.venv/bin/python` و `.venv/bin/pytest` استفاده کرد. مقدارهای واقعی secret نباید وارد Git، مستندات یا خروجی issue شوند.

PostgreSQL در همه محیط‌ها یک dependency خارجی و از قبل provision‌شده است. Django و Docker Compose دیتابیس را ایجاد نمی‌کنند؛ فقط `migrate` ساختار schema را مدیریت می‌کند. `POSTGRES_HOST` برای اجرای مستقیم Python و `POSTGRES_DOCKER_HOST` برای اتصال کانتینرهاست؛ مقدار پیش‌فرض دومی `host.docker.internal` است.

برای اجرای migration از طریق image برنامه:

```bash
docker compose run --rm app python manage.py migrate
```

## ۲. دستورات روزمره

```bash
make migrate
make test
make test-fast
make test-unit
make test-integration
make lint
make format
make worker
make beat
```

Commandهای عملیاتی سراسری در `infrastructure/operations/management/commands/` قرار می‌گیرند. `infrastructure/database/` یک Python package ساده برای primitiveهای ORM است و نباید فقط برای command discovery به Django app تبدیل شود.

## ۳. تنظیمات محیط

| محیط | settings module |
|---|---|
| Development | `config.settings.development` |
| Test | `config.settings.test` |
| Staging | `config.settings.staging` |
| Production | `config.settings.production` |
| Demo | `config.settings.demo` |

Test settings باید تمام toggleهای SAP را قطعی کند و از `.env` شخصی اثر نپذیرد.

## ۴. ترتیب مطالعه کد برای عضو جدید

1. `docs/PROJECT_OVERVIEW.md`
2. `docs/TECHNICAL_ARCHITECTURE.md`
3. `config/settings/base.py` و `config/urls.py`
4. `interfaces/api/v1/urls.py`
5. یک جریان کوچک در Vehicle یا Driver
6. Fault و Repair
7. `docs/SAP_INTEGRATION_GUIDE.md`
8. Mock client، یک OData adapter و یک BAPI adapter
9. SAPTransactionManager و taskهای Celery
10. `docs/ENGINEERING_BACKLOG.md`

## ۵. Workflow توسعه

- `main`: فقط کد قابل انتشار
- `develop`: integration branch، در صورت استفاده تیم
- `feat/<scope>-<description>`: قابلیت
- `fix/<scope>-<description>`: رفع باگ
- `hotfix/<scope>-<description>`: اصلاح فوری Production

Commitها از Conventional Commits پیروی کنند:

```text
feat(vehicle): add assignment history filter
fix(sap): claim failed transaction before retry
docs(architecture): record identity provider decision
test(auth): cover driver object authorization
```

Push مستقیم و force push به branchهای محافظت‌شده، commit secret و merge با تست ناموفق ممنوع است.

## ۶. Definition of Done

- رفتار و acceptance criteria مشخص است.
- business rule در domain/application قرار دارد.
- authorization نقش و object scope بررسی شده است.
- transaction boundary کوتاه و مشخص است.
- migration و rollback/data impact بررسی شده است.
- unit و integration test مرتبط وجود دارد.
- lint، type check، migration check و tests عبور می‌کنند.
- API schema در صورت تغییر endpoint به‌روز است.
- سند canonical مرتبط به‌روز شده است.
- secret یا payload حساس در log و response اضافه نشده است.

## ۷. Quality Gate پیشنهادی CI

```bash
black --check .
isort --check .
ruff check .
mypy .
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run
pytest --cov --cov-fail-under=80
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
docker compose config --quiet
```

حداقل یک job جدا باید با PostgreSQL واقعی اجرا شود تا constraint، lock و queryهای PostgreSQL-specific را بررسی کند.

## ۸. Migration

0. ساخت Database و Role مسئولیت DBA/زیرساخت است و خارج از Django انجام می‌شود.
1. قبل از تغییر، schema و داده‌های موجود بررسی شود.
2. model و migration در یک PR باشند.
3. برای constraint جدید ابتدا داده‌های ناقض گزارش و پاک‌سازی شوند.
4. migration پرهزینه با تخمین lock و زمان اجرا بررسی شود.
5. `makemigrations --check` همیشه باید صفر باشد.

Migration یک مرحله مستقل deployment است و نباید هنگام شروع WSGI، ASGI یا Celery اجرا شود.

## ۹. Release checks و تنظیمات Production

ترتیب release job مستقل از startup پردازش‌هاست:

```bash
python manage.py check --deploy --settings=config.settings.production
python manage.py migrate --noinput --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
```

- Production فایل `.env` محلی را نمی‌خواند و envهای اجباری هنگام import settings اعتبارسنجی می‌شوند.
- `POSTGRES_CONNECT_TIMEOUT` و `POSTGRES_STATEMENT_TIMEOUT_MS` مانع انتظار نامحدود connection/query می‌شوند.
- اتصال پایدار با `POSTGRES_CONN_MAX_AGE` و health check داخلی Django فعال است.
- pool فقط با `POSTGRES_POOL_ENABLED=True` و پس از محاسبه budget اتصال فعال شود؛ dependency آن `psycopg[pool]` است.
- Redis cache در Development fail-open ولی در Production fail-closed است؛ خطای cache در readiness دیده می‌شود.
- static با `ManifestStaticFilesStorage` تولید می‌شود.
- `MEDIA_ROOT` باید mount پایدار، private و backup‌شده باشد؛ Django در Production فایل media را serve نمی‌کند.
- Frontend با JWT header از CORS origins محدود استفاده می‌کند؛ CORS و `CSRF_TRUSTED_ORIGINS` دو تنظیم مستقل‌اند.
- `/api/health/live/` فقط process و `/api/health/ready/` اتصال DB/Redis را بررسی می‌کند.

تصمیم جاری: `FMMSUser.personnel_number` برای مقدار غیرخالی Unique است؛ migration حذف constraint نباید بدون ADR جدید پذیرفته شود.

## ۱۰. تست SAP

- تست و Development به‌صورت پیش‌فرض از Mock استفاده می‌کنند.
- suite باید مقدار `SAP_WRITE` را صریح تعیین کند.
- تست واقعی فقط در SAP غیرProduction و با credential فنی محدود انجام شود.
- هیچ تستی نباید document واقعی را بدون cleanup/approval در SAP PRD بسازد.
- سناریوهای timeout، duplicate، retry exhaustion و SAP-success/DB-failure باید پوشش داده شوند.

## ۱۱. قواعد مستندسازی

اسناد canonical فقط این پنج فایل‌اند:

- `PROJECT_OVERVIEW.md`
- `TECHNICAL_ARCHITECTURE.md`
- `SAP_INTEGRATION_GUIDE.md`
- `ENGINEERING_BACKLOG.md`
- `DEVELOPMENT_GUIDE.md`

قواعد:

1. هر موضوع فقط یک مالک canonical دارد.
2. گزارش review جدید مستقیماً backlog را به‌روزرسانی کند؛ checklist مستقل جدید ساخته نشود.
3. وضعیت کد و هدف آینده با هم مخلوط نشوند.
4. هر ادعای اجرایی با مسیر فایل، تست یا command قابل بررسی باشد.
5. فایل‌های قدیمی در `archive/` فقط سابقه‌اند و نباید به‌روزرسانی شوند.
6. `odata/` منبع خام محافظت‌شده است و نباید تغییر کند.
7. secret، URL حساس داخلی و credential در docs ثبت نشوند.

## ۱۱. به‌روزرسانی Backlog

هر مورد باید شناسه پایدار، شدت، وضعیت، محل، معیار پذیرش و evidence داشته باشد. وضعیت‌های مجاز:

- `Open`
- `In Progress`
- `Blocked`
- `Done`
- `Accepted Risk`
- `Superseded`

بسته شدن مورد فقط با لینک commit/PR و نتیجه validation انجام شود.
