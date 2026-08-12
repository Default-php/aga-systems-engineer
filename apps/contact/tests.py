from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.contact.models import ContactSubmission

VALID_DATA = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "subject": "Hello",
    "message": "This is a sufficiently long message body.",
    "website": "",
}


class ContactTests(TestCase):
    def test_get_renders_empty_form(self):
        response = self.client.get("/contact/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/form.html")
        self.assertFalse(response.context["form"].is_bound)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CONTACT_RECIPIENT_EMAIL="test-recipient@example.com",
        DEFAULT_FROM_EMAIL="test-from@example.com",
    )
    def test_post_valid_creates_submission_and_redirects(self):
        response = self.client.post("/contact/", VALID_DATA)
        self.assertRedirects(response, "/contact/?sent=1")
        self.assertEqual(ContactSubmission.objects.count(), 1)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.name, "Jane Doe")
        self.assertEqual(submission.email, "jane@example.com")

    def test_post_invalid_no_submission(self):
        response = self.client.post(
            "/contact/", {"name": "", "email": "", "message": "short"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertFalse(response.context["form"].is_valid())

    def test_post_invalid_email(self):
        response = self.client.post(
            "/contact/",
            {**VALID_DATA, "email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Enter a valid email address.")

    def test_honeypot_blocks_bot(self):
        response = self.client.post(
            "/contact/", {**VALID_DATA, "website": "http://spam.example"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Something went wrong. Please try again.")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CONTACT_RECIPIENT_EMAIL="test-recipient@example.com",
        DEFAULT_FROM_EMAIL="test-from@example.com",
    )
    def test_post_valid_sends_email(self):
        self.client.post("/contact/", VALID_DATA)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Hello")
        self.assertIn("This is a sufficiently long message body.", message.body)
        self.assertEqual(message.to, ["test-recipient@example.com"])
        self.assertEqual(message.from_email, "test-from@example.com")

    @patch("apps.contact.views.send_contact_email")
    def test_post_email_failure_still_redirects(self, mock_send):
        mock_send.side_effect = OSError("smtp unreachable")
        response = self.client.post("/contact/", VALID_DATA)
        self.assertEqual(response.status_code, 302)
        self.assertIn("sent=1", response.url)
        self.assertEqual(mock_send.call_count, 1)
        submission = ContactSubmission.objects.get()
        self.assertEqual(mock_send.call_args[0][0].pk, submission.pk)
        self.assertEqual(ContactSubmission.objects.count(), 1)

    def test_success_state_shows_thanks(self):
        response = self.client.get("/contact/?sent=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "message received")
        self.assertContains(response, "Send another")
