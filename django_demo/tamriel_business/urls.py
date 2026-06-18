"""
URL configuration for tamriel_business project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from accounts import views as accounts_views
from dashboard import views as dashboard_views
from usage import views as usage_views

urlpatterns = [
    path('', accounts_views.landing, name='landing'),
    path('login/', accounts_views.login_view, name='login'),
    path('register/', accounts_views.register_view, name='register'),
    path('logout/', accounts_views.logout_view, name='logout'),
    path('translator/', dashboard_views.translator_view, name='translator'),
    path('console/', dashboard_views.owner_console, name='owner_console'),
    path('usage/mock/text/', usage_views.mock_text_usage, name='mock_text_usage'),
    path(
        'usage/mock/screenshot/',
        usage_views.mock_screenshot_usage,
        name='mock_screenshot_usage',
    ),
    path('admin/', admin.site.urls),
]
