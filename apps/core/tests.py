from django.test import TestCase
from django.urls import reverse

from apps.projects.models import Project


class HomeViewTests(TestCase):
    def test_home_status_code(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_uses_templates(self):
        response = self.client.get(reverse("core:home"))
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "base.html")

    def test_home_url_resolves_root(self):
        self.assertEqual(reverse("core:home"), "/")

    def test_projects_context_contract(self):
        Project.objects.all().delete()
        response = self.client.get(reverse("core:home"))
        self.assertEqual(len(response.context["projects"]), 0)

        project = Project.objects.create(
            title="Sample Project",
            slug="sample-project",
            summary="A short summary.",
            tags_csv="Python, Django",
            featured=False,
        )
        response = self.client.get(reverse("core:home"))
        projects = response.context["projects"]
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].title, project.title)
        self.assertEqual(projects[0].summary, project.summary)
        self.assertEqual(projects[0].tags_list, ["Python", "Django"])
        self.assertTrue(callable(projects[0].get_absolute_url))
        self.assertEqual(
            projects[0].get_absolute_url(),
            reverse("projects:detail", kwargs={"slug": project.slug}),
        )

    def test_home_projects_featured_first(self):
        Project.objects.all().delete()
        Project.objects.create(
            title="One", slug="one", summary="s1", featured=False, display_order=1
        )
        Project.objects.create(
            title="Two", slug="two", summary="s2", featured=False, display_order=2
        )
        Project.objects.create(
            title="Featured", slug="featured", summary="s3", featured=True, display_order=3
        )
        response = self.client.get(reverse("core:home"))
        projects = response.context["projects"]
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].title, "Featured")
