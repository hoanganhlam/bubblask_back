from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.general import models
from apps.task.models import Board
from apps.authentication.api.serializers import UserReportSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from django.db.models import Q

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


class WSViewSet(viewsets.ModelViewSet):
    models = models.Workspace
    queryset = models.objects.order_by('-id') \
        .prefetch_related("members", "members__profile", "members__profile__media", "board").select_related("user")
    serializer_class = serializers.WSSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['name']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        q = Q()
        if request.GET.get("code"):
            q = q & Q(code=request.GET.get("code"))
        else:
            q = q & Q(is_public=True)
        self.queryset = self.queryset.filter(q)
        return super(WSViewSet, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        is_private = self.request.data.get("isPrivate")
        has_board = self.request.data.get("hasBoard")
        board_name = self.request.data.get("board_name")
        if is_private:
            instance.password = self.request.data.get("password")
        else:
            instance.password = None
        if has_board and board_name:
            Board.objects.create(title=board_name, ws=instance, user=self.request.user)
        instance.save()

    def perform_update(self, serializer):
        is_private = self.request.data.get("isPrivate")
        instance = self.get_object()
        if is_private:
            if self.request.data.get("password"):
                instance.password = self.request.data.get("password")
        else:
            instance.password = None
        instance.save()


@api_view(['POST'])
def join_ws(request, pk):
    status = False
    ws = models.Workspace.objects.get(pk=pk)
    password = request.data.get("password")
    if request.user:
        if request.user in ws.members.all():
            ws.members.remove(request.user)
            status = True
            msg = "OUT_COMPLETE"
        else:
            if request.user.id == ws.user.id:
                ws.members.add(request.user)
                status = True
                msg = "JOIN_COMPLETE"
            elif (ws.password and ws.password == password) or ws.password is None:
                ws.members.add(request.user)
                status = True
                msg = "JOIN_COMPLETE"
            else:
                msg = "JOIN_FAILED"
        ws.save()
        if request.user.profile.setting is None:
            request.user.profile.setting = {}
        if msg == "JOIN_COMPLETE":
            request.user.profile.setting["ws"] = pk
        elif msg == "JOIN_FAILED" or msg == "OUT_COMPLETE":
            request.user.profile.setting["ws"] = None
        request.user.profile.save()
    else:
        msg = "REQUIRE_LOGIN"
    return Response({
        "status": status,
        "msg": msg
    })


@api_view(['GET'])
def ws_members(request, pk):
    if request.user.is_authenticated:
        ws = models.Workspace.objects.get(pk=pk)
        results = UserReportSerializer(ws.members.all(), many=True).data
    else:
        results = []
    return Response(results)


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
