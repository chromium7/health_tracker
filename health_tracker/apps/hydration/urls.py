"""URL routes for the hydration app."""

from django.urls import path

from health_tracker.apps.hydration.views import (
    drink_delete_view,
    drink_detail_view,
    drink_edit_view,
    log_water_view,
    water_view,
)

urlpatterns = [
    path("", water_view, name="water"),
    path("log/", log_water_view, name="log_water"),
    path("<int:pk>/", drink_detail_view, name="drink_detail"),
    path("<int:pk>/edit/", drink_edit_view, name="drink_edit"),
    path("<int:pk>/delete/", drink_delete_view, name="drink_delete"),
]
