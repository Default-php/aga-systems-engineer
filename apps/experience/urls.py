from django.urls import path

from apps.experience import views

app_name = "experience"

urlpatterns = [
    path("", views.experience_list, name="list"),
]
