from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.certifications.models import Certification


class CertificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cert = Certification.objects.create(
            name="AWS Solutions Architect",
            issuer="Amazon Web Services",
            date_obtained=date(2024, 3, 15),
            credential_id="ABC-123",
            credential_url="https://example.com/verify/abc",
        )
        cls.blank = Certification.objects.create(
            name="Basics",
            issuer="Example Institute",
            date_obtained=date(2021, 1, 1),
        )

    def test_list_status_200(self):
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certifications/list.html")

    def test_url_reverse(self):
        self.assertEqual(reverse("certifications:list"), "/certifications/")

    def test_ordering_desc_by_date_obtained(self):
        Certification.objects.create(
            name="A", issuer="X", date_obtained=date(2022, 1, 1)
        )
        Certification.objects.create(
            name="B", issuer="X", date_obtained=date(2020, 3, 1)
        )
        response = self.client.get("/certifications/")
        dates = [c.date_obtained for c in response.context["certs"]]
        self.assertEqual(
            dates,
            [date(2024, 3, 15), date(2022, 1, 1), date(2021, 1, 1), date(2020, 3, 1)],
        )

    def test_date_display_property(self):
        self.assertEqual(self.cert.date_display, "Mar 2024")

    def test_str_includes_name_and_issuer(self):
        self.assertIn(self.cert.name, str(self.cert))
        self.assertIn(self.cert.issuer, str(self.cert))

    def test_empty_list(self):
        Certification.objects.all().delete()
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No certifications yet.")

    def test_render_shows_credential_id(self):
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC-123")
        self.assertContains(response, "ID:")

    def test_render_shows_credential_url(self):
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://example.com/verify")
        self.assertContains(response, "noopener noreferrer")
        self.assertContains(response, "Verify")

    def test_render_hides_credential_block_when_blank(self):
        Certification.objects.all().delete()
        Certification.objects.create(
            name="Basics", issuer="Example Institute", date_obtained=date(2021, 1, 1)
        )
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("ID:", content)
        self.assertNotIn("Verify", content)

    def test_render_contains_card_content(self):
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AWS Solutions Architect")
        self.assertContains(response, "Amazon Web Services")
        self.assertContains(response, "Mar 2024")
