from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_request_limit",
        "monthly_token_limit",
        "is_unlimited",
        "created_at",
    )
    search_fields = ("name",)
