from django.contrib import admin
from django.urls import path, include 
from django.conf import settings 
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('uploads/', include('apps.uploads.urls', namespace='uploads')),
    path('api/ai/', include('apps.ai_processing.urls', namespace='ai_processing')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)