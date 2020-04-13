from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'hash-tags', views.HashTagViewSet)

urlpatterns = [
    url(r'^', include(router.urls))
]
