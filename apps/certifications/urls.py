from django.urls import path

from apps.certifications import views

app_name = "certifications"

urlpatterns = [
    path("", views.certifications_list, name="list"),
]
