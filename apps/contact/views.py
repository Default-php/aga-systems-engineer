from django.shortcuts import redirect, render
from django.urls import reverse

from apps.contact.emails import send_contact_email
from apps.contact.forms import ContactForm


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            submission = form.save_to_submission(request=request)
            send_contact_email(submission)
            return redirect(reverse("contact:contact") + "?sent=1")
    else:
        form = ContactForm()
    sent = request.GET.get("sent") == "1"
    return render(request, "contact/form.html", {"form": form, "sent": sent})
