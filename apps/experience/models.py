import calendar

from django.db import models


class Experience(models.Model):
    title = models.CharField(max_length=200, help_text="Role or position.")
    organization = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if current.")
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "display_order", "-id"]
        verbose_name = "Experience entry"
        verbose_name_plural = "Experience entries"

    def __str__(self) -> str:
        end = self.end_date.isoformat() if self.end_date else "present"
        return f"{self.title} @ {self.organization} ({self.start_date.isoformat()} – {end})"

    @property
    def is_current(self) -> bool:
        return self.end_date is None

    @property
    def date_range(self) -> str:
        start = f"{calendar.month_abbr[self.start_date.month]} {self.start_date.year}"
        end = f"{calendar.month_abbr[self.end_date.month]} {self.end_date.year}" if self.end_date else "Present"
        return f"{start} – {end}"
