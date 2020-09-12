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
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from utils.pusher import pusher_client
from utils.other import get_paginator
from django.db import connection


class BoardViewSet(viewsets.ModelViewSet):
    models = models.Board
    queryset = models.objects.order_by('-id').prefetch_related("hash_tags", "media")
    serializer_class = serializers.BoardSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'slug'

    def list(self, request, *args, **kwargs):
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_BOARDS(%s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.user.id if request.user.is_authenticated else None,
                               '{' + request.GET.get('hash_tags') + '}' if request.GET.get('hash_tags') else None,
                               p.get("board", None),
                               request.GET.get("is_interface", None),
                               request.GET.get("user", None)
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(result)

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
                hash_tag = HashTag.objects.filter(slug=vi_slug(text_tag)).first()
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
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TASKS(%s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.user.id if request.user.is_authenticated else None,
                               request.GET.get("board", None),
                               '{' + request.GET.get('statuses') + '}' if request.GET.get('statuses') else None,
                               request.GET.get("user", None),
                               request.GET.get("parent", None)
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(result)

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
            instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        old_stt = instance.status
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        new_stt = instance.status
        # Start Tracking
        if old_stt != 'pending' and old_stt != new_stt and instance.children.count() == 0:
            now = timezone.now()
            ws = None
            user_tz = request.user.profile.time_zone
            local_time = now + timedelta(hours=user_tz)
            local_date = local_time.date()
            if request.data.get("ws"):
                ws = Workspace.objects.get(pk=int(request.data.get("ws")))
            tracking = models.Tracking.objects.filter(user=request.user, time_zone=user_tz,
                                                      date_record=local_date).first()
            if tracking is None:
                tracking = models.Tracking(user=request.user, time_zone=user_tz, date_record=local_date)
            if tracking.data is None:
                tracking.data = []
            if request.data.get("status") in ["complete", "stopping", "stopped"]:
                if len(tracking.data) > 0:
                    if tracking.data[len(tracking.data) - 1]:
                        start_time = tracking.data[len(tracking.data) - 1].get("time_start")
                        time_taken = (now - parse_datetime(start_time)).total_seconds()
                        tracking.data[len(tracking.data) - 1]["time_stop"] = str(now)
                        tracking.data[len(tracking.data) - 1]["time_taken"] = time_taken
                        if request.data.get("status") == "complete":
                            instance.take_time = sum(c.get("time_taken", 0) for c in tracking.data)
                            instance.save()
                        if request.user.profile.extra is None:
                            request.user.profile.extra = {}
                        request.user.profile.extra["temp_score"] = request.user.profile.extra.get("temp_score",
                                                                                                  0) + time_taken
                        if ws is not None:
                            if ws.report is None:
                                ws.report = {}
                            ws.report[request.user.id] = ws.report.get(str(request.user.id), 0) + time_taken
                            pusher_client.trigger('ws_' + str(ws.id), 'change-user-score', {
                                "user": request.user.id,
                                "score": ws.report.get(str(request.user.id), 0) + time_taken
                            })
                            ws.save()
                        request.user.profile.save()
            elif request.data.get("status") == "running":
                tracking.data.append({
                    "time_start": str(now),
                    "time_stop": None,
                    "time_taken": 0,
                    "task": instance.id,
                    "ws": ws.id if ws is not None else None
                })
            tracking.save()
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
            user=request.user,
            status="pending"
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
