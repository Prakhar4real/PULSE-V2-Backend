# api/urls.py
from django.urls import path
from .views import CreateUserView, ReportListCreateView, ReportDetailView, UserProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Auth
    path("user/register/", CreateUserView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="get_token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh"),

    # Reports
    path("reports/", ReportListCreateView.as_view(), name="report-list"),
    path("reports/delete/<int:pk>/", ReportDetailView.as_view(), name="delete-report"),

    # User Profile (The new Gamification link)
    path("user/profile/", UserProfileView.as_view(), name="user-profile"),
]