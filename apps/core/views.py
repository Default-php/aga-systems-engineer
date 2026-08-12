from django.shortcuts import render

from apps.projects.models import Project


def home(request):
    featured = list(
        Project.objects.filter(featured=True).order_by("display_order", "-created_at")[:3]
    )
    projects = featured or list(
        Project.objects.all().order_by("display_order", "-created_at")[:3]
    )
    return render(request, "home.html", {"projects": projects})
