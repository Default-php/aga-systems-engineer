import logging

from django.shortcuts import redirect, render
from django.urls import reverse

from apps.contact.emails import send_contact_email
from apps.contact.forms import ContactForm

logger = logging.getLogger(__name__)


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            submission = form.save_to_submission(request=request)
            try:
                send_contact_email(submission)
            except Exception:
                # Submission is already persisted; admin can review and retry manually.
                # Don't expose internals to the user.
                logger.exception(
                    "Failed to send contact email for submission id=%s", submission.pk
                )
            return redirect(reverse("contact:contact") + "?sent=1")
    else:
        form = ContactForm()
    sent = request.GET.get("sent") == "1"
    return render(request, "contact/form.html", {"form": form, "sent": sent})
