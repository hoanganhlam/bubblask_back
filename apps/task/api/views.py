from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.task import models
from apps.general.models import HashTag
from rest_framework.response import Response
from rest_framework import status
from utils.slug import _slug_strip


class BoardViewSet(viewsets.ModelViewSet):
    models = models.Board
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.BoardSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'slug'

    def list(self, request, *args, **kwargs):
        tag = request.GET.get("tag")
        if tag:
            self.queryset = self.queryset.filter(hash_tags=int(tag))
        return super(BoardViewSet, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        data = request.data
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        task_graph_setting = request.data.get("task_graph_setting")
        text_tags = request.data.get("text_tags")
        if instance.settings is None:
            instance.settings = {}
        if task_graph_setting is not None:
            instance.settings["task_graph_setting"] = task_graph_setting
        if text_tags:
            data["hash_tags"] = []
            for text_tag in text_tags:
                hash_tag = HashTag.objects.filter(slug=_slug_strip(text_tag)).first()
                if hash_tag is None:
                    hash_tag = HashTag(title=text_tag, for_models=["board"])
                    hash_tag.save()
                data["hash_tags"].append(hash_tag.id)
        instance.save()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and (request.user.id == instance.user.id) or request.user.is_staff:
            instance.save(db_status=-1)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskViewSet(viewsets.ModelViewSet):
    models = models.Task
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.TaskSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        board_id = request.GET.get("board")
        if board_id is None:
            if request.user.is_authenticated:
                queryset = models.Task.objects.filter(
                    user=request.user,
                    status__in=["pending", "stopping", "running"],
                    is_bubble=False,
                    board=None
                ).order_by('-id')
                return Response(serializers.TaskSerializer(queryset, many=True).data)
        else:
            queryset = models.Task.objects.filter(
                board_id=int(board_id)
            ).order_by('-id')
            return Response(serializers.TaskSerializer(queryset, many=True).data)
        return Response([])

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and (request.user.id == instance.user.id) or request.user.is_staff:
            if instance.status in ['stopping', 'running']:
                instance.status = 'stopped'
            elif instance.status in ['complete', 'stopped']:
                instance.db_status = -1
            else:
                instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
