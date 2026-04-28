"""Корневой роутер URL."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.cemeteries.urls")),
    path("", include("apps.users.web_urls")),
    path("", include("apps.marketplace.web_urls")),
    path("api/auth/", include("apps.users.urls")),
    path("api/marketplace/", include("apps.marketplace.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
