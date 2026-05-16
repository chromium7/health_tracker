"""URL routes for the documents app."""

from django.urls import path

from health_tracker.apps.documents.views import (
    document_list_view,
    document_upload_view,
)

urlpatterns = [
    path("", document_list_view, name="document_list"),
    path("upload/", document_upload_view, name="document_upload"),
]
