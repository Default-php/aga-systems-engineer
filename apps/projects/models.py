from django.db import models


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=300, help_text="Short card description (~150 chars).")
    description = models.TextField(blank=True, help_text="Full description for the detail page.")
    image = models.ImageField(upload_to="projects/", blank=True, null=True)
    repo_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)
    tags_csv = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags.")
    display_order = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False, help_text="Surface on the home page.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def tags_list(self) -> list[str]:
        return [t.strip() for t in self.tags_csv.split(",") if t.strip()]

    def get_absolute_url(self) -> str:
        from django.urls import reverse
        return reverse("projects:detail", kwargs={"slug": self.slug})
