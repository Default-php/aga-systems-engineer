from django.shortcuts import render

from apps.skills.models import Category


def skills_list(request):
    categories = Category.objects.prefetch_related("skills").all()
    return render(request, "skills/list.html", {"categories": categories})
