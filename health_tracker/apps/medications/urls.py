"""URL routes for the medications app."""

from django.urls import path

from health_tracker.apps.medications.views import (
    log_medication_taken_view,
    medication_list_view,
    medication_log_delete_view,
    medication_log_detail_view,
    medication_log_edit_view,
    medication_restart_view,
    medication_stop_view,
)

urlpatterns = [
    path("", medication_list_view, name="medication_list"),
    path("log/", log_medication_taken_view, name="log_medication_taken"),
    path("<int:pk>/stop/", medication_stop_view, name="medication_stop"),
    path("<int:pk>/restart/", medication_restart_view, name="medication_restart"),
    path("logs/<int:pk>/", medication_log_detail_view, name="medication_log_detail"),
    path("logs/<int:pk>/edit/", medication_log_edit_view, name="medication_log_edit"),
    path("logs/<int:pk>/delete/", medication_log_delete_view, name="medication_log_delete"),
]
