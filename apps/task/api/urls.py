from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet)
router.register(r'boards', views.BoardViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
