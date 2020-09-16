from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.task import models
from apps.general.models import HashTag
from rest_framework import status
from utils.slug import vi_slug
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from utils.pusher import pusher_client
from utils.other import get_paginator
from django.db import connection


def fetch_board(boar_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_BOARD(%s, %s)", [
            int(boar_id) if str(boar_id).isnumeric() else None,
            str(boar_id),
        ])
        out = cursor.fetchone()[0]
    return Response(out)


def fetch_task(task_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_TASK(%s)", [
            task_id
        ])
        result = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return Response(status=status.HTTP_200_OK, data=result)


class BoardViewSet(viewsets.ModelViewSet):
    models = models.Board
    queryset = models.objects.order_by('-id').prefetch_related("hash_tags", "media")
    serializer_class = serializers.BoardSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'slug'
    lookup_value_regex = '[\w.@+-]+'

    def list(self, request, *args, **kwargs):
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_BOARDS(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.user.id if request.user.is_authenticated else None,
                               '{' + request.GET.get('hash_tags') + '}' if request.GET.get('hash_tags') else None,
                               p.get("board", None),
                               '{' + request.GET.get('kinds') + '}' if request.GET.get('kinds') else None,
                               request.GET.get("is_private", None),
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return fetch_board(serializer.data.get("id"))

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
        return fetch_board(serializer.data.get("id"))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and (request.user.id == instance.user.id) or request.user.is_staff:
            instance.save(db_status=-1)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        return fetch_board(kwargs["slug"])


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
        serializer.save(user=self.request.user, assignee=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return fetch_task(serializer.data.get("id"))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and (request.user.id == instance.user.id) or request.user.is_staff:
            flag = False
            if instance.status in ['stopping', 'running']:
                instance.status = 'stopped'
                flag = True
            elif instance.status in ['complete', 'stopped']:
                instance.db_status = -1
                flag = True
            else:
                instance.delete()
            if flag:
                instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        errs = []
        user = request.user
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        # CHECK
        if not user.is_authenticated or not (user == instance.user or user == instance.assignee):
            errs.append("UNAUTHORISED")
        old_stt = instance.status
        old_assignee = instance.assignee
        if old_assignee is not None:
            if user != old_assignee:
                errs.append("UNAUTHORISED")
            if old_assignee.id != request.data.get("assignee") and user != instance.user:
                errs.append("UNAUTHORISED")
            # if old_assignee.id != request.data.get("assignee") and user == instance.user:
        else:
            if user == instance.user or (instance.settings is not None and instance.settings.get("collaborate")):
                instance.assignee = user
            else:
                errs.append("UNAUTHORISED")
        if len(errs) > 0:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errs)
        # FINISH CHECK

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        new_stt = instance.status
        # Start Tracking
        if old_stt != 'pending' and old_stt != new_stt and instance.children.count() == 0:
            now = timezone.now()
            user_tz = user.profile.time_zone
            local_time = now + timedelta(hours=user_tz)
            local_date = local_time.date()
            tracking = models.Tracking.objects.filter(
                user=user,
                time_zone=user_tz,
                board_id=user.profile.setting.get("board") if user.profile is not None and user.profile.setting.get("board") else None,
                date_record=local_date).first()
            if tracking is None:
                tracking = models.Tracking(user=user, time_zone=user_tz, date_record=local_date)
                if user.profile and user.profile and user.profile.setting.get("board"):
                    b = models.Board.objects.get(pk=user.profile.setting.get("board"))
                    tracking.board = b
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
                        if user.profile.extra is None:
                            user.profile.extra = {}
                        user.profile.extra["temp_score"] = user.profile.extra.get("temp_score", 0) + time_taken
                        pusher_client.trigger('board_' + str(user.profile.setting.get("board")), 'change-user-score', {
                            "user": request.user.id,
                            "score": time_taken
                        })
                        request.user.profile.save()
            elif request.data.get("status") == "running":
                tracking.data.append({
                    "time_start": str(now),
                    "time_stop": None,
                    "time_taken": 0,
                    "task": instance.id,
                })
            tracking.save()
        # End tracking
        return fetch_task(instance.id)


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


@api_view(['POST'])
def join_board(request, pk):
    board = models.Board.objects.get(pk=pk)
    password = request.data.get("password")
    if request.user:
        current_board = request.user.profile.setting.get("board", None)
        if request.user in board.members.all() and current_board is not None and int(current_board) == board.id:
            flag = True
            msg = "OUT_COMPLETE"
        elif request.user.id == board.user.id or (not board.is_private) or (
            board.is_private and board.password == password):
            flag = True
            msg = "JOIN_COMPLETE"
        else:
            flag = False
            msg = "JOIN_FAILED"
        board.save()
        if request.user.profile.setting is None:
            request.user.profile.setting = {}

        if msg == "JOIN_COMPLETE":
            check = models.BoardMember.objects.filter(user=request.user, board=board).first()
            if check is None:
                models.BoardMember.objects.create(user=request.user, board=board)
            request.user.profile.setting["board"] = pk
        elif msg == "JOIN_FAILED" or msg == "OUT_COMPLETE":
            if request.data.get("force_out"):
                models.BoardMember.objects.filter(user=request.user, board=board).delete()
            request.user.profile.setting["board"] = None
        request.user.profile.save()
    else:
        flag = False
        msg = "REQUIRE_LOGIN"
    return Response({
        "status": flag,
        "msg": msg
    })


@api_view(['GET'])
def board_members(request, pk):
    fields = request.GET.get("fields", 'user,board').split(",")
    p = get_paginator(request)
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_MEMBERS(%s, %s, %s, %s, %s)",
                       [
                           p.get("page_size"),
                           p.get("offs3t"),
                           p.get("search"),
                           None,
                           pk
                       ])
        result = cursor.fetchone()[0]
        if result.get("results") is None:
            result["results"] = []
        temp = result["results"]
        result["results"] = []
        for r in temp:
            new_result = {}
            for field in fields:
                new_result[field] = r.get(field)
            result["results"].append(new_result)
        cursor.close()
        connection.close()
        return Response(result)


@api_view(['GET'])
def board_messages(request, pk):
    p = get_paginator(request)
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_MESSAGES(%s, %s, %s, %s)",
                       [
                           p.get("page_size"),
                           p.get("offs3t"),
                           p.get("search"),
                           "board_" + str(pk)
                       ])
        result = cursor.fetchone()[0]
        if result.get("results") is None:
            result["results"] = []
        cursor.close()
        connection.close()
        return Response(result)
