from django.shortcuts import get_object_or_404, render

from apps.projects.models import Project


def project_list(request):
    projects = Project.objects.all()
    return render(request, "projects/list.html", {"projects": projects})


def project_detail(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    return render(request, "projects/detail.html", {"project": project})
