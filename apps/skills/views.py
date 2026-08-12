from django.shortcuts import render

from apps.skills.models import Category


def skills_list(request):
    categories = Category.objects.prefetch_related("skills").all()
    has_skills = any(c.skills.exists() for c in categories)
    return render(
        request, "skills/list.html", {"categories": categories, "has_skills": has_skills}
    )
