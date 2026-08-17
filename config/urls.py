"""
URL configuration for portfolio project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.http import require_GET

from config.sitemaps import BlogSitemap, ProjectSitemap, StaticSitemap


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


sitemaps = {
    "static": StaticSitemap,
    "blog": BlogSitemap,
    "projects": ProjectSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path("", include("apps.core.urls")),
    path("projects/", include("apps.projects.urls")),
    path("skills/", include("apps.skills.urls")),
    path("experience/", include("apps.experience.urls")),
    path("blog/", include("apps.blog.urls")),
    path("contact/", include("apps.contact.urls")),
    path("", include("apps.ai_assistant.urls")),
    path("certifications/", include("apps.certifications.urls")),
]

# Dev-only media serving — Django doesn't serve /media/ automatically. In
# production staticfiles are served by WhiteNoise and media by the web server.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
