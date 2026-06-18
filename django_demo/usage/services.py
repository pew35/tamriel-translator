from decimal import Decimal
from random import randint

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import UsageRecord


INPUT_COST_PER_1M_TOKENS = Decimal("0.75")
OUTPUT_COST_PER_1M_TOKENS = Decimal("4.50")


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> Decimal:
    input_cost = Decimal(input_tokens) * INPUT_COST_PER_1M_TOKENS / Decimal(1_000_000)
    output_cost = Decimal(output_tokens) * OUTPUT_COST_PER_1M_TOKENS / Decimal(1_000_000)
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


def approximate_blended_token_limit(monthly_budget_usd: Decimal) -> int:
    blended_cost_per_1m = (INPUT_COST_PER_1M_TOKENS + OUTPUT_COST_PER_1M_TOKENS) / 2
    return int(monthly_budget_usd / blended_cost_per_1m * Decimal(1_000_000))


def current_month_range():
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if month_start.month == 12:
        next_month = month_start.replace(
            year=month_start.year + 1,
            month=1,
        )
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    return month_start, next_month


def record_mock_usage(user, request_type: str) -> UsageRecord:
    if request_type == UsageRecord.RequestType.SCREENSHOT:
        input_tokens = randint(1200, 2200)
        output_tokens = randint(180, 360)
    else:
        input_tokens = randint(220, 380)
        output_tokens = randint(80, 160)

    return UsageRecord.objects.create(
        user=user,
        request_type=request_type,
        model_name="gpt-5.4-mini-mock",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens),
    )


def monthly_usage_for_user(user):
    month_start, next_month = current_month_range()
    records = UsageRecord.objects.filter(
        user=user,
        created_at__gte=month_start,
        created_at__lt=next_month,
    )

    return records.aggregate(
        request_count=Count("id"),
        input_tokens=Coalesce(Sum("input_tokens"), 0),
        output_tokens=Coalesce(Sum("output_tokens"), 0),
        total_tokens=Coalesce(Sum("total_tokens"), 0),
        estimated_cost_usd=Coalesce(Sum("estimated_cost_usd"), Decimal("0")),
    )


def monthly_usage_by_user():
    month_start, next_month = current_month_range()
    user_model = get_user_model()

    rows = []

    for user in user_model.objects.select_related("profile", "profile__plan").order_by("username"):
        usage = monthly_usage_for_user(user)
        rows.append(
            {
                "user": user,
                "profile": getattr(user, "profile", None),
                **usage,
            }
        )

    return rows
