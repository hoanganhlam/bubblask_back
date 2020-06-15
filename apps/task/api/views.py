from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.task import models
from apps.general.models import HashTag, Workspace
from rest_framework import status
from utils.slug import vi_slug
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone


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
        q = Q()
        tag = request.GET.get("tag")
        is_only_user = request.GET.get("only_user")
        if tag:
            q = q & Q(hash_tags=int(tag))
        if is_only_user == "true" and request.user.is_authenticated:
            q = q & Q(user=request.user)
        elif is_only_user != "true":
            q = q & Q(is_interface=True)
        self.queryset = self.queryset.filter(q)
        return super(BoardViewSet, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        data = request.data
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        task_graph_setting = request.data.get("task_graph_setting")
        task_order = request.data.get("task_order")
        text_tags = request.data.get("text_tags")
        if instance.settings is None:
            instance.settings = {}
        if task_graph_setting is not None:
            instance.settings["task_graph_setting"] = task_graph_setting
        if task_order is not None:
            instance.settings["task_order"] = task_order
        if text_tags:
            data["hash_tags"] = []
            for text_tag in text_tags:
                print(vi_slug(text_tag))
                hash_tag = HashTag.objects.filter(slug=vi_slug(text_tag)).first()
                print(hash_tag)
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        # Start Tracking
        now = timezone.now()
        print(now)

        # => Tim localtime
        # => Check localtime
        # => tao tracking
        # => lay lastime tracking

        # ws = None
        # tz = request.user.profile.time_zone or 0
        # if request.data.get("ws"):
        #     ws = Workspace.objects.get(pk=int(request.data.get("ws")))
        # tracking = models.Tracking.objects.filter(user=request.user, ws=ws, time_zone=tz).first()
        # if tracking is None:
        #     tracking = models.Tracking(user=request.user, ws=ws, time_zone=tz)
        #
        # if request.data.get("status") == "complete":
        #     pass
        # elif request.data.get("status") == "stopping" or request.data.get("status") == "stopped":
        #     pass
        # elif request.data.get("status") == "running":
        #     pass
        # tracking.save()
        return Response(serializer.data)


@api_view(['POST'])
def clone_board(request, pk):
    board = models.Board.objects.get(pk=pk)
    new_board = models.Board(
        title=board.title,
        user=request.user,
        parent=board
    )
    new_board.save()
    old_tasks = list(board.tasks.all())
    old_task_ids = list(map(lambda x: x.id, old_tasks))
    new_tasks = []
    for task in old_tasks:
        new_task = models.Task(
            title=task.title,
            description=task.description,
            interval=task.interval,
            tomato=task.tomato,
            is_bubble=task.is_bubble,
            settings=task.settings,
            board=new_board,
            user=request.user
        )
        new_task.save()
        new_tasks.append(new_task)
    for index in range(len(old_tasks)):
        old_task = old_tasks[index]
        new_task = new_tasks[index]
        if old_task.parent:
            new_parent = new_tasks[old_task_ids.index(old_task.parent.id)]
            new_task.parent = new_parent
            old_task_order = old_task.settings.get("order") if old_task.settings else None
            if old_task_order:
                new_task_order = []
                for idx in old_task_order:
                    new_task_order.append(new_tasks[old_task_ids.index(idx)].id)
                new_task.settings["order"] = new_task_order
            new_task.save()
    old_task_order = board.settings.get("task_order") if board.settings else None
    if old_task_order:
        new_task_order = []
        for idx in old_task_order:
            new_task_order.append(new_tasks[old_task_ids.index(idx)].id)
        new_board.settings["task_order"] = new_task_order
        new_board.save()
    return Response(serializers.BoardSerializer(new_board).data)
