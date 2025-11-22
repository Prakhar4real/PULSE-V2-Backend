# api/urls.py

from django.urls import path
from .views import CreateUserView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # The Register Endpoint
    path("user/register/", CreateUserView.as_view(), name="register"),
    
    # The Login Endpoint (This is the one you are trying to test!)
    path("token/", TokenObtainPairView.as_view(), name="get_token"),
    
    # The Refresh Endpoint
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh"),
]