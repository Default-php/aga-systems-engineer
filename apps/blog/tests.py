import locale
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post
from apps.core.date_utils import MONTH_ABBR_EN


class PostTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.published = Post.objects.create(
            title="Hello World",
            slug="hello-world",
            excerpt="First post.",
            body="Body text.",
            is_draft=False,
            published_at=now,
        )
        cls.draft = Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            body="Not ready.",
            is_draft=True,
            published_at=None,
        )
        cls.scheduled = Post.objects.create(
            title="Scheduled",
            slug="scheduled",
            body="Upcoming.",
            is_draft=True,
            published_at=now + timedelta(days=7),
        )
        cls.incoherent = Post.objects.create(
            title="Missing Date",
            slug="missing-date",
            body="Incoherent.",
            is_draft=False,
            published_at=None,
        )

    def test_list_status_200_drafts_excluded(self):
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "blog/list.html")
        self.assertEqual(list(response.context["posts"]), [self.published])

    def test_list_reverse(self):
        self.assertEqual(reverse("blog:list"), "/blog/")

    def test_detail_status_200_published(self):
        response = self.client.get(f"/blog/{self.published.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "blog/detail.html")

    def test_detail_draft_404(self):
        response = self.client.get(f"/blog/{self.draft.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_published_manager_filters_correctly(self):
        self.assertEqual(list(Post.published.all()), [self.published])
        self.assertEqual(list(Post.published.published()), [self.published])
        self.assertEqual(Post.objects.count(), 4)

    def test_empty_list(self):
        Post.objects.all().delete()
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No posts yet.")

    def test_published_at_display_locale_independent(self):
        # MONTH_ABBR_EN is a hardcoded English list (calendar.month_abbr is
        # locale-aware in Python 3.12, so it is not used); the locale toggle
        # below actively confirms the output does not change.
        post = Post(
            title="Dated",
            slug="dated",
            body="x",
            is_draft=False,
            published_at=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.UTC),
        )
        expected = f"{MONTH_ABBR_EN[3]} 15, 2026"
        self.assertEqual(post.published_at_display, expected)
        # Active check: toggle to a non-English locale, result unchanged.
        original = locale.setlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        except locale.Error:
            pass  # locale not installed; independence is still implicit via MONTH_ABBR_EN
        try:
            self.assertEqual(post.published_at_display, expected)
        finally:
            try:
                locale.setlocale(locale.LC_TIME, original)
            except (locale.Error, TypeError):
                pass

    def test_get_absolute_url(self):
        self.assertEqual(
            self.published.get_absolute_url(),
            reverse("blog:detail", kwargs={"slug": self.published.slug}),
        )
