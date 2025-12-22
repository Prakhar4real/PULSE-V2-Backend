from django.contrib import admin
from .models import Profile, Report, Mission, UserMission

class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'ai_confidence', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description', 'location')

class MissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'points_reward', 'icon') 

# Option A: Keep the decorator
@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'status', 'ai_analysis_preview', 'submitted_at')
    list_filter = ('status', 'mission')
    readonly_fields = ('ai_analysis',) 

    def ai_analysis_preview(self, obj):
        return obj.ai_analysis[:50] + "..." if obj.ai_analysis else "Pending"
    ai_analysis_preview.short_description = "AI Opinion"

# Register the others normally
admin.site.register(Profile)
admin.site.register(Report, ReportAdmin)
admin.site.register(Mission, MissionAdmin)