from django.contrib import admin

from .models import UsageRecord


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "request_type",
        "model_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "status",
    )
    list_filter = ("request_type", "status", "model_name", "created_at")
    search_fields = ("user__username",)
