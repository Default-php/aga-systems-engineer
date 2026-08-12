from django.db import models

from apps.core.date_utils import MONTH_ABBR_EN


class Certification(models.Model):
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    date_obtained = models.DateField()
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date_obtained", "display_order", "-id"]
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"

    def __str__(self) -> str:
        return f"{self.name} — {self.issuer}"

    @property
    def date_display(self) -> str:
        # MONTH_ABBR_EN is a fixed English list; calendar.month_abbr is
        # locale-aware in Python 3.12 and must not be used for display.
        return f"{MONTH_ABBR_EN[self.date_obtained.month]} {self.date_obtained.year}"
