import calendar

from django.conf import settings
from django.db import models
from django.urls import reverse


class PublishedManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_draft=False, published_at__isnull=False)
            .order_by("-published_at")
        )

    def published(self):
        return self.get_queryset()


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_draft = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_published(self) -> bool:
        return not self.is_draft and self.published_at is not None

    @property
    def published_at_display(self) -> str:
        if self.published_at is None:
            return ""
        d = self.published_at
        return f"{calendar.month_abbr[d.month]} {d.day}, {d.year}"

    def get_absolute_url(self) -> str:
        return reverse("blog:detail", kwargs={"slug": self.slug})
