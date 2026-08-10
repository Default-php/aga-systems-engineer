from django.test import TestCase
from django.urls import reverse


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
        response = self.client.get(reverse("core:home"))
        projects = response.context["projects"]
        self.assertEqual(len(projects), 3)
        for project in projects:
            self.assertIsInstance(project, dict)
            self.assertIn("title", project)
            self.assertIn("description", project)
            self.assertIn("tags", project)
            self.assertIn("url", project)
            self.assertIsInstance(project["tags"], list)
            self.assertTrue(project["tags"])
            self.assertTrue(all(isinstance(tag, str) for tag in project["tags"]))
