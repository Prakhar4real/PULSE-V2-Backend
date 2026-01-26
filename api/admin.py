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

# Register other models normally
admin.site.register(Report)
admin.site.register(Mission)
admin.site.register(UserMission)
admin.site.register(Notice)
