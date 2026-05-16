"""URL routes for the users app."""

from django.urls import path

from health_tracker.apps.users.views import login_view, logout_view

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]
