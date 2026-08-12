from django.contrib import admin

from apps.certifications.models import Certification


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "date_obtained", "display_order")
    list_filter = ("issuer",)
    search_fields = ("name", "issuer", "credential_id")
    date_hierarchy = "date_obtained"
    list_editable = ("display_order",)
    fields = ("name", "issuer", "date_obtained", "credential_id", "credential_url", "display_order")
