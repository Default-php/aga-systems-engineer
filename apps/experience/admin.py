from django.contrib import admin

from apps.experience.models import Experience


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "start_date", "end_date", "display_order")
    list_filter = ("organization",)
    search_fields = ("title", "organization", "description")
    date_hierarchy = "start_date"
    list_editable = ("display_order",)
    fields = ("title", "organization", "location", "start_date", "end_date", "description", "display_order")
