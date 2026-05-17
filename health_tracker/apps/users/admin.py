"""Django admin configuration for the users app."""

from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from health_tracker.apps.users.models import User


class UserAdminForm(forms.ModelForm):
    """Admin ModelForm enforcing role integrity for User accounts."""

    class Meta:
        model = User
        fields = "__all__"

    def clean(self) -> dict:
        """Validate cross-field role and ``patient_profile`` constraints.

        Returns:
            The cleaned form data.

        Raises:
            forms.ValidationError: When a caregiver lacks a
                ``patient_profile`` or a patient has one assigned.
        """
        cleaned = super().clean()
        role = cleaned.get("role")
        patient_profile = cleaned.get("patient_profile")
        if role == User.Role.CAREGIVER and patient_profile is None:
            raise forms.ValidationError("A caregiver must have a patient_profile assigned.")
        if role == User.Role.PATIENT and patient_profile is not None:
            raise forms.ValidationError("A patient must not have a patient_profile assigned.")
        return cleaned


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin for the custom ``User`` model.

    Adds a ``HealthTracker`` fieldset exposing ``role``, ``pin``, and
    ``patient_profile`` to both the create and edit pages.
    """

    form = UserAdminForm

    list_display = ["username", "role", "patient_profile", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["username"]

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("HealthTracker", {"fields": ("role", "pin", "patient_profile", "daily_water_target_ml")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("HealthTracker", {"fields": ("role", "pin", "patient_profile", "daily_water_target_ml")}),
    )
