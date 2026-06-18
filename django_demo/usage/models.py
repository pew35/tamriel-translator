from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class UsageRecord(models.Model):
    class RequestType(models.TextChoices):
        TEXT = "text", "Text translation"
        SCREENSHOT = "screenshot", "Screenshot translation"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
    )
    model_name = models.CharField(max_length=80, default="mock-gpt")
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal("0.000000"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUCCESS,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["request_type", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        self.total_tokens = self.input_tokens + self.output_tokens
        super().save(*args, **kwargs)

    @property
    def usage_month(self):
        local_time = timezone.localtime(self.created_at)
        return local_time.strftime("%Y-%m")

    def __str__(self):
        return (
            f"{self.user.username} {self.request_type} "
            f"{self.total_tokens} tokens on {self.usage_month}"
        )
