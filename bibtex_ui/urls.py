"""URL configuration for the BibTeX cleaner UI."""

from django.urls import include, path

urlpatterns = [
    path("", include("ui_app.urls")),
]
