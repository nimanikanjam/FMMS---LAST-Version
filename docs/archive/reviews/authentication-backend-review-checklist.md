<div dir="rtl">

# چک‌لیست اصلاحات بک‌اند اپ Authentication

تاریخ بررسی: ۱۴۰۵/۰۵/۰۲

محدوده بررسی:

- `apps/authentication`
- `interfaces/api/v1/auth`

## وضعیت کلی

امتیاز کلی اپ: **۷.۵ از ۱۰**

| بخش | امتیاز |
| --- | --- |
| معماری | ۷ |
| کیفیت کد | ۸ |
| خوانایی | ۸ |
| رعایت اصول Django | ۸ |
| کارایی | ۷ |
| امنیت | ۷ |
| تست‌پذیری | ۷ |
| مستندسازی | ۷ |

## اعتبارسنجی فعلی

```bash
.venv/bin/ruff check apps/authentication interfaces/api/v1/auth
.venv/bin/pytest tests/integration/api/test_auth_api.py -q
```

آخرین اعتبارسنجی بعد از اصلاحات موارد ۱، ۲، ۳، ۴ و ۷:

- `ruff`: پاس شد.
- `pytest tests/integration/api/test_auth_api.py -q`: ۵ تست پاس شد.

## تغییرات انجام‌شده

موارد زیر انجام شده‌اند:

- claimهای سفارشی `username`، `email`، `full_name` و `role` از JWT حذف شدند. اطلاعات profile همچنان در body پاسخ login و endpoint `/auth/me/` برمی‌گردد.
- برای endpointهای token، scoped throttling اضافه شد:
  - `auth_token_obtain`: نرخ `10/min`
  - `auth_token_refresh`: نرخ `30/min`
- docstring مربوط به `FMMSUserManager` با رفتار واقعی username-based login هماهنگ شد.
- مقدار پیش‌فرض role برای superuser از enum استفاده می‌کند، نه string خام.
- OpenAPI response schema برای فیلد `user` در login از `UserProfileSerializer` استفاده می‌کند.
- تست integration برای اطمینان از minimal JWT claims و throttle scope اضافه شد.

فایل‌های تغییرکرده:

- `interfaces/api/v1/auth/serializers.py`
- `interfaces/api/v1/auth/views.py`
- `apps/authentication/infrastructure/managers.py`
- `config/settings/base.py`
- `tests/integration/api/test_auth_api.py`

## چک‌لیست اصلاحات

### ۱. کاهش claimهای حساس داخل JWT

- [x] انجام شد

شدت: زیاد

محل:

- `interfaces/api/v1/auth/serializers.py:34`
- `interfaces/api/v1/auth/serializers.py:35`
- `interfaces/api/v1/auth/serializers.py:36`
- `interfaces/api/v1/auth/serializers.py:37`

دسته‌بندی: Security، Privacy، JWT

مشکل:

توکن JWT شامل `username`، `email`، `full_name` و `role` است. JWT در کلاینت نگهداری می‌شود و تا زمان expire شدن claimها stale می‌مانند.

راهکار:

داخل JWT فقط claimهای ضروری و پایدار مثل `user_id` و شاید `role_version` نگهداری شود. اطلاعات profile از `/me/` خوانده شود.

معیار پذیرش:

- تغییر role یا full_name کاربر وابسته به token قدیمی نباشد.
- تست obtain token با claimهای جدید به‌روزرسانی شود.

### ۲. مشخص کردن سیاست Throttling برای Login و Refresh

- [x] انجام شد

شدت: زیاد

محل:

- `interfaces/api/v1/auth/views.py:24`
- `interfaces/api/v1/auth/views.py:35`

دسته‌بندی: Security، DRF

مشکل:

در خود viewهای auth هیچ throttle class مشخص نشده است. اگر تنظیم global پروژه کافی نباشد، endpointهای token در برابر brute-force ضعیف می‌شوند.

راهکار:

برای token obtain و refresh، throttle scope اختصاصی تعریف شود یا در همین viewها `throttle_scope`/`throttle_classes` صریح شود.

معیار پذیرش:

- تست یا تنظیم مستند برای rate limit login وجود داشته باشد.

### ۳. ناهماهنگی docstring manager با رفتار واقعی login

- [x] انجام شد

شدت: کم

محل:

- `apps/authentication/infrastructure/managers.py:22`
- `apps/authentication/infrastructure/models.py:89`
- `interfaces/api/v1/auth/serializers.py:28`

دسته‌بندی: Docstring، Readability

مشکل:

docstring manager می‌گوید email-based authentication، اما مدل `USERNAME_FIELD = "username"` دارد و serializer هم `username_field = "username"` است.

راهکار:

docstring اصلاح شود تا بگوید username-based login با email به عنوان contact field.

معیار پذیرش:

- مستندات manager، model و API login یک روایت واحد داشته باشند.

### ۴. استفاده از Enum به جای string خام برای نقش superuser

