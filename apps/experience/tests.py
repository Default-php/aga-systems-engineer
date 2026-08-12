from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.experience.models import Experience


class ExperienceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.current = Experience.objects.create(
            title="Senior Engineer",
            organization="ACME Corp",
            location="Remote",
            start_date=date(2024, 1, 1),
            end_date=None,
            description="Leading platform work.",
        )
        cls.past = Experience.objects.create(
            title="Engineer",
            organization="Globex",
            location="New York",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 6, 1),
            description="Built APIs.",
        )

    def test_list_status_200(self):
        response = self.client.get("/experience/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "experience/list.html")

    def test_url_reverse(self):
        self.assertEqual(reverse("experience:list"), "/experience/")

    def test_ordering_desc_by_start_date(self):
        Experience.objects.create(
            title="Junior", organization="OldCo", start_date=date(2023, 1, 1)
        )
        Experience.objects.create(
            title="Intern", organization="OldCo", start_date=date(2020, 6, 1)
        )
        Experience.objects.create(
            title="Lead", organization="NewCo", start_date=date(2024, 2, 1)
        )
        response = self.client.get("/experience/")
        starts = [e.start_date for e in response.context["entries"]]
        self.assertEqual(
            starts,
            [date(2024, 2, 1), date(2024, 1, 1), date(2023, 1, 1), date(2020, 6, 1), date(2020, 1, 1)],
        )

    def test_is_current_true_when_end_date_null(self):
        self.assertTrue(self.current.is_current)
        self.assertFalse(self.past.is_current)

    def test_date_range_property(self):
        self.assertEqual(self.past.date_range, "Jan 2020 – Jun 2022")
        self.assertEqual(self.current.date_range, "Jan 2024 – Present")

    def test_empty_list(self):
        Experience.objects.all().delete()
        response = self.client.get("/experience/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No experience yet.")

    def test_str_includes_role_and_org(self):
        self.assertIn(self.current.title, str(self.current))
        self.assertIn(self.current.organization, str(self.current))


class ExperienceRenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.current = Experience.objects.create(
            title="Senior Engineer",
            organization="ACME Corp",
            start_date=date(2024, 1, 1),
            end_date=None,
            description="Leading platform work.",
        )
        cls.past = Experience.objects.create(
            title="Engineer",
            organization="Globex",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 6, 1),
            description="Built APIs.",
        )
        cls.multi = Experience.objects.create(
            title="Analyst",
            organization="Initech",
            start_date=date(2018, 3, 1),
            end_date=date(2019, 5, 1),
            description="First paragraph.\n\nSecond paragraph.",
        )

    def test_render_contains_date_range_and_title(self):
        response = self.client.get("/experience/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jan 2020 – Jun 2022")
        self.assertContains(response, "Engineer")
        self.assertContains(response, "Globex")

    def test_render_shows_current_badge(self):
        response = self.client.get("/experience/")
        self.assertContains(response, "Current")

    def test_render_linebreaks_description(self):
        response = self.client.get("/experience/")
        self.assertContains(response, "<p>First paragraph.</p>")
        self.assertContains(response, "<p>Second paragraph.</p>")
