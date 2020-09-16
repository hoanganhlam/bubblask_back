from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.general import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from utils.pusher import pusher_client
from rest_framework import status

client_id = "1c9c426ee079a60ccb9705a970c697bd7b93b6c4b913aee0538e41b94dd00091"
client_secret = "fddd82e02796b3e32cdd6fdc0e5db18c9a2aad787ca7744ecf793b15bc88f651"
redirect_uri = ""
code = ""


class HashTagViewSet(viewsets.ModelViewSet):
    models = models.HashTag
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.HashTagSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        if request.GET.get("for_model"):
            self.queryset = self.queryset.filter(for_models__overlap=[request.GET.get("for_model")])
        return super(HashTagViewSet, self).list(request, *args, **kwargs)


class MessageViewSet(viewsets.ModelViewSet):
    models = models.Message
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.MessageSerializer
    permission_classes = permissions.IsAuthenticatedOrReadOnly,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter]
    lookup_field = 'pk'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        pusher_client.trigger(request.data.get("room"), 'new_message', serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@api_view(['GET'])
def get_unsplash(request):
    search = request.GET.get("search")
    url = "https://api.unsplash.com/search/photos/"
    queries = {
        "client_id": client_id,
        "query": search,
        "per_page": 8
    }
    r = requests.get(url, params=queries)
    return Response(r.json())
