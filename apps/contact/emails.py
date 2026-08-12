from django.conf import settings
from django.core.mail import send_mail

from apps.contact.models import ContactSubmission


def send_contact_email(submission: ContactSubmission) -> int:
    subject = submission.subject or f"Contact form: {submission.name}"
    message = f"From: {submission.name} <{submission.email}>\n\n{submission.message}"
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
    )
