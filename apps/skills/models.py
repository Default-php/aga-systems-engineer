from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Skill(models.Model):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    LEVEL_CHOICES = [
        (BEGINNER, "Beginner"),
        (INTERMEDIATE, "Intermediate"),
        (ADVANCED, "Advanced"),
        (EXPERT, "Expert"),
    ]

    name = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="skills")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=INTERMEDIATE)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category__display_order", "display_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_level_display()})"

    @property
    def level_display(self) -> str:
        return self.get_level_display()
