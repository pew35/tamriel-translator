from django.conf import settings
from django.db import models

from billing.models import Plan


class UserProfile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        OWNER = "owner", "Owner"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    display_name = models.CharField(max_length=80, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    monthly_budget_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=10,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name or self.user.username
