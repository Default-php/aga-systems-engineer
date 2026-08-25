from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import QuerySet
from django.test import TestCase
from django.urls import reverse

from apps.projects.models import Project


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Sample Project",
            slug="sample-project",
            summary="A short summary.",
            tags_csv=" Python, Django ,  REST ",
            featured=False,
        )

    def test_tags_list_split(self):
        self.assertEqual(self.project.tags_list, ["Python", "Django", "REST"])

    def test_get_absolute_url(self):
        self.assertEqual(
            self.project.get_absolute_url(),
            reverse("projects:detail", kwargs={"slug": self.project.slug}),
        )


class ProjectViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Sample Project",
            slug="sample-project",
            summary="A short summary.",
            tags_csv="Python, Django, REST",
            featured=False,
        )

    def test_list_status_200(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/list.html")

    def test_list_context_shape(self):
        response = self.client.get("/projects/")
        self.assertIsInstance(response.context["projects"], QuerySet)
        self.assertEqual(
            response.context["projects"].first().tags_list,
            ["Python", "Django", "REST"],
        )

    def test_list_empty(self):
        Project.objects.all().delete()
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)

    def test_detail_status_200(self):
        response = self.client.get(f"/projects/{self.project.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/detail.html")

    def test_detail_404(self):
        response = self.client.get("/projects/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_url_reverse(self):
        self.assertEqual(reverse("projects:list"), "/projects/")
        self.assertEqual(
            reverse("projects:detail", kwargs={"slug": "x"}), "/projects/x/"
        )


class ProjectImageRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.with_image = Project.objects.create(
            title="With image",
            slug="with-image",
            summary="Has image",
            image=SimpleUploadedFile(
                "with.png", b"fake-png-bytes", content_type="image/png"
            ),
        )
        cls.without_image = Project.objects.create(
            title="Without image",
            slug="without-image",
            summary="No image",
        )

    @classmethod
    def tearDownClass(cls):
        # Remove only the image files this class created (SimpleUploadedFile
        # writes them under MEDIA_ROOT). Never touch other media.
        from pathlib import Path

        projects_dir = Path(settings.MEDIA_ROOT) / "projects"
        if projects_dir.exists():
            for child in projects_dir.glob("with*.png"):
                child.unlink(missing_ok=True)
        super().tearDownClass()

    def test_listing_renders_imgs_for_projects_with_image_only(self):
        url = reverse("projects:list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # One project has an image, one doesn't. Exactly one <img> in the listing.
        self.assertEqual(body.count("<img"), 1)

    def test_card_renders_img_when_image_present(self):
        url = reverse("projects:list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'src="{self.with_image.image.url}"')
        self.assertContains(resp, f'alt="{self.with_image.title}"')

    def test_detail_renders_img_when_image_present(self):
        resp = self.client.get(self.with_image.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'src="{self.with_image.image.url}"')

    def test_detail_no_img_when_image_absent(self):
        resp = self.client.get(self.without_image.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "<img")
