from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Report, Profile, Mission, UserMission, Notice

# 1. "Inline" admin view for Profile
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Info (Phone, Level, Points)'
    fk_name = 'user'
    # Show these fields
    fields = ('phone_number', 'level', 'points', 'bio', 'profile_picture')

# 2. Extend the standard User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    
    list_display = ('username', 'email', 'get_level', 'get_points', 'is_staff')

    def get_level(self, instance):
        return instance.profile.level
    get_level.short_description = 'Rank'

    def get_points(self, instance):
        return instance.profile.points
    get_points.short_description = 'XP'

# 3. Re-register User with the new settings
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# NEW ADMIN CLASSES FOR TIMESTAMPS

# 4. Custom Admin for Reports
class ReportAdmin(admin.ModelAdmin):
    # This adds the time to the main table list!
    list_display = ('title', 'user', 'status', 'created_at') 
    
    # This forces the time to show up on the detailed view page
    readonly_fields = ('created_at', 'ai_analysis', 'ai_confidence')

# 5. Custom Admin for User Missions
class UserMissionAdmin(admin.ModelAdmin):
    # This adds the time to the main table list!
    list_display = ('user', 'mission', 'status', 'submitted_at')
    
    # This forces the time to show up on the detailed view page
    readonly_fields = ('submitted_at', 'ai_analysis')


# REGISTER MODELS

# Register with our new custom admin classes
admin.site.register(Report, ReportAdmin)
admin.site.register(UserMission, UserMissionAdmin)

# Register the rest normally
admin.site.register(Mission)
admin.site.register(Notice)