"""FMMS root URL configuration."""

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from config.health import liveness, readiness

urlpatterns = [
    path("api/health/live/", liveness, name="health-live"),
    path("api/health/ready/", readiness, name="health-ready"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("interfaces.api.v1.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

if settings.DEBUG or os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".demo"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
