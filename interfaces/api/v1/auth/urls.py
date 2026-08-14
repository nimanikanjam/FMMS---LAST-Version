"""Authentication URL routes."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from interfaces.api.v1.auth.views import (
    CurrentUserView,
    FMMSJWTTokenObtainPairView,
    FMMSJWTTokenRefreshView,
    UserAccountViewSet,
)

router = DefaultRouter()
router.register("users", UserAccountViewSet, basename="user-account")

urlpatterns = [
    path("token/", FMMSJWTTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", FMMSJWTTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    *router.urls,
]
