from django.urls import path

from apps.skills import views

app_name = "skills"

urlpatterns = [
    path("", views.skills_list, name="list"),
]