- [x] انجام شد

شدت: کم

محل:

- `apps/authentication/infrastructure/managers.py:97`

دسته‌بندی: Python Best Practice، Enum

مشکل:

برای نقش superuser مقدار `"ADMIN"` به صورت string خام تنظیم شده است.

راهکار:

از `FMMSUserRole.ADMIN` استفاده شود.

معیار پذیرش:

- تغییر مقدار enum در آینده باعث جا ماندن string خام نشود.

### ۵. نبود Bulk Profile Reader

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/authentication/domain/interfaces/user_profile_reader.py:15`
- `apps/authentication/infrastructure/user_profile_reader.py:16`

دسته‌بندی: Performance، ISP

مشکل:

Reader فقط `get_profile(user_id)` دارد. مصرف‌کننده‌هایی که لیست DTO غنی می‌کنند مجبورند برای هر کاربر یک query جدا بزنند.

راهکار:

متد `get_profiles(user_ids: set[uuid.UUID]) -> dict[uuid.UUID, UserProfileSummaryDTO]` اضافه شود.

معیار پذیرش:

- enrichment لیستی بتواند batch انجام شود.

### ۶. Service Layer برای Current User وجود ندارد

- [ ] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/auth/views.py:46`
- `interfaces/api/v1/auth/views.py:54`

دسته‌بندی: معماری، SRP

مشکل:

`CurrentUserView` مستقیم `request.user` را serialize می‌کند. الان ساده است، اما اگر profile rule یا enrichment اضافه شود، منطق به view منتقل می‌شود.

راهکار:

در صورت رشد نیازمندی، `GetCurrentUserProfileService` اضافه شود. تا وقتی فقط serialization ساده است، این مورد کم‌ریسک است.

معیار پذیرش:

- هر rule جدید profile خارج از view پیاده شود.

### ۷. Response schema برای user در token دقیق نیست

- [x] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/auth/serializers.py:69`

دسته‌بندی: DRF، Documentation

مشکل:

در `TokenObtainPairResponseSerializer` فیلد `user` به صورت `DictField` مستند شده، در حالی که ساختار واقعی همان `UserProfileSerializer` است.

راهکار:

از nested serializer استفاده شود.

معیار پذیرش:

- OpenAPI schema ساختار دقیق user را نشان دهد.

### ۸. افشای `is_staff` و `is_superuser` در `/me/`

- [ ] انجام شد

شدت: کم

محل:

- `interfaces/api/v1/auth/serializers.py:88`
- `interfaces/api/v1/auth/serializers.py:89`

دسته‌بندی: Security، API Contract

مشکل:

این endpoint برای کاربر authenticated، مقادیر `is_staff` و `is_superuser` را expose می‌کند. این اطلاعات فوق‌حساس نیستند، اما معمولاً role/application permission کافی است.

راهکار:

اگر frontend به این دو فیلد نیاز ندارد، حذف شوند و فقط `role` برگردد.

معیار پذیرش:

- قرارداد frontend بررسی و خروجی `/me/` حداقلی شود.

### ۹. نبود validation صریح role در manager ورودی‌های عادی

- [ ] انجام شد

شدت: متوسط

محل:

- `apps/authentication/infrastructure/managers.py:32`
- `apps/authentication/infrastructure/managers.py:61`

دسته‌بندی: Validation، Django

مشکل:

`extra_fields` مستقیم به model پاس داده می‌شود. اگر role نامعتبر از مسیر غیر-admin وارد شود، خطا فقط در سطح DB/model validation احتمالی مشخص می‌شود.

راهکار:

قبل از ساخت user، role در صورت وجود با `FMMSUserRole.values` validate شود یا `full_clean()` قبل از save اجرا شود.

معیار پذیرش:

- create_user با role نامعتبر خطای کنترل‌شده بدهد.

### ۱۰. تست‌های امنیتی auth محدودند

- [ ] انجام شد

شدت: متوسط

محل:

- `tests/integration/api/test_auth_api.py:18`
- `tests/integration/api/test_auth_api.py:46`

دسته‌بندی: Testability، Security

مشکل:

تست token و `/me/` وجود دارد، اما برای inactive user، claimهای token، schema profile و throttling تستی دیده نشد.

راهکار:

تست‌های auth برای inactive user و minimal JWT claims اضافه شود.

معیار پذیرش:

- inactive user نتواند token بگیرد.
- claimهای مورد انتظار صریح تست شوند.

## اولویت اجرا

1. کاهش claimهای JWT.
2. تعیین throttling login/refresh.
3. تست inactive user و token claims.
4. اصلاح docstring manager.
5. جایگزینی string خام role با enum.
6. دقیق کردن schema فیلد `user`.
7. تصمیم درباره حذف `is_staff` و `is_superuser`.
8. افزودن bulk profile reader.
9. validation صریح role در manager.
10. نگه داشتن هر rule جدید `/me/` بیرون از view.

</div>
