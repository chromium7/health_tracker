"""User model for HealthTracker.

A custom AbstractUser subclass that swaps password-based auth for a
4-digit PIN and adds a patient/caregiver role distinction.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with PIN auth and a patient/caregiver role.

    Accounts are created and managed exclusively via Django Admin.

    Attributes:
        pin: 4-digit numeric string used for login.
        role: Either ``Role.PATIENT`` or ``Role.CAREGIVER``.
        patient_profile: For caregivers only - the patient they monitor.
            Always ``None`` for patients.
    """

    class Role(models.TextChoices):
        """Roles a HealthTracker account can hold."""

        PATIENT = "patient", "Patient"
        CAREGIVER = "caregiver", "Caregiver"

    pin = models.CharField(
        max_length=4,
        help_text="4-digit numeric PIN used for login.",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    patient_profile = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caregivers",
        help_text="Caregivers only: the patient this account monitors.",
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["pin", "role"]

    @property
    def is_patient(self) -> bool:
        """Return ``True`` when this user's role is patient."""
        return self.role == self.Role.PATIENT

    @property
    def is_caregiver(self) -> bool:
        """Return ``True`` when this user's role is caregiver."""
        return self.role == self.Role.CAREGIVER

    def get_patient(self) -> "User":
        """Resolve and return the relevant patient ``User`` object.

        For a patient account this returns ``self``. For a caregiver
        account this returns ``self.patient_profile``.

        All views must call this method rather than accessing
        ``request.user`` directly for health-data queries.

        Returns:
            The patient ``User`` instance.

        Raises:
            ValueError: If this user is a caregiver with no
                ``patient_profile`` assigned (indicates an admin
                misconfiguration).
        """
        if self.is_patient:
            return self
        if self.patient_profile_id is None:
            raise ValueError(f"Caregiver '{self.username}' has no patient_profile assigned.")
        return self.patient_profile

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
