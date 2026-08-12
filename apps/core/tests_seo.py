import re

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.blog.models import Post
from apps.projects.models import Project
from apps.certifications.models import Certification


class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.post = Post.objects.create(
            title="Published Post",
            slug="published-post",
            body="Body.",
            is_draft=False,
            published_at=timezone.now(),
        )
        cls.draft = Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            body="Secret.",
            is_draft=True,
            published_at=None,
        )
        cls.project = Project.objects.create(
            title="Sample Project",
            slug="sample-project",
            summary="A short summary.",
        )
        cls.cert = Certification.objects.create(
            name="AWS Solutions Architect",
            issuer="Amazon Web Services",
            date_obtained=timezone.now().date(),
        )

    def test_sitemap_renders_xml(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("xml", response["Content-Type"])
        content = response.content.decode()
        for expected in ("/", "/projects/", "/skills/", "/experience/", "/certifications/", "/contact/"):
            self.assertIn(expected, content)
        self.assertIn("/blog/published-post/", content)
        self.assertIn("/projects/sample-project/", content)
        for forbidden in ("/admin/", "/static/", "/media/"):
            self.assertNotIn(forbidden, content)
        self.assertNotIn("/blog/draft-post/", content)
        self.assertEqual(content.count("/certifications/"), 1)

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        content = response.content.decode()
        self.assertIn("User-agent: *", content)
        self.assertIn("Disallow: /admin/", content)

    def test_home_contains_og_tags(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('property="og:title"', content)
        self.assertIn('property="og:description"', content)
        self.assertIn('name="twitter:card"', content)
        self.assertIn('rel="canonical"', content)

        canonical = re.search(
            r'<link\s+rel="canonical"\s+href="([^"]+)"', content
        )
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical.group(1), "http://testserver/")

        og_url = re.search(
            r'<meta\s+property="og:url"\s+content="([^"]+)"', content
        )
        self.assertIsNotNone(og_url)
        self.assertEqual(og_url.group(1), "http://testserver/")

        og_desc = re.search(
            r'<meta\s+property="og:description"\s+content="([^"]+)"', content
        )
        self.assertIsNotNone(og_desc)
        self.assertTrue(og_desc.group(1).strip())

    def test_meta_description_default_matches_settings(self):
        response = self.client.get("/")
        content = response.content.decode()
        match = re.search(
            r'<meta\s+name="description"\s+content="([^"]+)"', content
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), settings.SITE_DESCRIPTION)
