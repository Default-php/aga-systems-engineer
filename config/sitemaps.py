from django.contrib.sitemaps import Sitemap
from django.urls import reverse_lazy

from apps.blog.models import Post
from apps.projects.models import Project


class StaticSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return [
            "core:home",
            "projects:list",
            "skills:list",
            "experience:list",
            "certifications:list",
            "contact:contact",
        ]

    def location(self, item):
        return reverse_lazy(item)


class BlogSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Post.published.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class ProjectSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Project.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()
