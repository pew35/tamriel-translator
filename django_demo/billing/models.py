from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=80, unique=True)
    monthly_request_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_token_limit = models.PositiveIntegerField(null=True, blank=True)
    is_unlimited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
