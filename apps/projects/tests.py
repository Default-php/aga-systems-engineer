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
