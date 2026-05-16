"""Forms for the users app."""

from __future__ import annotations

from django import forms


class LoginForm(forms.Form):
    """Login form accepting a username and a 4-digit PIN."""

    username = forms.CharField(max_length=150)
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput,
        label="PIN 4 Digit",
    )

    def clean_username(self) -> str:
        """Strip surrounding whitespace from the submitted username.

        Returns:
            The cleaned username.
        """
        return self.cleaned_data["username"].strip()

    def clean_pin(self) -> str:
        """Validate that the PIN is exactly 4 numeric digits.

        Returns:
            The cleaned PIN.

        Raises:
            forms.ValidationError: When the PIN contains non-digit
                characters.
        """
        pin = self.cleaned_data["pin"]
        if not pin.isdigit():
            raise forms.ValidationError("PIN hanya boleh berisi angka.")
        return pin
