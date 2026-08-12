from django.test import TestCase
from django.urls import reverse

from apps.skills.models import Category, Skill


class SkillTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Backend", slug="backend", display_order=0
        )
        cls.skill = Skill.objects.create(
            name="Django", category=cls.category, level=Skill.ADVANCED
        )

    def test_list_status_200(self):
        response = self.client.get("/skills/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "skills/list.html")

    def test_url_reverse(self):
        self.assertEqual(reverse("skills:list"), "/skills/")

    def test_level_display_property(self):
        self.assertEqual(self.skill.level_display, self.skill.get_level_display())

    def test_ordering_categories(self):
        Category.objects.create(name="Alpha", slug="alpha", display_order=5)
        Category.objects.create(name="Beta", slug="beta", display_order=5)
        Category.objects.create(name="Zeta", slug="zeta", display_order=10)
        response = self.client.get("/skills/")
        categories = list(response.context["categories"])
        self.assertEqual(
            [c.display_order for c in categories], [0, 5, 5, 10]
        )
        self.assertEqual(
            [c.name for c in categories if c.display_order == 5],
            ["Alpha", "Beta"],
        )

    def test_ordering_skills_within_category(self):
        cat = Category.objects.create(name="Data", slug="data", display_order=1)
        Skill.objects.create(name="SQL", category=cat, display_order=3)
        Skill.objects.create(name="Pandas", category=cat, display_order=1)
        Skill.objects.create(name="Spark", category=cat, display_order=2)
        response = self.client.get("/skills/")
        data_cat = next(c for c in response.context["categories"] if c.slug == "data")
        self.assertEqual(
            [s.display_order for s in data_cat.skills.all()], [1, 2, 3]
        )

    def test_empty_list(self):
        Category.objects.all().delete()
        response = self.client.get("/skills/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No skills yet.")

    def test_skill_str(self):
        self.assertIn(self.skill.name, str(self.skill))
        self.assertIn(self.skill.get_level_display(), str(self.skill))
