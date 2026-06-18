from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "role",
        "plan",
        "monthly_budget_usd",
        "created_at",
    )
    list_filter = ("role", "plan")
    search_fields = ("user__username", "display_name")
