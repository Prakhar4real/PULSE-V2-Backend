from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

# --- PULSE ADMIN CUSTOMIZATION ---
admin.site.site_header = "PULSE Administration"
admin.site.site_title = "PULSE Admin Portal"
admin.site.index_title = "Welcome to the PULSE Command Center"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')), # Points to API app
]

# Allow images to show up during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)