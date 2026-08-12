from django.contrib import admin

from apps.blog.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "is_draft", "published_at", "created_at"]
    list_filter = ["is_draft"]
    search_fields = ["title", "excerpt", "body"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    list_editable = ["is_draft", "published_at"]
