from django.shortcuts import render

from apps.experience.models import Experience


def experience_list(request):
    entries = Experience.objects.all()
    return render(request, "experience/list.html", {"entries": entries})
