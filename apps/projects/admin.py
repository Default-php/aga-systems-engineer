from django.contrib import admin

from apps.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "featured", "display_order", "updated_at"]
    list_filter = ["featured"]
    search_fields = ["title", "summary", "description"]
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ["featured", "display_order"]
    ordering = ["display_order", "-created_at"]
