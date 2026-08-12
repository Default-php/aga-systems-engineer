from django.contrib import admin

from apps.contact.models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at", "contacted")
    list_filter = ("contacted",)
    search_fields = ("name", "email", "message")
    list_editable = ("contacted",)
