from django.shortcuts import render

from apps.certifications.models import Certification


def certifications_list(request):
    certs = Certification.objects.all()
    return render(request, "certifications/list.html", {"certs": certs})
