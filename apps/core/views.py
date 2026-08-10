from django.shortcuts import render

# Phase 2: replace placeholder data with apps.projects queryset.
projects = [
    {
        "title": "AI Assistant Integration",
        "description": "End-to-end integration of AI capabilities into a Django application.",
        "tags": ["Python", "REST APIs", "AI"],
        "url": "#",
    },
    {
        "title": "Cloud Deployment Pipeline",
        "description": "Automated build-and-deploy pipeline for containerized services.",
        "tags": ["Docker", "CI/CD", "Cloud"],
        "url": "#",
    },
    {
        "title": "Infrastructure Automation",
        "description": "Repeatable provisioning and configuration for server fleets.",
        "tags": ["Linux", "Ansible", "Automation"],
        "url": "#",
    },
]


def home(request):
    return render(request, "home.html", {"projects": projects})
