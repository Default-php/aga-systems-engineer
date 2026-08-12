from django import forms

from apps.contact.models import ContactSubmission

FIELD_CLASS = (
    "mt-1 block w-full rounded-md border border-edge bg-surface px-3 py-2 text-ink "
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
)


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        min_length=1,
        strip=True,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    subject = forms.CharField(max_length=200, required=False)
    message = forms.CharField(
        min_length=10,
        max_length=5000,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("name", "email", "subject", "message"):
            self.fields[name].widget.attrs.setdefault("class", FIELD_CLASS)

    def clean_website(self):
        website = self.cleaned_data.get("website", "")
        if website:
            # Honeypot filled — treat as a bot; fail with a generic error.
            self.add_error(None, "Something went wrong. Please try again.")
            return ""
        return ""

    def save_to_submission(self, request=None) -> ContactSubmission:
        ip_address = None
        if request is not None:
            ip_address = request.META.get("REMOTE_ADDR")
        return ContactSubmission.objects.create(
            name=self.cleaned_data["name"],
            email=self.cleaned_data["email"],
            subject=self.cleaned_data.get("subject", ""),
            message=self.cleaned_data["message"],
            ip_address=ip_address,
        )
