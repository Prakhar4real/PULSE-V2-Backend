from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, 
    UserProfileView, 
    ProfileUpdateView, 
    ReportListCreateView, 
    ReportDetailView, 
    ReportDeleteView, 
    AIChatView, 
    GamificationViewSet,
    NoticeListCreateView,
    TrafficStatsView  
)

urlpatterns = [
    # --- AUTHENTICATION ---
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', RegisterView.as_view(), name='register'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    
    # PROFILE UPDATE URL
    path('user/update/', ProfileUpdateView.as_view(), name='user-update'),

    # --- NOTICES ---
    path('notices/', NoticeListCreateView.as_view(), name='notice-list'),

    # --- REPORTS ---
    path('reports/', ReportListCreateView.as_view(), name='report-list-create'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report-detail'),
    path('reports/<int:pk>/delete/', ReportDeleteView.as_view(), name='report-delete'),

    # --- TRAFFIC STATS ---
    path('traffic-stats/', TrafficStatsView.as_view(), name='traffic-stats'), 

    # --- AI CHAT ---
    path('ai/chat/', AIChatView.as_view(), name='ai-chat'),

    # --- GAMIFICATION ---
    path('leaderboard/', GamificationViewSet.as_view({'get': 'leaderboard'}), name='leaderboard'),
    path('missions/', GamificationViewSet.as_view({'get': 'missions'}), name='missions'),
    path('missions/<int:pk>/join/', GamificationViewSet.as_view({'post': 'join'}), name='mission-join'),
    path('missions/<int:pk>/submit_proof/', GamificationViewSet.as_view({'post': 'submit_proof'}), name='mission-submit-proof'),
]