from django.contrib import admin
from .models import Profile, Report, Mission, UserMission, Notice

# --- 1. Simple Registrations ---

admin.site.register(Profile)
admin.site.register(Mission)

# --- 2. Custom Admin for Reports ---
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'ai_confidence', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description')

# --- 3. Custom Admin for User Missions ---

@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'status', 'submitted_at')
    list_filter = ('status',)

# --- 4. Custom Admin for Notices ---
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_pinned', 'created_at')
    list_filter = ('is_pinned', 'created_at')
    search_fields = ('title', 'content')