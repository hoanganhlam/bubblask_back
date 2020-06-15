from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'hash-tags', views.HashTagViewSet)
router.register(r'workspaces', views.WSViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^unsplash', views.get_unsplash),
    url(r'^workspaces/(?P<pk>[0-9]+)/join/$', views.join_ws),
    url(r'^workspaces/(?P<pk>[0-9]+)/members/$', views.ws_members),
]
