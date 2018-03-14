"""aproj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from apimas_django import adapter
from aproj.spec import APP_CONFIG, DEPLOY_CONFIG

app_spec = adapter.configure_apimas_app(APP_CONFIG)
deployment_spec = adapter.configure_spec(app_spec, DEPLOY_CONFIG)

api_urls = adapter.construct_views(deployment_spec)

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
]
urlpatterns.extend(api_urls)

urls_media = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns.extend(urls_media)
