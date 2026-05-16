"""Views for the documents app."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from health_tracker.apps.documents.forms import DocumentUploadForm
from health_tracker.apps.documents.models import Document


@login_required
def document_list_view(request: HttpRequest) -> HttpResponse:
    """List the resolved patient's documents.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered document-list template.
    """
    patient = request.user.get_patient()
    documents = Document.objects.filter(patient=patient)
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents},
    )


@login_required
def document_upload_view(request: HttpRequest) -> HttpResponse:
    """Render and process the document upload form.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered form on GET / invalid POST, or a redirect to the
        document list after a successful upload.
    """
    patient = request.user.get_patient()

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.patient = patient
            document.save()
            return redirect("document_list")
    else:
        form = DocumentUploadForm()

    return render(
        request,
        "documents/document_upload_form.html",
        {"form": form},
    )
