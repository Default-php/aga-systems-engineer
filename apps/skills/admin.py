from django.contrib import admin

from apps.skills.models import Category, Skill


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ("name", "level", "display_order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    inlines = [SkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "level", "display_order")
    list_filter = ("category", "level")
    search_fields = ("name",)
    list_editable = ("level", "display_order")
