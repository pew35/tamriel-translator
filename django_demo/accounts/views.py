from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from billing.models import Plan

from .models import UserProfile


BUDGET_CHOICES = (Decimal("5.00"), Decimal("10.00"))


def landing(request):
    if request.user.is_authenticated:
        return redirect("translator")

    return redirect("login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    error = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("translator")

        error = "Invalid username or password."

    return render(request, "accounts/login.html", {"error": error})


@require_http_methods(["GET", "POST"])
def register_view(request):
    error = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        budget = Decimal(request.POST.get("monthly_budget_usd", "5.00"))

        if budget not in BUDGET_CHOICES:
            error = "Choose a valid monthly budget."
        elif not username or not password:
            error = "Username and password are required."
        elif get_user_model().objects.filter(username=username).exists():
            error = "Username already exists."
        else:
            plan, _created = Plan.objects.get_or_create(
                name=f"${budget:.0f} Monthly Tester",
                defaults={
                    "monthly_request_limit": None,
                    "monthly_token_limit": None,
                    "is_unlimited": False,
                },
            )
            user = get_user_model().objects.create_user(
                username=username,
                password=password,
            )
            UserProfile.objects.create(
                user=user,
                plan=plan,
                display_name=username,
                role=UserProfile.Role.USER,
                monthly_budget_usd=budget,
            )
            login(request, user)
            return redirect("translator")

    return render(
        request,
        "accounts/register.html",
        {
            "budget_choices": BUDGET_CHOICES,
            "error": error,
        },
    )


def logout_view(request):
    logout(request)
    return redirect("login")
