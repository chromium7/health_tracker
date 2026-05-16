"""
URL configuration for health_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from health_tracker.apps.data_imports.views import csv_import_view


urlpatterns = [
    path("admin/import/", csv_import_view, name="data_import"),
    path("admin/", admin.site.urls),
    path("api/", include("health_tracker.api.urls", namespace="api")),
    path(
        "manifest.webmanifest",
        TemplateView.as_view(
            template_name="manifest.webmanifest",
            content_type="application/manifest+json",
        ),
        name="pwa_manifest",
    ),
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js",
            content_type="application/javascript",
        ),
        name="pwa_service_worker",
    ),
    path("", include("health_tracker.apps.users.urls")),
    path("medications/", include("health_tracker.apps.medications.urls")),
    path("hydration/", include("health_tracker.apps.hydration.urls")),
    path("documents/", include("health_tracker.apps.documents.urls")),
    path("", include("health_tracker.apps.metrics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass
