"""UI app routes."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/clean", views.clean_api, name="clean_api"),
]
