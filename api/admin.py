from django.contrib import admin
from .models import Report, Profile # <--- Import Profile

admin.site.register(Report)
admin.site.register(Profile) # <--- Register it