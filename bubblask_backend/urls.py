"""bubblask_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.urls import path, re_path
from django.conf.urls import include, url
from rest_auth.registration.views import VerifyEmailView, RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^v1/general/', include(('apps.general.api.urls', 'api_general'), namespace='api_general')),
    url(r'^v1/auth/', include(('apps.authentication.api.urls', 'api_auth'))),
    url(r'^v1/task/', include(('apps.task.api.urls', 'api_task'), namespace='api_task')),
    re_path(r'^account-confirm-email/', VerifyEmailView.as_view(),
            name='account_email_verification_sent'),
    re_path(r'^account-confirm-email/(?P<key>[-:\w]+)/$', VerifyEmailView.as_view(),
            name='account_confirm_email'),
]
