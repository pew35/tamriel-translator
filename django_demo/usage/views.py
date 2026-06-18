from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import UsageRecord
from .services import record_mock_usage


@login_required
@require_POST
def mock_text_usage(request):
    record_mock_usage(request.user, UsageRecord.RequestType.TEXT)
    return redirect("translator")


@login_required
@require_POST
def mock_screenshot_usage(request):
    record_mock_usage(request.user, UsageRecord.RequestType.SCREENSHOT)
    return redirect("translator")
