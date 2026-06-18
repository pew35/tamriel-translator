from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import UserProfile
from billing.models import Plan


class Command(BaseCommand):
    help = "Create the Peggy owner demo account."

    def handle(self, *args, **options):
        plan, _created = Plan.objects.get_or_create(
            name="Unlimited Owner Tester",
            defaults={
                "monthly_request_limit": None,
                "monthly_token_limit": None,
                "is_unlimited": True,
            },
        )

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="peggy",
            defaults={
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password("123")
        user.is_staff = True
        user.is_superuser = True
        user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "plan": plan,
                "display_name": "Peggy",
                "role": UserProfile.Role.OWNER,
                "monthly_budget_usd": Decimal("10.00"),
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} demo owner account: peggy / 123",
            ),
        )
