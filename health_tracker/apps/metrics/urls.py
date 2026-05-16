"""URL routes for the metrics app."""

from django.urls import path

from health_tracker.apps.metrics.views import (
    activity_list_view,
    dashboard_view,
    log_metric_view,
    metric_delete_view,
    metric_detail_view,
    metric_edit_view,
)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("activities/", activity_list_view, name="activity_list"),
    path(
        "metrics/log/<str:metric_type>/",
        log_metric_view,
        name="log_metric",
    ),
    path("metrics/<int:pk>/", metric_detail_view, name="metric_detail"),
    path("metrics/<int:pk>/edit/", metric_edit_view, name="metric_edit"),
    path("metrics/<int:pk>/delete/", metric_delete_view, name="metric_delete"),
]
