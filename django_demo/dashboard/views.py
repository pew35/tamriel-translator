from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from usage.models import UsageRecord
from usage.services import (
    approximate_blended_token_limit,
    current_month_range,
    monthly_usage_by_user,
    monthly_usage_for_user,
)


def is_owner(user):
    return user.is_authenticated and (
        user.is_staff or getattr(getattr(user, "profile", None), "role", "") == "owner"
    )


@login_required
def translator_view(request):
    profile = request.user.profile
    monthly_usage = monthly_usage_for_user(request.user)
    recent_records = request.user.usage_records.all()[:8]

    return render(
        request,
        "dashboard/translator.html",
        {
            "profile": profile,
            "monthly_usage": monthly_usage,
            "recent_records": recent_records,
            "approx_token_limit": approximate_blended_token_limit(
                profile.monthly_budget_usd,
            ),
        },
    )


@user_passes_test(is_owner)
def owner_console(request):
    month_start, _next_month = current_month_range()

    return render(
        request,
        "dashboard/owner_console.html",
        {
            "month_label": timezone.localtime(month_start).strftime("%B %Y"),
            "usage_rows": monthly_usage_by_user(),
            "recent_records": UsageRecord.objects.select_related("user").all()[:20],
        },
    )
